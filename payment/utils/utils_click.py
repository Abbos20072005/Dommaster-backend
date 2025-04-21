import hashlib

from django.conf import settings
from django.utils.module_loading import import_string

from .exception_click import ClickErrorCode, ClickError
from payment.models import ClickTransaction

OrderModels = import_string(settings.CLICK_ACCOUNT_MODEL)


def _serialize_request(data, prepare):
    required_fields = [
        "click_trans_id", "service_id", "click_paydoc_id", "merchant_trans_id", "amount", "action", "error",
        "sign_time", "sign_string"
    ]
    if not prepare:
        required_fields.append("merchant_prepare_id")

    for field in required_fields:
        if field not in data:
            return None, ClickError(ClickErrorCode.CLICK_REQUEST_ERROR)

    sign_string = generate_sign(data, prepare)
    if sign_string != data.get("sign_string"):
        return None, ClickError(ClickErrorCode.SIGN_CHECK_FAILED)

    return data, None


def generate_sign(data, prepare):
    sign_data = "".join([
        str(data["click_trans_id"]),
        str(settings.CLICK_SERVICE_ID),
        settings.CLICK_SECRET_KEY,
        str(data["merchant_trans_id"]),
        str(data["merchant_prepare_id"]) if not prepare else '',
        str(data["amount"]),
        str(data["action"]),
        str(data["sign_time"])
    ])
    return hashlib.md5(sign_data.encode()).hexdigest()


def get_order(merchant_trans_id):
    return OrderModels.objects.filter(id=merchant_trans_id).first()


def get_transaction(prepare_id):
    return ClickTransaction.objects.filter(id=prepare_id).first()


def create_transaction(params, order):
    return ClickTransaction.get_or_create(
        account_id=order.id,
        transaction_id=params["click_trans_id"],
        amount=params["amount"],
        state=ClickTransaction.INITIATING
    )
