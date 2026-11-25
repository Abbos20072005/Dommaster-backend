"""Checkout / password-login guards found by the 13.11.2026 pentest. Run: env/Scripts/python.exe manage.py test apps.service"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient

from apps.authorization.models import Customer, CustomerAddresses
from apps.base.models import Promocodes
from apps.service.models import Cart, CartItem, Order, Product
from apps.service.tests import ApiTestCase, make_customer, make_item_category, make_product


class CheckoutGuardTests(ApiTestCase):
    def setUp(self):
        self.customer = make_customer("+998900000201")
        CustomerAddresses.objects.create(customer=self.customer, name="Uy", is_default=True)
        _, item_category = make_item_category("C")
        self.product = make_product("P1", item_category, 38364)
        self.cart = Cart.objects.create(customer=self.customer)
        self.item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)
        self.client = self.client_for(self.customer)

    def checkout(self, **data):
        return self.client.post("/api/v1/order/", {"payment_type": 1, "delivery_price": "30000", **data},
                                format="json")

    def test_negative_cart_quantity_refused(self):
        response = self.client.patch("/api/v1/cart/item/", {"product": self.product.id, "quantity": -5},
                                     format="json")
        self.assertEqual(response.status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 1)
        self.item.delete()
        response = self.client.post("/api/v1/cart/item/", {"product": self.product.id, "quantity": -5},
                                    format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CartItem.objects.exists())

    def test_negative_delivery_price_refused(self):
        self.assertEqual(self.checkout(delivery_price="-30000").status_code, 400)
        self.assertFalse(Order.objects.exists())
        response = self.checkout()
        self.assertEqual(response.status_code, 201, response.data)
        # the product price 38364 is stored rounded up to 38400 (utils.price) + delivery 30000
        self.assertEqual(Order.objects.get().total_price, 68400)

    def test_unknown_payment_and_delivery_type_refused(self):
        for data in ({"payment_type": 99}, {"payment_type": -1}, {"delivery_type": 5}):
            self.assertEqual(self.checkout(**data).status_code, 400, data)
        self.assertFalse(Order.objects.exists())
        # 0 = not chosen yet: the app sends it
        self.assertEqual(self.checkout(payment_type=0).status_code, 201)

    def test_payment_on_delivery_refused(self):
        # launch audit B-03 (25.11.2026): only the card online is offered
        for method in ("cash", "card", None):
            response = self.checkout(payment_type=4, payment_method=method)
            self.assertEqual((response.status_code, response.data["error_code"]), (400, 5), method)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(CartItem.objects.count(), 1)

        order = Order.objects.create(customer=self.customer, payment_type=0)
        response = self.client.post("/api/v1/order/pay/", {"order_id": order.id, "payment_type": 4,
                                                          "payment_method": "cash"}, format="json")
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual((order.payment_type, order.payment_method), (0, None))

    def test_old_cash_order_stays_readable(self):
        order = Order.objects.create(customer=self.customer, payment_type=4, payment_method="cash",
                                     order_location=CustomerAddresses.objects.get(customer=self.customer))
        detail = self.client.get(f"/api/v1/order/{order.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual((detail.data["result"]["payment_type"], detail.data["result"]["payment_method"]), (4, "cash"))

        admin = APIClient()
        admin.force_authenticate(get_user_model().objects.create_user("admin", password="x", is_staff=True))
        row = admin.get(f"/api/v1/admin/orders/{order.id}/").data
        self.assertEqual((row["payment_type"], row["payment_method"]), (4, "cash"))
        self.assertEqual(admin.get("/api/v1/admin/orders/?payment_type=4").data["count"], 1)
        response = admin.patch(f"/api/v1/admin/orders/{order.id}/", {"receiver_name": "Ali"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data["payment_type"], response.data["payment_method"]), (4, "cash"))

    def test_empty_cart_refused(self):
        self.item.is_checked = False
        self.item.save()
        response = self.checkout()
        self.assertEqual((response.status_code, response.data["error_code"]), (400, 46))
        self.item.delete()
        self.assertEqual(self.checkout().status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_fixed_promocode_above_the_sum(self):
        Promocodes.objects.create(code="BIG", discount_price=100000, expires_at="2099-01-01", customer=self.customer)
        response = self.checkout(promocode="BIG", delivery_price="0")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Order.objects.get().total_price, 0)


class PasswordLoginTests(ApiTestCase):
    def login(self, phone):
        return APIClient().post("/api/v1/auth/login/", {"phone_number": phone, "password": "secret1"},
                                format="json")

    def test_unverified_phone_gets_no_tokens(self):
        Customer.objects.create(phone_number="+998900000202", password=make_password("secret1"))
        response = self.login("+998900000202")
        self.assertEqual((response.status_code, response.data["error_code"]), (403, 45))
        Customer.objects.filter(phone_number="+998900000202").update(verified=True)
        response = self.login("+998900000202")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.data)

    @mock.patch("apps.authorization.api.v1.client.views.EskizOTP.send_otp_service")
    def test_register_ignores_role(self, _):
        response = APIClient().post("/api/v1/auth/register/", {
            "full_name": "X", "phone_number": "+998900000203", "password": "secret1", "role": "prorab",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Customer.objects.get(phone_number="+998900000203").role, Customer.Role.USER)


class CatalogWriteEndpointsGoneTests(ApiTestCase):
    """The client API had open product / category / characteristic create and product rename (PTEST products 12014-12017)."""

    def test_no_catalog_writes_through_the_client_api(self):
        _, item_category = make_item_category("C")
        product = make_product("P1", item_category, 1000)
        client = APIClient()
        calls = [
            ("post", "/api/v1/products/create/", {"name": "X", "product_item_category": item_category.id, "price": 1}),
            ("patch", f"/api/v1/products/{product.id}/update/", {"name_ru": "X"}),
            ("post", "/api/v1/sub-categories/create/", {"name": "X", "product_category": item_category.id}),
            ("post", "/api/v1/item-categories/create/", {"name": "X", "product_sub_category": 1}),
            ("post", "/api/v1/characteristics/", {"product": product.id, "name": "X", "value": "1"}),
        ]
        for method, url, data in calls:
            self.assertIn(getattr(client, method)(url, data, format="json").status_code, (404, 405), url)
        product.refresh_from_db()
        self.assertEqual((product.name_ru, item_category.product_sub_category.product_category.product_category.count()),
                         ("P1", 1))
        self.assertEqual(Product.objects.count(), 1)
