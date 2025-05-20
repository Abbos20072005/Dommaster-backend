from django.conf import settings
import base64

import os
import django

def generate_link(order_id: int, total_price: int, type_pyment: int, is_web: bool = False):
    if type_pyment == 1:
        # Click payment link
        url = (
            f'https://my.click.uz/services/pay?service_id={settings.CLICK_SERVICE_ID}'
            f'&merchant_id={settings.CLICK_MERCHANT_ID}'
            f'&amount={total_price}'
            f'&transaction_param={order_id}'
        )
        if is_web and settings.REDIRECTED_URL:
            url += f'&return_url={settings.REDIRECTED_URL}'
        return url

    elif type_pyment == 2:
        # Payme payment link
        url_prefix = f'm={settings.PAYME_ID};ac.order_id={order_id};a={total_price * 100}'
        if is_web and settings.REDIRECTED_URL:
            url_prefix += f';c={settings.REDIRECTED_URL}'

        # Encode the string correctly
        encoded_string = base64.b64encode(url_prefix.encode()).decode()
        url = f'https://checkout.paycom.uz/{encoded_string}'
        return url

    return None

#print(generate_link(15, 1000, 2))