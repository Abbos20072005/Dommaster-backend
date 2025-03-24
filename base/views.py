from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from .serializers import BannerSerializer
from .models import Banner

class BaseViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Banner",
        operation_description="Banner",
        responses={200: BannerSerializer(many=True)},
        tags=["Base"]
    )
    def banner_list(self, request):
        banner = Banner.objects.filter(is_visible=True)
        serializer = BannerSerializer(banner, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)