"""Product slugs follow a rename (`SeoFieldsMixin.SLUG_FOLLOWS_NAME`) + `backfill_seo_slugs --products`."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.service import seo_redirects
from apps.service.models import Brand, Product
from apps.service.tests import make_item_category, make_product


class ProductSlugFollowsNameTests(TestCase):
    def setUp(self):
        _, self.item_category = make_item_category("Выключатели")
        self.product = make_product("Выключатель Asfora антрацит", self.item_category, 100)

    def reload(self):
        return Product.objects.get(pk=self.product.pk)

    def test_new_product_slug(self):
        self.assertEqual(self.product.slug_ru, f"vyklyuchatel-asfora-antratsit-{self.product.pk}")

    def test_rename_moves_the_generated_slug(self):
        self.product.name_ru = "Выключатель Asfora 10 А, антрацит"
        self.product.save()
        product = self.reload()
        self.assertEqual(product.slug_ru, f"vyklyuchatel-asfora-10-a-antratsit-{product.pk}")
        # uz has its own name, which did not change
        self.assertEqual(product.slug_uz, f"vyklyuchatel-asfora-antratsit-{product.pk}")

    def test_rename_with_update_fields(self):
        self.product.name_ru = "Шуруп М400 25 кг"
        self.product.save(update_fields=["name_ru"])
        self.assertEqual(self.reload().slug_ru, f"shurup-m400-25-kg-{self.product.pk}")

    def test_uz_slug_from_ru_name_follows_it(self):
        Product.objects.filter(pk=self.product.pk).update(name_uz=None)
        product = self.reload()
        product.name_ru = "Автомат 16 A 1P"
        product.save()
        self.assertEqual(self.reload().slug_uz, f"avtomat-16-a-1p-{product.pk}")

    def test_hand_made_slug_stays(self):
        Product.objects.filter(pk=self.product.pk).update(slug_ru="asfora-po-akcii")
        product = self.reload()
        product.name_ru = "Выключатель Asfora 10 А"
        product.save()
        self.assertEqual(self.reload().slug_ru, "asfora-po-akcii")

    def test_slug_sent_with_the_rename_wins(self):
        self.product.name_ru = "Выключатель Asfora 10 А"
        self.product.slug_ru = "my-slug"
        self.product.save()
        self.assertEqual(self.reload().slug_ru, "my-slug")

    def test_other_field_update_leaves_the_slug(self):
        Product.objects.filter(pk=self.product.pk).update(name_ru="Новое имя")
        product = self.reload()
        product.price = 200
        product.save(update_fields=["price"])
        self.assertEqual(self.reload().slug_ru, f"vyklyuchatel-asfora-antratsit-{product.pk}")

    def test_brand_slug_is_still_stable(self):
        brand = Brand.objects.create(name="Weber", name_ru="Weber", name_uz="Weber")
        brand.name_ru = "Weber Saint-Gobain"
        brand.save()
        self.assertEqual(Brand.objects.get(pk=brand.pk).slug_ru, "weber")


class RefreshProductSlugsCommandTests(TestCase):
    def setUp(self):
        _, item_category = make_item_category("Выключатели")
        self.stale = make_product("Выключатель Asfora антрацит", item_category, 100)
        self.fresh = make_product("Розетка", item_category, 100)
        # renamed without the slug following (as before SLUG_FOLLOWS_NAME)
        Product.objects.filter(pk=self.stale.pk).update(name_ru="Выключатель Asfora 10 А, антрацит")

    def run_command(self, *args):
        out = StringIO()
        call_command("backfill_seo_slugs", "--products", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_saves_nothing(self):
        output = self.run_command("--dry-run")
        self.assertIn("would refresh 1 row(s)", output)
        self.assertEqual(Product.objects.get(pk=self.stale.pk).slug_ru,
                         f"vyklyuchatel-asfora-antratsit-{self.stale.pk}")

    def test_refreshes_only_stale_slugs(self):
        fresh_slug = self.fresh.slug_ru
        output = self.run_command()
        self.assertIn("refreshed 1 row(s) (slug_uz 0, slug_ru 1)", output)
        self.assertEqual(Product.objects.get(pk=self.stale.pk).slug_ru,
                         f"vyklyuchatel-asfora-10-a-antratsit-{self.stale.pk}")
        self.assertEqual(Product.objects.get(pk=self.fresh.pk).slug_ru, fresh_slug)
        self.assertIn("refreshed 0 row(s)", self.run_command())


class ResolveRenamedProductTests(TestCase):
    def setUp(self):
        _, item_category = make_item_category("Выключатели")
        self.product = make_product("Выключатель Asfora антрацит", item_category, 100)
        self.old_slug = self.product.slug_ru
        self.product.name_ru = "Выключатель Asfora 10 А, антрацит"
        self.product.save()

    def test_old_slug_is_moved_by_its_id(self):
        result = seo_redirects.resolve("product", self.old_slug, "ru")
        self.assertEqual(result, {"status": "moved", "type": "product", "id": self.product.pk,
                                  "slug": f"vyklyuchatel-asfora-10-a-antratsit-{self.product.pk}", "redirect": None})

    def test_current_slug(self):
        result = seo_redirects.resolve("product", Product.objects.get(pk=self.product.pk).slug_ru, "ru")
        self.assertEqual(result["status"], "current")

    def test_unknown_id_is_not_found(self):
        self.assertIsNone(seo_redirects.resolve("product", "vyklyuchatel-999999", "ru"))
        self.assertIsNone(seo_redirects.resolve("product", "vyklyuchatel", "ru"))

    def test_hidden_product_is_gone(self):
        # more cases in tests_seo_gone.py
        Product.objects.filter(pk=self.product.pk).update(is_active=False)
        self.assertEqual(seo_redirects.resolve("product", self.old_slug, "ru")["status"], "gone")

    def test_brand_slug_with_a_number_is_not_taken_as_an_id(self):
        self.assertIsNone(seo_redirects.resolve("brand", f"weber-{self.product.pk}", "ru"))
