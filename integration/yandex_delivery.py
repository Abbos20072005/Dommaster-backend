import os
import time
import logging
from decimal import Decimal, InvalidOperation

import requests
from dotenv import load_dotenv
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from service.models import Product
from service.serializers import normalize_delivery_price

load_dotenv()

logger = logging.getLogger(__name__)

YANDEX_DELIVERY_API_URL = os.getenv(
    "YANDEX_DELIVERY_API_URL", "https://b2b.taxi.yandex.net"
)
YANDEX_DELIVERY_OAUTH_TOKEN = os.getenv("YANDEX_DELIVERY_OAUTH_TOKEN", "")
YANDEX_DELIVERY_LANGUAGE = os.getenv("YANDEX_DELIVERY_LANGUAGE", "ru")

CHECK_PRICE_PATH = "/b2b/cargo/integration/v2/check-price"
CHECK_PRICE_MAX_ATTEMPTS = 3
CHECK_PRICE_RETRY_BASE_DELAY = 1

TAX_CLASS_LIMITS = {
    "courier": (Decimal("0.8"), Decimal("0.5"), Decimal("0.5")),
    "express": (Decimal("1.0"), Decimal("0.6"), Decimal("0.5")),
    "cargo__van": (Decimal("1.7"), Decimal("0.96"), Decimal("0.9")),
    "cargo__lcv_m": (Decimal("2.6"), Decimal("1.3"), Decimal("1.5")),
    "cargo__lcv_l": (Decimal("3.8"), Decimal("1.8"), Decimal("1.8")),
}

SIZE_KEYS = {"length", "width", "height"}

YANDEX_ERROR_MESSAGES = {
    "bad_request": "Некорректный запрос: проверьте переданные данные.",
    "missing_accept_language": "Язык запроса (Accept-Language) не передан или некорректен.",
    "address_not_found": "Адрес не найден: проверьте точки маршрута.",
    "errors.suitable_offer_not_found": "Не найдено подходящего автомобиля — ослабьте требования.",
    "estimating.cant_construct_route": "Не удалось построить маршрут — проверьте адреса и координаты.",
    "estimating.claim.no_zone_id": "Нет зоны доставки для этих точек — проверьте зону покрытия.",
    "estimating.requirement_unavailable": "Запрошенное требование недоступно в этой зоне доставки.",
    "estimating.no_pickup_point": "Не найдена точка забора груза.",
    "estimating.too_large_linear_size": "Товар слишком велик по линейным размерам.",
    "estimating.warning.too_large_item": "Товар слишком велик для выбранного тарифа.",
    "estimating.warning.too_heavy_item": "Товар слишком тяжёлый для выбранного тарифа.",
    "estimating.too_many_loaders": "Слишком много грузчиков для этого тарифа.",
    "estimating.cargo_type_unavailable": "Данный тип кузова недоступен в этой зоне.",
    "estimating.route_too_long": "Маршрут слишком длинный для выбранного тарифа.",
    "estimating.route_too_short": "Маршрут слишком короткий для выбранного тарифа.",
    "estimating.tariff.not_available_in_zone": "Тариф недоступен в этой зоне доставки.",
    "estimating.tariff.no_categories": "Для тарифа не заданы категории в этой зоне.",
    "no_tariff_plan": "Для этой зоны не настроен тарифный план.",
    "estimating.swapped_coordinates": "Координаты переданы в неверном порядке: нужно [долгота, широта].",
    "estimating.payment_method_card_not_allowed": "Оплата картой недоступна для этого тарифа.",
    "estimating.payment_method_cash_not_allowed": "Оплата наличными недоступна для этого тарифа.",
}


class DeliveryItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=False)
    quantity = serializers.IntegerField(min_value=1)
    weight = serializers.DecimalField(
        max_digits=10, decimal_places=4, required=False
    )
    size = serializers.DictField(required=False)
    pickup_point = serializers.IntegerField(required=False)
    dropoff_point = serializers.IntegerField(required=False)
    age_restricted = serializers.BooleanField(required=False)

    def validate_size(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("size должен быть объектом")
        if not SIZE_KEYS.issuperset(set(value.keys())) or not SIZE_KEYS.intersection(
            value.keys()
        ):
            raise serializers.ValidationError(
                "size должен содержать только length, width, height"
            )
        try:
            for key in value:
                Decimal(str(value[key]))
        except InvalidOperation:
            raise serializers.ValidationError("Значения size должны быть числами")
        return value


class DeliveryRoutePointSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    fullname = serializers.CharField(required=False, allow_blank=True)
    coordinates = serializers.ListField(
        child=serializers.FloatField(), min_length=2, max_length=2, required=False
    )
    country = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    street = serializers.CharField(required=False)
    building = serializers.CharField(required=False)
    porch = serializers.CharField(required=False)
    sfloor = serializers.CharField(required=False)
    sflat = serializers.CharField(required=False)


class DeliveryIntervalSerializer(serializers.Serializer):
    delivery_interval = serializers.DictField(
        child=serializers.DateTimeField(), required=True
    )

    def validate_delivery_interval(self, value):
        if "from" not in value or "to" not in value:
            raise serializers.ValidationError(
                "delivery_interval должен содержать ключи 'from' и 'to'"
            )
        return value


class RequirementsSerializer(serializers.Serializer):
    taxi_class = serializers.ChoiceField(
        choices=["courier", "express", "cargo"], required=False
    )
    cargo_type = serializers.ChoiceField(
        choices=["van", "lcv_m", "lcv_l", "lcv_xl"], required=False
    )
    cargo_loaders = serializers.IntegerField(min_value=0, max_value=2, required=False)
    cargo_options = serializers.ListField(
        child=serializers.ChoiceField(choices=["auto_courier", "thermobag"]),
        required=False,
    )
    pro_courier = serializers.BooleanField(required=False)
    same_day_data = DeliveryIntervalSerializer(required=False)


class CheckPriceRequestSerializer(serializers.Serializer):
    items = serializers.ListField(child=DeliveryItemSerializer())
    route_points = serializers.ListField(child=DeliveryRoutePointSerializer())
    requirements = RequirementsSerializer(required=False)
    skip_door_to_door = serializers.BooleanField(required=False, default=False)
    accept_language = serializers.ChoiceField(
        choices=["ru", "en"], required=False, default=YANDEX_DELIVERY_LANGUAGE
    )

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Должен быть хотя бы один товар")
        return value

    def validate_route_points(self, value):
        if len(value) < 2:
            raise serializers.ValidationError(
                "Нужно минимум две точки маршрута: забор и доставка"
            )
        return value

    def validate(self, attrs):
        requirements = attrs.get("requirements") or {}
        taxi_class = requirements.get("taxi_class")
        limit_key = None
        if taxi_class == "cargo":
            limit_key = f"cargo__{requirements.get('cargo_type') or 'lcv_l'}"
        elif taxi_class:
            limit_key = taxi_class

        limits = TAX_CLASS_LIMITS.get(limit_key) if limit_key else None
        if limits and limit_key not in ("cargo__lcv_l", "cargo__lcv_xl"):
            for item in attrs["items"]:
                size = item.get("size")
                if not size:
                    continue
                for index, dimension in enumerate(("length", "width", "height")):
                    if (
                        dimension in size
                        and Decimal(str(size[dimension])) > limits[index]
                    ):
                        raise serializers.ValidationError(
                            "Размеры товара превышают лимиты выбранного тарифа "
                            f"({limits[0]} x {limits[1]} x {limits[2]} м)"
                        )
        return attrs


class CheckPriceResponseSerializer(serializers.Serializer):
    price = serializers.DecimalField(max_digits=18, decimal_places=4)
    currency_rules = serializers.DictField()
    requirements = RequirementsSerializer(required=False)
    distance_meters = serializers.IntegerField(required=False)
    eta = serializers.IntegerField(required=False)
    zone_id = serializers.CharField(required=False)


def _raise_yandex_error(response):
    yandex_code = None
    yandex_message = None
    try:
        data = response.json()
        if isinstance(data, dict):
            yandex_code = data.get("code")
            yandex_message = data.get("message")
    except ValueError:
        pass

    yandex_code = str(yandex_code) if yandex_code else str(response.status_code)
    user_message = (
        YANDEX_ERROR_MESSAGES.get(yandex_code)
        or yandex_message
        or f"Ошибка сервиса Яндекс Доставки (HTTP {response.status_code})"
    )
    logger.error(f"Yandex Delivery check-price failed: {yandex_code} - {user_message}")
    raise CustomApiException(
        error_code=ErrorCodes.YANDEX_DELIVERY_ERROR, message=user_message
    )


def _build_items(validated_items, route_points, requirements):
    first_point_id = route_points[0].get("id", 1)
    last_point_id = route_points[-1].get("id", len(route_points))

    product_ids = [
        item.get("product_id")
        for item in validated_items
        if item.get("product_id") is not None
    ]
    products = {}
    if product_ids:
        products = {
            product.id: product
            for product in Product.objects.filter(id__in=product_ids)
        }

    items = []
    for item in validated_items:
        product = products.get(item.get("product_id"))
        quantity = item["quantity"]

        weight = item.get("weight")
        size = dict(item.get("size") or {})

        if weight is None and product is not None and product.weight is not None:
            weight = product.weight
        if not size and product is not None:
            if product.length is not None:
                size["length"] = float(product.length)
            if product.width is not None:
                size["width"] = float(product.width)
            if product.height is not None:
                size["height"] = float(product.height)

        size = {key: float(value) for key, value in size.items()}

        payload_item = {"quantity": quantity}
        if weight is not None:
            payload_item["weight"] = float(weight)
        if size:
            payload_item["size"] = size

        if len(route_points) > 1:
            payload_item["pickup_point"] = item.get("pickup_point") or first_point_id
            payload_item["dropoff_point"] = item.get("dropoff_point") or last_point_id
        if item.get("age_restricted"):
            payload_item["age_restricted"] = True

        items.append(payload_item)

    return items


def _build_requirements(requirements):
    if not requirements:
        return None

    payload_requirements = {}
    if requirements.get("taxi_class"):
        payload_requirements["taxi_class"] = requirements["taxi_class"]
    if requirements.get("cargo_type"):
        payload_requirements["cargo_type"] = requirements["cargo_type"]
    if requirements.get("cargo_loaders") is not None:
        payload_requirements["cargo_loaders"] = requirements["cargo_loaders"]
    if requirements.get("cargo_options"):
        payload_requirements["cargo_options"] = requirements["cargo_options"]
    if requirements.get("pro_courier"):
        payload_requirements["pro_courier"] = True

    same_day = requirements.get("same_day_data")
    if same_day and same_day.get("delivery_interval"):
        payload_requirements["same_day_data"] = {
            "delivery_interval": same_day["delivery_interval"]
        }

    return payload_requirements or None


class YandexDeliveryService:
    @staticmethod
    def check_price(
        items, route_points, requirements=None, skip_door_to_door=False, accept_language=None
    ):
        if not YANDEX_DELIVERY_OAUTH_TOKEN:
            raise CustomApiException(
                error_code=ErrorCodes.YANDEX_DELIVERY_ERROR,
                message="Не настроен токен Яндекс Доставки",
            )

        url = f"{YANDEX_DELIVERY_API_URL}{CHECK_PRICE_PATH}"
        headers = {
            "Authorization": f"Bearer {YANDEX_DELIVERY_OAUTH_TOKEN}",
            "Content-Type": "application/json",
            "Accept-Language": accept_language or YANDEX_DELIVERY_LANGUAGE,
        }
        payload = {
            "items": items,
            "route_points": route_points,
        }
        if requirements:
            payload["requirements"] = requirements
        if skip_door_to_door:
            payload["skip_door_to_door"] = True

        for attempt in range(1, CHECK_PRICE_MAX_ATTEMPTS + 1):
            try:
                response = requests.post(
                    url, json=payload, headers=headers, timeout=30
                )
            except requests.RequestException as e:
                logger.error(f"Yandex Delivery request failed: {e}")
                raise CustomApiException(
                    error_code=ErrorCodes.YANDEX_DELIVERY_ERROR,
                    message="Не удалось связаться с сервисом Яндекс Доставки",
                )

            if response.status_code == 429 and attempt < CHECK_PRICE_MAX_ATTEMPTS:
                time.sleep(CHECK_PRICE_RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                continue

            if response.status_code != 200:
                _raise_yandex_error(response)

            return response.json()


class YandexDeliveryIntegrationViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Yandex Delivery check price",
        operation_description="Предварительный расчёт стоимости доставки (check-price) для Узбекистана",
        request_body=CheckPriceRequestSerializer(),
        responses={200: CheckPriceResponseSerializer()},
        tags=["Yandex Delivery"],
    )
    def check_price(self, request):
        serializer = CheckPriceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(
                error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors
            )

        validated = serializer.validated_data
        route_points = validated["route_points"]
        requirements = validated.get("requirements") or {}
        skip_door_to_door = validated.get("skip_door_to_door", False)

        items = _build_items(
            validated["items"], route_points, requirements
        )
        route_points = [
            {key: value for key, value in point.items() if value not in (None, "")}
            for point in route_points
        ]

        yandex_data = YandexDeliveryService.check_price(
            items=items,
            route_points=route_points,
            requirements=_build_requirements(requirements),
            skip_door_to_door=skip_door_to_door,
            accept_language=validated.get("accept_language"),
        )

        price = normalize_delivery_price(yandex_data.get("price"))
        if price is None:
            raise CustomApiException(
                error_code=ErrorCodes.YANDEX_DELIVERY_ERROR,
                message="Некорректная цена от Яндекс Доставки",
            )

        result = {
            "price": str(price),
            "currency_rules": yandex_data.get("currency_rules"),
            "requirements": yandex_data.get("requirements"),
            "distance_meters": yandex_data.get("distance_meters"),
            "eta": yandex_data.get("eta"),
            "zone_id": yandex_data.get("zone_id"),
        }

        return Response(
            data={"result": result, "ok": True}, status=status.HTTP_200_OK
        )