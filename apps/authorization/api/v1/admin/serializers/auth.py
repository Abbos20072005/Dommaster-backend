from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from apps.authorization.models import StaffProfile
from .staff import StaffAccessLevelField, validate_staff_password

ACCOUNT_BLOCKED = "Account is blocked"


def generate_admin_tokens(admin):
    # `admin_id` instead of `user_id` so admin tokens never authenticate as a Customer (and vice versa)
    refresh = RefreshToken()
    refresh['admin_id'] = admin.id
    refresh['role'] = 'admin'
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def find_staff(username):
    # logins created in the dashboard are lowercase; the form may send "Kamola.e"
    staff = get_user_model().objects.filter(is_staff=True)
    return staff.filter(username=username).first() or staff.filter(username__iexact=username).first()


class AdminSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="staff_profile.full_name", read_only=True)
    position = serializers.CharField(source="staff_profile.position", read_only=True)
    access_level = StaffAccessLevelField(read_only=True)
    must_change_password = serializers.BooleanField(source="staff_profile.must_change_password", read_only=True)

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "first_name", "last_name", "email", "is_superuser", "last_login",
                  "full_name", "position", "access_level", "must_change_password")


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, write_only=True)
    password = serializers.CharField(max_length=128, write_only=True)

    def validate(self, attrs):
        staff = find_staff(attrs["username"])
        if staff and not staff.is_active:
            # same answer for a right and a wrong password: a blocked account must not confirm guesses
            raise PermissionDenied(ACCOUNT_BLOCKED)

        username = staff.username if staff else attrs["username"]
        admin = authenticate(self.context.get("request"), username=username, password=attrs["password"])
        if admin is None:
            if staff and StaffProfile.of(staff).register_failed_login():
                raise PermissionDenied(ACCOUNT_BLOCKED)
            raise AuthenticationFailed("Incorrect username or password")
        if not admin.is_staff:
            raise PermissionDenied()

        StaffProfile.of(admin).reset_failed_logins()
        update_last_login(None, admin)
        return {**generate_admin_tokens(admin), "admin": AdminSerializer(admin).data}


class AdminTokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            refresh = RefreshToken(attrs["refresh"])
        except TokenError as e:
            raise InvalidToken(e.args[0])

        admin_id = refresh.payload.get("admin_id")
        admin = get_user_model().objects.filter(id=admin_id, is_active=True, is_staff=True).first() if admin_id else None
        if not admin:
            raise InvalidToken("Token contained no recognizable admin identification")

        return generate_admin_tokens(admin)


class AdminChangePasswordSerializer(serializers.Serializer):
    """The logged-in admin changes their own password (also clears `must_change_password`)."""
    old_password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)

    def validate_old_password(self, value):
        if not self.instance.check_password(value):
            raise serializers.ValidationError("Incorrect password")
        return value

    def validate(self, attrs):
        if attrs["new_password"] == attrs["old_password"]:
            raise serializers.ValidationError({"new_password": "The new password must differ from the old one"})
        try:
            validate_staff_password(attrs["new_password"], self.instance)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"new_password": e.detail["password"]})
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.set_password(validated_data["new_password"])
        instance.save(update_fields=["password"])
        profile = StaffProfile.of(instance)
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password", "updated_at"])
        return instance

    def to_representation(self, instance):
        return AdminSerializer(instance).data
