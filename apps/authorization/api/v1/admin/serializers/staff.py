from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.db import transaction
from django.utils.crypto import get_random_string
from rest_framework import serializers
from apps.authorization.models import StaffProfile

User = get_user_model()

GENERATED_PASSWORD_LENGTH = 12


def generate_password():
    while True:
        password = get_random_string(GENERATED_PASSWORD_LENGTH)
        if not password.isdigit():  # NumericPasswordValidator
            return password


def validate_staff_password(password, user):
    try:
        password_validation.validate_password(password, user)
    except DjangoValidationError as e:
        raise serializers.ValidationError({"password": list(e.messages)})


class StaffAccessLevelField(serializers.ChoiceField):
    """Access level: stored as `User.is_superuser`."""

    def __init__(self, **kwargs):
        super().__init__(choices=StaffProfile.AccessLevel.choices, **kwargs)

    def get_attribute(self, instance):
        return StaffProfile.AccessLevel.SUPER_ADMIN if instance.is_superuser else StaffProfile.AccessLevel.STAFF


class StaffShortSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="staff_profile.full_name", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "full_name")


class StaffSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="staff_profile.full_name", max_length=150)
    position = serializers.CharField(source="staff_profile.position", max_length=150, required=False,
                                     allow_blank=True)
    access_level = StaffAccessLevelField(required=False)
    must_change_password = serializers.BooleanField(source="staff_profile.must_change_password", required=False)
    status = serializers.ChoiceField(source="staff_profile.status", choices=StaffProfile.Status.choices,
                                     read_only=True)
    block_reason = serializers.ChoiceField(source="staff_profile.block_reason", read_only=True, allow_null=True,
                                           choices=StaffProfile.BlockReason.choices)
    failed_login_attempts = serializers.IntegerField(source="staff_profile.failed_login_attempts", read_only=True)
    created_by = StaffShortSerializer(source="staff_profile.created_by", read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(source="date_joined", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "full_name", "position", "access_level", "must_change_password", "status",
                  "block_reason", "failed_login_attempts", "last_login", "created_by", "created_at")
        # login can't be changed after creation
        read_only_fields = ("username", "last_login")

    def validate_access_level(self, value):
        user = self.instance
        if user and user == self.context["request"].user and value != StaffProfile.of(user).access_level:
            raise serializers.ValidationError("You cannot change your own access level")
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        access_level = validated_data.get("access_level")
        if access_level is not None:
            instance.is_superuser = access_level == StaffProfile.AccessLevel.SUPER_ADMIN
            instance.save(update_fields=["is_superuser"])

        profile_data = validated_data.get("staff_profile")
        if profile_data:
            profile = StaffProfile.of(instance)
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()
        return instance


class StaffCreateSerializer(StaffSerializer):
    username = serializers.CharField(max_length=150, validators=[
        RegexValidator(r"^[a-zA-Z0-9.]+$", "Only latin letters, digits and dots are allowed")])
    password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)
    must_change_password = serializers.BooleanField(source="staff_profile.must_change_password", default=True)

    class Meta(StaffSerializer.Meta):
        fields = StaffSerializer.Meta.fields + ("password",)
        read_only_fields = ("last_login",)

    def validate_username(self, value):
        value = value.lower()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Staff with this login already exists")
        return value

    def validate(self, attrs):
        validate_staff_password(attrs["password"], User(username=attrs["username"]))
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"], password=validated_data["password"], is_staff=True,
            is_superuser=validated_data.get("access_level") == StaffProfile.AccessLevel.SUPER_ADMIN,
        )
        profile = StaffProfile.of(user)  # created by the post_save signal
        for field, value in validated_data["staff_profile"].items():
            setattr(profile, field, value)
        profile.created_by = self.context["request"].user
        profile.save()
        return user


class StaffResetPasswordSerializer(serializers.Serializer):
    """Sets a temporary password. Without `password` one is generated; the response returns it once."""
    password = serializers.CharField(max_length=128, required=False, trim_whitespace=False)
    must_change_password = serializers.BooleanField(default=True)

    def validate(self, attrs):
        if attrs.get("password"):
            validate_staff_password(attrs["password"], self.instance)
        else:
            attrs["password"] = generate_password()
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.set_password(validated_data["password"])
        instance.save(update_fields=["password"])
        profile = StaffProfile.of(instance)
        profile.must_change_password = validated_data["must_change_password"]
        profile.save(update_fields=["must_change_password", "updated_at"])
        return instance

    def to_representation(self, instance):
        return {"password": self.validated_data["password"],
                "must_change_password": self.validated_data["must_change_password"]}
