"""Removed pages (BLD-270): `seo/resolve` `gone` for hidden / deleted products, 410 for a deleted news,
304 for conditional GETs.

Run: env/Scripts/python.exe manage.py test apps.service.tests_seo_gone
"""
import os
import shutil
import tempfile

from django.test import TestCase, override_settings
from django.utils.http import http_date
from rest_framework.test import APIClient

from apps.base.models import News
from apps.service import merchant_feed, seo_redirects
from apps.service.models import AlternativeProduct, DeletedObject, Product, ProductItemCategory
from apps.service.tests import make_item_category, make_product


class GoneProductTests(TestCase):
    def setUp(self):
        self.category, self.item_category = make_item_category("Выключатели")
        self.sub_category = self.item_category.product_sub_category
        self.product = make_product("Выключатель Asfora", self.item_category, 100)
        self.alternative = make_product("Выключатель Glossa", self.item_category, 90)

    def resolve(self, slug):
        return seo_redirects.resolve("product", slug, "ru")

    def hide(self, product):
        Product.objects.filter(pk=product.pk).update(is_active=False)

    def test_active_product_is_current(self):
        result = self.resolve(self.product.slug_ru)
        self.assertEqual((result["status"], result["redirect"]), ("current", None))

    def test_bare_id_of_an_active_product_is_moved(self):
        result = self.resolve(str(self.product.pk))
        self.assertEqual((result["status"], result["slug"]), ("moved", self.product.slug_ru))

    def test_hidden_product_goes_to_its_alternative(self):
        AlternativeProduct.objects.create(product=self.product, linked_product=self.alternative, position=0)
        self.hide(self.product)
        result = self.resolve(self.product.slug_ru)
        self.assertEqual(result["status"], "gone")
        self.assertEqual(result["id"], self.product.pk)
        redirect = result["redirect"]
        self.assertEqual((redirect["type"], redirect["id"], redirect["slug"]),
                         ("product", self.alternative.pk, self.alternative.slug_ru))
        self.assertEqual([crumb["level"] for crumb in redirect["breadcrumbs"]],
                         ["product_category", "product_sub_category", "product_item_category", "product"])

    def test_hidden_alternative_is_skipped(self):
        AlternativeProduct.objects.create(product=self.product, linked_product=self.alternative, position=0)
        self.hide(self.product)
        self.hide(self.alternative)
        redirect = self.resolve(self.product.slug_ru)["redirect"]
        self.assertEqual((redirect["type"], redirect["id"]), ("item_category", self.item_category.pk))
        self.assertEqual(redirect["slug"], self.item_category.slug_ru)

    def test_inactive_item_category_falls_back_to_the_sub_category(self):
        self.hide(self.product)
        ProductItemCategory.objects.filter(pk=self.item_category.pk).update(is_active=False)
        redirect = self.resolve(self.product.slug_ru)["redirect"]
        self.assertEqual((redirect["type"], redirect["id"]), ("sub_category", self.sub_category.pk))

    def test_no_active_level_means_410(self):
        self.hide(self.product)
        for level in (self.item_category, self.sub_category, self.category):
            type(level).objects.filter(pk=level.pk).update(is_active=False)
        result = self.resolve(self.product.slug_ru)
        self.assertEqual((result["status"], result["redirect"]), ("gone", None))

    def test_deleted_product_goes_to_the_alternative_it_had(self):
        AlternativeProduct.objects.create(product=self.product, linked_product=self.alternative, position=0)
        slug, pk = self.product.slug_ru, self.product.pk
        self.product.delete()
        row = DeletedObject.objects.get(object_id=pk)
        self.assertEqual((row.item_category_id, row.alternative_ids), (self.item_category.pk, [self.alternative.pk]))
        result = self.resolve(slug)
        self.assertEqual((result["status"], result["id"]), ("gone", pk))
        self.assertEqual(result["redirect"]["id"], self.alternative.pk)

    def test_deleted_product_without_alternative_goes_to_its_category(self):
        pk = self.product.pk
        self.product.delete()
        redirect = self.resolve(str(pk))["redirect"]
        self.assertEqual((redirect["type"], redirect["id"]), ("item_category", self.item_category.pk))

    def test_deleted_with_its_category(self):
        pk = self.product.pk
        self.item_category.delete()
        result = self.resolve(f"vyklyuchatel-asfora-{pk}")
        # only the item category id is kept, and it is gone too -> 410
        self.assertEqual((result["status"], result["redirect"]), ("gone", None))

    def test_unknown_slug_is_not_found(self):
        self.assertIsNone(self.resolve("net-takogo-tovara"))
        response = APIClient().get("/api/v1/seo/resolve/", {"type": "product", "slug": "net-takogo-tovara"})
        self.assertEqual(response.data["result"]["status"], "not_found")
        self.assertIsNone(response.data["result"]["redirect"])

    def test_endpoint(self):
        self.hide(self.product)
        response = APIClient().get("/api/v1/seo/resolve/", {"type": "product", "slug": self.product.slug_ru})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["result"]["redirect"]["type"], "item_category")


class DeletedNewsTests(TestCase):
    def setUp(self):
        self.news = News.objects.create(title_ru="Новость", title_uz="Yangilik", description_ru="Текст",
                                        image="news/x.png")

    def test_deleted_news_is_410(self):
        pk = self.news.pk
        self.news.delete()
        response = APIClient().get(f"/api/v1/base/news/{pk}/")
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.data["error_code"], 40)

    def test_never_existed_is_404(self):
        response = APIClient().get(f"/api/v1/base/news/{self.news.pk + 100}/")
        self.assertEqual(response.status_code, 404)


class ConditionalGetTests(TestCase):
    def test_etag_gives_304(self):
        news = News.objects.create(title_ru="Новость", description_ru="Текст", image="news/x.png")
        client = APIClient()
        first = client.get(f"/api/v1/base/news/{news.pk}/")
        self.assertTrue(first.has_header("ETag"))
        second = client.get(f"/api/v1/base/news/{news.pk}/", HTTP_IF_NONE_MATCH=first["ETag"])
        self.assertEqual(second.status_code, 304)

    def test_feed_last_modified(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, True)
        with override_settings(MEDIA_ROOT=media):
            path = merchant_feed.feed_path(merchant_feed.GOOGLE_FILE)
            os.makedirs(os.path.dirname(path))
            with open(path, "w") as file:
                file.write("<rss/>")
            os.utime(path, (1700000000, 1700000000))
            client = APIClient()
            first = client.get("/api/v1/feeds/google.xml")
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first["Last-Modified"], http_date(1700000000))
            first.close()
            second = client.get("/api/v1/feeds/google.xml", HTTP_IF_MODIFIED_SINCE=http_date(1700000000))
            self.assertEqual(second.status_code, 304)
            changed = client.get("/api/v1/feeds/google.xml", HTTP_IF_MODIFIED_SINCE=http_date(1690000000))
            self.assertEqual(changed.status_code, 200)
            changed.close()
