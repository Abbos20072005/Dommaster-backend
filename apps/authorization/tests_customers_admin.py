"""Admin customers page: new fields, filters, stats, soft delete, logout-all, notes, journal, masked phone.
Run: manage.py test apps.authorization.tests_customers_admin"""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authorization.activity import mask_phone
from apps.authorization.api.v1.client.views import issue_customer_tokens
from apps.authorization.models import Customer, CustomerActivity, FcmToken, OTP
from apps.service.models import Order

URL = "/api/v1/admin/customers/"
ADDRESSES = "/api/v1/auth/customer/addresses/"


def make_customer(phone, **fields):
    return Customer.objects.create(phone_number=phone, full_name=phone, **fields)


class CustomersAdminTest(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.ali = make_customer("+998901234567", registration_channel="ios")
        self.vali = make_customer("+998931112233", registration_channel="site")

    def customer_client(self, customer):
        client = APIClient()
        access, refresh = issue_customer_tokens(customer)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return client, refresh

    def ids(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return {row["id"] for row in response.json()["results"]}

    def test_mask_phone(self):
        self.assertEqual(mask_phone("+998901234567"), "+998 90 *** ** 67")

    def test_list_fields_and_masked_phone(self):
        Order.objects.create(customer=self.ali, status=3, total_price=100)
        Order.objects.create(customer=self.ali, status=4, total_price=50)
        FcmToken.objects.create(customer=self.ali, device_id="d1", fcm_token="t1", platform="ios")
        FcmToken.objects.create(customer=self.ali, device_id="d2", fcm_token="t2", platform="android")
        row = next(r for r in self.client.get(URL).json()["results"] if r["id"] == self.ali.id)
        self.assertEqual(row["phone_number"], "+998 90 *** ** 67")
        self.assertEqual((row["orders_count"], row["returns_count"], row["active_devices"]), (1, 1, 2))
        self.assertEqual(row["registration_channel"], "ios")
        self.assertIsNotNone(row["last_order_at"])

    def test_reveal_phone_is_journaled(self):
        response = self.client.post(f"{URL}{self.ali.id}/reveal-phone/")
        self.assertEqual(response.json()["phone_number"], "+998901234567")
        activity = self.client.get(f"{URL}{self.ali.id}/activity/").json()["results"]
        self.assertEqual(activity[0]["kind"], "phone_revealed")
        self.assertEqual(activity[0]["channel"], "admin")
        self.assertEqual(activity[0]["actor"]["id"], self.admin.id)

    def test_filters(self):
        Order.objects.create(customer=self.ali, status=3, total_price=500)
        Order.objects.create(customer=self.vali, status=4, total_price=10)
        android = make_customer("+998941112233", registration_channel="android")
        self.assertEqual(self.ids(self.client.get(URL, {"registration_channel": "ios,android"})),
                         {self.ali.id, android.id})
        self.assertEqual(self.ids(self.client.get(URL + "?registration_channel=ios&registration_channel=site")),
                         {self.ali.id, self.vali.id})
        self.assertEqual(self.client.get(URL, {"registration_channel": "web"}).status_code, 400)
        self.assertEqual(self.ids(self.client.get(URL, {"purchase_min": 100})), {self.ali.id})
        self.assertEqual(self.ids(self.client.get(URL, {"orders_min": 1, "orders_max": 1})), {self.ali.id})
        self.assertEqual(self.ids(self.client.get(URL, {"has_returns": "true"})), {self.vali.id})
        today = timezone.now().date().isoformat()
        self.assertEqual(self.ids(self.client.get(URL, {"last_order_from": today})), {self.ali.id, self.vali.id})

    def test_search_by_order_number(self):
        order = Order.objects.create(customer=self.vali, status=0, total_price=10)
        self.assertEqual(self.ids(self.client.get(URL, {"search": f"#{order.id}"})), {self.vali.id})
        self.assertEqual(self.ids(self.client.get(URL, {"search": "90 123"})), {self.ali.id})

    def test_ordering_by_last_order(self):
        Order.objects.create(customer=self.vali, status=0)
        rows = self.client.get(URL, {"ordering": "-last_order_at"}).json()["results"]
        self.assertEqual(rows[0]["id"], self.vali.id)

    def test_patch_segment_tags_language_journal(self):
        response = self.client.patch(f"{URL}{self.ali.id}/", {"segment": "vip", "tags": [" opt ", "Opt", "b2b"],
                                                               "language": "uz", "is_blocked": True}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["tags"], ["opt", "b2b"])
        self.assertEqual(self.ids(self.client.get(URL, {"segment": "vip"})), {self.ali.id})
        self.assertEqual(self.ids(self.client.get(URL, {"tag": "b2b"})), {self.ali.id})
        kinds = [a["kind"] for a in self.client.get(f"{URL}{self.ali.id}/activity/").json()["results"]]
        self.assertCountEqual(kinds, ["updated", "blocked"])

    def test_admin_delete_is_soft(self):
        Order.objects.create(customer=self.ali, status=3, total_price=1)
        client, _ = self.customer_client(self.ali)
        self.assertEqual(self.client.delete(f"{URL}{self.ali.id}/").status_code, 204)
        self.ali.refresh_from_db()
        self.assertTrue(self.ali.is_deleted)
        self.assertEqual(Order.objects.filter(customer=self.ali).count(), 1)
        self.assertNotIn(self.ali.id, self.ids(self.client.get(URL)))
        self.assertEqual(self.ids(self.client.get(URL, {"is_deleted": "true"})), {self.ali.id})
        self.assertEqual(self.client.get(f"{URL}{self.ali.id}/").status_code, 200)
        self.assertNotEqual(client.get(ADDRESSES).status_code, 200)  # its token is dead
        stats = self.client.get(f"{URL}stats/").json()
        self.assertEqual((stats["total"], stats["deleted"], stats["ordered_30d"]), (1, 1, 0))

    def test_client_delete_is_soft_and_phone_gets_new_account(self):
        client, _ = self.customer_client(self.ali)
        self.assertEqual(client.delete("/api/v1/auth/delete/account/").status_code, 204)
        self.assertTrue(Customer.objects.get(pk=self.ali.pk).is_deleted)
        with mock.patch("apps.authorization.api.v1.client.views.EskizOTP.send_otp_service"):
            response = APIClient().post("/api/v1/auth/auth/phone/", {"phone_number": "998901234567",
                                                                     "platform": "android"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["result"]["is_new"])
        new = Customer.objects.filter(phone_number="+998901234567", is_deleted=False).get()
        self.assertEqual(new.registration_channel, "android")

    def test_logout_all(self):
        FcmToken.objects.create(customer=self.ali, device_id="d1", fcm_token="t1")
        self.ali.tokens_valid_after = None
        self.ali.save()
        client, refresh = self.customer_client(self.ali)
        self.assertEqual(client.get(ADDRESSES).status_code, 200)
        # tokens are refused when issued before the cutoff (iat has 1 s precision, so move the cutoff forward)
        with mock.patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(seconds=2)):
            self.assertEqual(self.client.post(f"{URL}{self.ali.id}/logout-all/").status_code, 204)
        self.assertFalse(FcmToken.objects.filter(customer=self.ali).exists())
        self.assertNotEqual(client.get(ADDRESSES).status_code, 200)
        response = APIClient().post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertNotEqual(response.status_code, 200)

    def test_notes(self):
        other = get_user_model().objects.create_user("other", password="x", is_staff=True)
        response = self.client.post(f"{URL}{self.ali.id}/notes/", {"text": "  call back  "}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        note_id = response.json()["id"]
        self.assertEqual(self.client.post(f"{URL}{self.ali.id}/notes/", {"text": " "}, format="json").status_code,
                         400)
        notes = self.client.get(f"{URL}{self.ali.id}/notes/").json()["results"]
        self.assertEqual((notes[0]["text"], notes[0]["author"]["id"]), ("call back", self.admin.id))
        other_client = APIClient()
        other_client.force_authenticate(other)
        self.assertEqual(other_client.delete(f"{URL}{self.ali.id}/notes/{note_id}/").status_code, 403)
        self.assertEqual(self.client.delete(f"{URL}{self.vali.id}/notes/{note_id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"{URL}{self.ali.id}/notes/{note_id}/").status_code, 204)

    def test_otp_verify_journal_and_platform(self):
        new = make_customer("+998951112233")
        otp = OTP.objects.create(customer=new, otp_code=12345, expire_at=timezone.now() + timedelta(minutes=2))
        response = APIClient().post("/api/v1/auth/otp/verify/", {"otp_key": str(otp.otp_key), "otp_code": 12345,
                                                                  "platform": "ios"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        new.refresh_from_db()
        self.assertEqual((new.registration_channel, new.last_login_platform), ("ios", "ios"))
        event = CustomerActivity.objects.get(customer=new)
        self.assertEqual((event.kind, event.channel), ("registered", "ios"))

    def test_client_language_is_kept(self):
        client, _ = self.customer_client(self.ali)
        # the once-a-day guard lives in the shared Redis; test db ids repeat between runs
        with mock.patch("apps.authorization.visits.cache.add", return_value=True):
            client.get(ADDRESSES, HTTP_ACCEPT_LANGUAGE="uz")
        self.ali.refresh_from_db()
        self.assertEqual(self.ali.language, "uz")
