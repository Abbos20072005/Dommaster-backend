"""PRO projects (BLD-290..293). Run: env/Scripts/python.exe manage.py test apps.service

Expected numbers are worked out by hand in `ProExpensesTests` (see the comments there)."""
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authorization.roles import change_role
from apps.authorization.api.v1.client.views import issue_customer_tokens
from apps.authorization.models import Customer, CustomerAddresses, OTP
from apps.base.models import Promocodes
from apps.service.models import (
    Cart, CartItem, Order, OrderItem, OrderItemProjectChange, Product, ProductCategory, ProductItemCategory, ProductSubCategory,
    Project,
)
from apps.service.pro import allocate

D = Decimal
PRO = Customer.Role.PRORAB


def make_customer(phone, role=Customer.Role.USER):
    return Customer.objects.create(phone_number=phone, full_name=phone, role=role)


def make_item_category(name):
    category = ProductCategory.objects.create(name=name, name_ru=name, name_uz=name)
    sub = ProductSubCategory.objects.create(product_category=category, name=name, name_ru=name, name_uz=name)
    return category, ProductItemCategory.objects.create(product_sub_category=sub, name=name, name_ru=name,
                                                        name_uz=name)


def make_product(code, item_category, price, discount_price=None):
    return Product.objects.create(name=code, name_ru=code, name_uz=code, description="", product_code=code,
                                  product_item_category=item_category, price=price, discount_price=discount_price,
                                  quantity=100)


def make_order(customer, lines, **fields):
    """`lines` = [(product, quantity)]; unit_price as checkout keeps it."""
    order = Order.objects.create(customer=customer, **fields)
    items = [OrderItem.objects.create(order=order, product=product, quantity=quantity,
                                      unit_price=OrderItem.unit_price_of(product)) for product, quantity in lines]
    return order, items


class ApiTestCase(TestCase):
    def client_for(self, customer):
        client = APIClient()
        access, _ = issue_customer_tokens(customer)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return client


class AllocateTests(TestCase):
    def test_parts_add_up(self):
        self.assertEqual(allocate(D("0.05"), [D(1), D(1), D(1)]), [D("0.02"), D("0.02"), D("0.01")])
        self.assertEqual(allocate(D("10000"), [D(180000), D(50000), D(70000)]),
                         [D("6000.00"), D("1666.67"), D("2333.33")])
        self.assertEqual(allocate(D("7"), [D(0), D(0)]), [D("3.50"), D("3.50")])
        self.assertEqual(allocate(D("0"), [D(5)]), [D("0.00")])


class RoleTests(ApiTestCase):
    def setUp(self):
        self.customer = make_customer("+998900000001")
        self.staff = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.admin = APIClient()
        self.admin.force_authenticate(self.staff)

    def test_grant_and_revoke_keep_history(self):
        url = f"/api/v1/admin/customers/{self.customer.id}/role/"
        response = self.admin.post(url, {"role": "prorab"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["role"], "prorab")
        self.assertEqual(self.admin.post(url, {"role": "prorab"}, format="json").status_code, 400)

        # revoking needs a reason
        self.assertEqual(self.admin.post(url, {"role": "user"}, format="json").status_code, 400)
        response = self.admin.post(url, {"role": "user", "reason": "Shartnoma tugadi"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

        history = self.admin.get(f"/api/v1/admin/customers/{self.customer.id}/role-history/").data
        self.assertEqual(history["count"], 2)
        latest = history["results"][0]
        self.assertEqual((latest["old_value"], latest["new_value"], latest["reason"]),
                         ("prorab", "user", "Shartnoma tugadi"))
        self.assertEqual(latest["changed_by"]["id"], self.staff.id)

        # the customers CRUD can't change the role (no history there)
        self.admin.patch(f"/api/v1/admin/customers/{self.customer.id}/", {"role": "prorab"}, format="json")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, "user")

    def test_customer_cannot_change_own_role(self):
        client = self.client_for(self.customer)
        me = client.get("/api/v1/auth/auth/me/").data["result"]
        self.assertEqual(me["role"], "user")
        client.patch("/api/v1/auth/customer/update/", {"role": "prorab", "full_name": "Ali"}, format="json")
        self.customer.refresh_from_db()
        self.assertEqual((self.customer.role, self.customer.full_name), ("user", "Ali"))

    def test_order_keeps_role(self):
        order = Order.objects.create(customer=self.customer)
        change_role(self.customer.id, PRO, self.staff)
        pro_order = Order.objects.create(customer=self.customer)
        order.refresh_from_db()
        self.assertEqual((order.role_at_order, pro_order.role_at_order), ("user", "prorab"))


class ProjectApiTests(ApiTestCase):
    def setUp(self):
        self.customer = make_customer("+998900000002", PRO)
        self.client_pro = self.client_for(self.customer)
        _, item_category = make_item_category("Santexnika")
        self.product = make_product("P1", item_category, 1000)

    def create(self, name, client=None):
        return (client or self.client_pro).post("/api/v1/pro/projects/", {"name": name, "address": "Chilonzor"},
                                                format="json")

    def test_plain_customer_gets_403_and_foreign_project_404(self):
        plain = make_customer("+998900000003")
        response = self.client_for(plain).get("/api/v1/pro/projects/")
        self.assertEqual((response.status_code, response.data["error_code"]), (403, 34))

        other = make_customer("+998900000004", PRO)
        project_id = self.create("Begona", self.client_for(other)).data["result"]["id"]
        self.assertEqual(self.client_pro.get(f"/api/v1/pro/projects/{project_id}/").status_code, 404)

    def test_name_rules(self):
        self.assertEqual(self.create("Uy").status_code, 400)  # < 3 characters
        first = self.create("Uy  qurilishi").data["result"]
        self.assertEqual(first["name"], "Uy qurilishi")
        response = self.create("uy qurilishi")
        self.assertEqual((response.status_code, response.data["error_code"]), (400, 35))

        # an archived project frees the name; restoring it then collides
        self.client_pro.post(f"/api/v1/pro/projects/{first['id']}/archive/")
        self.assertEqual(self.create("Uy qurilishi").status_code, 201)
        response = self.client_pro.post(f"/api/v1/pro/projects/{first['id']}/restore/")
        self.assertEqual((response.status_code, response.data["error_code"]), (400, 35))

    def test_delete_only_without_items(self):
        empty = self.create("Bo'sh loyiha").data["result"]["id"]
        used = self.create("Ishlatilgan").data["result"]["id"]
        order, _ = make_order(self.customer, [(self.product, 1)])
        self.client_pro.post(f"/api/v1/pro/orders/{order.id}/link/", {"project_id": used}, format="json")

        response = self.client_pro.delete(f"/api/v1/pro/projects/{used}/")
        self.assertEqual((response.status_code, response.data["error_code"]), (409, 36))
        self.assertEqual(self.client_pro.delete(f"/api/v1/pro/projects/{empty}/").status_code, 204)

    def test_revoked_pro_hides_projects(self):
        project = self.create("Dacha").data["result"]["id"]
        order, (item,) = make_order(self.customer, [(self.product, 2)])
        self.client_pro.post(f"/api/v1/pro/orders/{order.id}/link/", {"project_id": project}, format="json")
        detail = self.client_pro.get(f"/api/v1/order/{order.id}/").data["result"]
        self.assertEqual(detail["order_items"][0]["project"], {"id": project, "name": "Dacha"})

        change_role(self.customer.id, Customer.Role.USER, None, "test")
        self.assertEqual(self.client_pro.get("/api/v1/pro/projects/").status_code, 403)
        self.assertIsNone(self.client_pro.get(f"/api/v1/order/{order.id}/").data["result"]["order_items"][0]["project"])
        self.assertTrue(Project.objects.filter(id=project).exists())

        change_role(self.customer.id, PRO, None)
        self.assertEqual(len(self.client_pro.get("/api/v1/pro/projects/").data["result"]), 1)


class LinkTests(ApiTestCase):
    def setUp(self):
        self.customer = make_customer("+998900000005", PRO)
        self.client_pro = self.client_for(self.customer)
        self.category, item_category = make_item_category("Elektr")
        product = make_product("P1", item_category, 1000)
        self.order, self.items = make_order(self.customer, [(product, 1), (make_product("P2", item_category, 500), 3)])
        self.house = Project.objects.create(customer=self.customer, name="Uy")
        self.office = Project.objects.create(customer=self.customer, name="Ofis")
        self.url = f"/api/v1/pro/orders/{self.order.id}/link/"

    def test_conflict_then_force(self):
        response = self.client_pro.post(self.url, {"project_id": self.house.id}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(OrderItem.objects.get(id=self.items[0].id).category_root_id, self.category.id)

        # one item to another project: 409, nothing changed
        body = {"project_id": self.office.id, "item_ids": [self.items[1].id]}
        response = self.client_pro.post(self.url, body, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["detail"]["conflicting_item_ids"], [self.items[1].id])
        self.assertEqual(OrderItem.objects.get(id=self.items[1].id).project_id, self.house.id)

        response = self.client_pro.post(self.url, {**body, "force": True}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item["project"]["id"] for item in response.data["result"]["order_items"]],
                         [self.house.id, self.office.id])
        actions = list(OrderItemProjectChange.objects.order_by("id").values_list("action", flat=True))
        self.assertEqual(actions, ["link", "link", "move"])

        self.client_pro.post(f"/api/v1/pro/orders/{self.order.id}/unlink/", {"item_ids": [self.items[0].id]},
                             format="json")
        self.assertIsNone(OrderItem.objects.get(id=self.items[0].id).project_id)
        unlinked = self.client_pro.get("/api/v1/pro/orders/unlinked/").data["result"]["content"]
        self.assertEqual([(row["id"], row["unlinked_items_count"]) for row in unlinked], [(self.order.id, 1)])

    def test_refused_links(self):
        self.house.status = Project.ARCHIVED
        self.house.save()
        response = self.client_pro.post(self.url, {"project_id": self.house.id}, format="json")
        self.assertEqual((response.status_code, response.data["error_code"]), (400, 38))

        Order.objects.filter(id=self.order.id).update(status=4)
        response = self.client_pro.post(self.url, {"project_id": self.office.id}, format="json")
        self.assertEqual((response.status_code, response.data["error_code"]), (400, 39))

        foreign = Order.objects.create(customer=make_customer("+998900000006", PRO))
        response = self.client_pro.post(f"/api/v1/pro/orders/{foreign.id}/link/", {"project_id": self.office.id},
                                        format="json")
        self.assertEqual(response.status_code, 404)


class ProExpensesTests(ApiTestCase):
    """Two projects, four orders.

    Products: P1 100 000 with discount 90 000 (category A), P2 50 000 and P3 70 000 (category B).

    Order 1 - paid, promocode discount 10 000, delivery 25 000, split between the projects:
        P1 × 2 = 180 000 -> house  promo 6 000.00  delivery 15 000.00  goods 174 000.00
        P2 × 1 =  50 000 -> office promo 1 666.67  delivery  4 166.67  goods  48 333.33
        P3 × 1 =  70 000 -> house  promo 2 333.33  delivery  5 833.33  goods  67 666.67
        (10 000 / 300 000 and 25 000 / 300 000 of each sum; the cent left by rounding goes to the biggest remainder,
        P2's .667)
    Order 2 - paid, pickup (its delivery_price 15 000 is not charged): P2 × 4 = 200 000 -> office; P1 × 1 not linked
    Order 3 - canceled (payment Paid): P1 × 1 -> house, not counted
    Order 4 - not paid: P2 × 1 -> house, not counted

    house:  goods 174 000 + 67 666.67 = 241 666.67, delivery 15 000 + 5 833.33 = 20 833.33, total 262 500.00
    office: goods 48 333.33 + 200 000 = 248 333.33, delivery 4 166.67, total 252 500.00
    all:    goods 490 000.00, delivery 25 000.00, total 515 000.00
    categories: A = 174 000.00, B = 48 333.33 + 67 666.67 + 200 000 = 316 000.00 (adds up to the goods)
    """

    def setUp(self):
        self.customer = make_customer("+998900000007", PRO)
        self.client_pro = self.client_for(self.customer)
        self.category_a, item_a = make_item_category("A")
        self.category_b, item_b = make_item_category("B")
        p1 = make_product("P1", item_a, 100000, 90000)
        p2 = make_product("P2", item_b, 50000)
        p3 = make_product("P3", item_b, 70000)
        self.house = Project.objects.create(customer=self.customer, name="Uy")
        self.office = Project.objects.create(customer=self.customer, name="Ofis")

        order1, items1 = make_order(self.customer, [(p1, 2), (p2, 1), (p3, 1)], payment_status=2,
                                    delivery_type=0, delivery_price=25000, promocode_discount=10000)
        order2, items2 = make_order(self.customer, [(p2, 4), (p1, 1)], payment_status=2, delivery_type=1,
                                    delivery_price=15000, promocode_discount=0)
        order3, _ = make_order(self.customer, [(p1, 1)], payment_status=2, delivery_type=0, delivery_price=10000)
        order4, _ = make_order(self.customer, [(p2, 1)], payment_status=0)

        self.link(order1, self.house)
        self.link(order1, self.office, [items1[1].id], force=True)
        self.link(order2, self.office, [items2[0].id])
        self.link(order3, self.house)
        self.link(order4, self.house)
        Order.objects.filter(id=order3.id).update(status=4)
        Order.objects.filter(id__in=[order1.id, order2.id]).update(status=3)

    def link(self, order, project, item_ids=None, force=False):
        body = {"project_id": project.id, "force": force, **({"item_ids": item_ids} if item_ids else {})}
        response = self.client_pro.post(f"/api/v1/pro/orders/{order.id}/link/", body, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    @staticmethod
    def money(row, *keys):
        return tuple(D(row[key]) for key in keys)

    def test_dashboard(self):
        result = self.client_pro.get("/api/v1/pro/dashboard/").data["result"]
        totals = result["totals"]
        self.assertEqual(self.money(totals, "goods", "delivery", "total"), (D("490000"), D("25000"), D("515000")))
        self.assertEqual((totals["orders_count"], totals["items_count"]), (2, 4))

        projects = {row["id"]: row for row in result["projects"]}
        self.assertEqual(self.money(projects[self.house.id], "goods", "delivery", "total"),
                         (D("241666.67"), D("20833.33"), D("262500.00")))
        self.assertEqual(self.money(projects[self.office.id], "goods", "delivery", "total"),
                         (D("248333.33"), D("4166.67"), D("252500.00")))

        categories = [(row["id"], D(row["goods"])) for row in result["categories"]]
        self.assertEqual(categories, [(self.category_b.id, D("316000.00")), (self.category_a.id, D("174000.00"))])
        self.assertEqual(sum(goods for _, goods in categories), D(totals["goods"]))

    def test_project_summary_and_items(self):
        summary = self.client_pro.get(f"/api/v1/pro/projects/{self.house.id}/summary/").data["result"]
        self.assertEqual(self.money(summary["totals"], "goods", "delivery", "total"),
                         (D("241666.67"), D("20833.33"), D("262500.00")))
        self.assertEqual({row["id"]: D(row["goods"]) for row in summary["categories"]},
                         {self.category_a.id: D("174000.00"), self.category_b.id: D("67666.67")})

        page = self.client_pro.get(f"/api/v1/pro/projects/{self.office.id}/items/?page_size=1").data["result"]
        self.assertEqual((page["totalElements"], page["numberOfElements"]), (2, 1))
        page = self.client_pro.get(f"/api/v1/pro/projects/{self.office.id}/items/?page_size=5").data["result"]
        rows = sorted((self.money(row, "amount", "discount", "goods", "delivery") for row in page["content"]))
        self.assertEqual(rows, [(D("50000"), D("1666.67"), D("48333.33"), D("4166.67")),
                                (D("200000"), D("0"), D("200000"), D("0"))])

    def test_period_filter(self):
        Order.objects.filter(order_items__project=self.office, delivery_type=1).update(created_at="2026-01-10")
        result = self.client_pro.get("/api/v1/pro/dashboard/?from=2026-01-01&to=2026-01-31").data["result"]
        self.assertEqual(self.money(result["totals"], "goods", "delivery"), (D("200000"), D("0")))
        response = self.client_pro.get("/api/v1/pro/dashboard/?from=2026-02-01&to=2026-01-01")
        self.assertEqual(response.status_code, 400)


class UnchangedFlowsTests(ApiTestCase):
    """Phone login, cart and checkout work as before for a PRO customer; checkout keeps the new snapshots."""

    def setUp(self):
        self.customer = make_customer("+998900000008", PRO)
        _, item_category = make_item_category("C")
        self.p1 = make_product("P1", item_category, 100000, 90000)
        self.p2 = make_product("P2", item_category, 50000)

    @mock.patch("apps.authorization.api.v1.client.views.is_telegram_linked", return_value=False)
    @mock.patch("apps.authorization.api.v1.client.views.EskizOTP.send_otp_service")
    def test_phone_login(self, send_sms, _):
        client = APIClient()
        response = client.post("/api/v1/auth/auth/phone/", {"phone_number": self.customer.phone_number},
                               format="json")
        self.assertEqual(response.status_code, 200, response.data)
        send_sms.assert_called_once()
        otp = OTP.objects.get(otp_key=response.data["result"]["otp_key"])
        response = client.post("/api/v1/auth/otp/verify/", {"otp_key": otp.otp_key, "otp_code": otp.otp_code},
                               format="json")
        self.assertEqual(response.status_code, 200, response.data)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['result']['access_token']}")
        self.assertEqual(client.get("/api/v1/auth/auth/me/").data["result"]["role"], "prorab")

    def test_checkout(self):
        cart = Cart.objects.create(customer=self.customer)
        CartItem.objects.create(cart=cart, product=self.p1, quantity=2)
        CartItem.objects.create(cart=cart, product=self.p2, quantity=1)
        cart.refresh_from_db()
        self.assertEqual((cart.total_price, cart.saved_price), (230000.0, 20000.0))

        CustomerAddresses.objects.create(customer=self.customer, name="Uy", is_default=True)
        Promocodes.objects.create(customer=self.customer, name="10%", code="PRO10", discount_precent=10,
                                  expires_at=date.today() + timedelta(days=1))
        response = self.client_for(self.customer).post("/api/v1/order/", {
            "payment_type": 1, "promocode": "PRO10", "delivery_type": 0, "delivery_price": "20000",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)

        order = Order.objects.get(id=response.data["order_id"])
        # 230 000 - 10 % + 20 000 delivery, as before
        self.assertEqual((order.total_price, order.products_total_price, order.saved_price),
                         (227000.0, 250000.0, 20000.0))
        self.assertIn("amount=227000.0", response.data["result"])
        self.assertEqual((order.promocode_discount, order.role_at_order), (D("23000.00"), "prorab"))
        self.assertEqual(sorted(order.order_items.values_list("unit_price", "quantity")),
                         [(D("50000.00"), 1), (D("90000.00"), 2)])
        self.assertFalse(CartItem.objects.filter(cart=cart).exists())
