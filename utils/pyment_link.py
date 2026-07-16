import base64

from django.conf import settings
from service.models import Order


def generate_link(order_id: int, total_price: int, type_pyment: int, is_web: bool = False, payment_method: str = None):
    if type_pyment == 1:

        url = (
            f'https://my.click.uz/services/pay?service_id={settings.CLICK_SERVICE_ID}'
            f'&merchant_id={settings.CLICK_MERCHANT_ID}'
            f'&amount={total_price}'
            f'&transaction_param={order_id}'
        )

        if is_web and settings.REDIRECTED_URL:
            url += f'&return_url={settings.REDIRECTED_URL.format(order_id)}'
        return url

    elif type_pyment == 2:

        url_prefix = f'm={settings.PAYME_ID};ac.order_id={order_id};a={total_price * 100}'

        if is_web and settings.REDIRECTED_URL:
            url_prefix += f';c={settings.REDIRECTED_URL.format(order_id)}'

        encoded_string = base64.b64encode(url_prefix.encode()).decode()
        url = f'https://checkout.paycom.uz/{encoded_string}'
        return url

    elif type_pyment == 3:

        url_prefix = f'?serviceId={settings.SERVICE_ID_UZUM}&account={order_id}'

        if is_web and settings.REDIRECTED_URL:
            url_prefix += f'&successUrl={settings.REDIRECTED_URL.format(order_id)}'
        url = f'https://www.uzumbank.uz/open-service{url_prefix}'
        return url

    elif type_pyment == 4:
        order = Order.objects.filter(id=order_id).first()
        order.status = 1
        order.payment_type = 4
        order.payment_method = payment_method
        order.save(update_fields=["status", "payment_type", "payment_method"])
        return None
    return None
