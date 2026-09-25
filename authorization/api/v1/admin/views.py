from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.response import Response
from utils.admin_views import AdminViewMixin
from .serializers import AdminLoginSerializer, AdminTokenRefreshSerializer, AdminSerializer


class AdminTokenAPIView(GenericAPIView):
    """Base for login/refresh: serializer.validate() returns the response payload."""
    authentication_classes = []

    def get_authenticate_header(self, request):
        # without it DRF turns AuthenticationFailed into 403 (no authenticators here)
        return 'Bearer realm="api"'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class AdminLoginAPIView(AdminTokenAPIView):
    serializer_class = AdminLoginSerializer


class AdminTokenRefreshAPIView(AdminTokenAPIView):
    serializer_class = AdminTokenRefreshSerializer


class AdminMeAPIView(AdminViewMixin, RetrieveAPIView):
    serializer_class = AdminSerializer

    def get_object(self):
        return self.request.user
