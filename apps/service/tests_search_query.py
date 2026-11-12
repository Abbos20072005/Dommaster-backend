"""Text search (`apps/service/search.py`): the other script, codes, brand noise, relevance, and the assistant's
`search_products` tool keeping only the products that carry the query words.

Run: env/Scripts/python.exe manage.py test apps.service.tests_search_query
"""
from apps.service import search
from apps.service.assistant import tools
from apps.service.models import Brand, Product
from apps.service.tests import ApiTestCase, make_item_category, make_product


def found(q):
    return set(search.search_products(Product.objects.filter(is_active=True), q).values_list("id", flat=True))


class QueryFormTests(ApiTestCase):
    def test_cyrillic_to_uzbek_latin(self):
        self.assertEqual(search.query_variants("қувур"), ["қувур", "quvur"])
        self.assertEqual(search.query_variants("бўёқ"), ["бўёқ", "bo'yoq"])
        self.assertEqual(search.query_variants("кафел елими"), ["кафел елими", "kafel yelimi"])
        self.assertEqual(search.query_variants("ғишт ҳовли"), ["ғишт ҳовли", "g'isht hovli"])

    def test_latin_to_cyrillic(self):
        self.assertEqual(search.query_variants("laminat"), ["laminat", "ламинат"])
        # sizes stay as they are, written one way
        self.assertEqual(search.query_variants("Gazablok 600х300×200"), ["gazablok 600x300x200", "газаблок 600x300x200"])
        self.assertEqual(search.query_variants("600x300"), ["600x300"])

    def test_code(self):
        self.assertTrue(search.is_code("ai91303"))
        self.assertTrue(search.is_code("LC1-D09M7"))
        self.assertFalse(search.is_code("perforator"))
        self.assertFalse(search.is_code("M6"))
        self.assertFalse(search.is_code("kabel 3x2.5"))


class SearchTests(ApiTestCase):
    def setUp(self):
        _, self.category = make_item_category("Santexnika")
        self.pipe = self.product("P1", "Труба PPR 20 мм", "PPR quvur 20 mm")
        self.laminate = self.product("P2", "Ламинат 8 мм дуб", "Laminat 8 mm")
        self.paint = self.product("P3", "Краска водоэмульсионная", "Suv emulsiyali bo'yoq")
        self.paint.articul_code = "AI-91303"
        self.paint.save()
        boou = Brand.objects.create(name="Boou", name_ru="Boou", name_uz="Boou")
        self.shower = self.product("P4", "Душевой шланг BOOU SH501", "Dush shlangi BOOU SH501", brand=boou)

    def product(self, code, ru, uz, brand=None):
        product = make_product(code, self.category, 100_000)
        product.name, product.name_ru, product.name_uz, product.brand = ru, ru, uz, brand
        product.save()
        return product

    def test_other_script(self):
        self.assertIn(self.pipe.pk, found("қувур"))
        self.assertIn(self.paint.pk, found("бўёқ"))
        self.assertIn(self.laminate.pk, found("laminat"))

    def test_articul(self):
        for q in ("ai91303", "AI91303", "ai-91303"):
            self.assertEqual(found(q), {self.paint.pk}, q)
        ranked = search.search_products(Product.objects.all(), "ai91303").values_list("similarity", flat=True)
        self.assertEqual(list(ranked), [1.0])

    def test_brand_sharing_a_few_letters_is_not_a_match(self):
        # "boyler" / "Boou" share 2 trigrams (similarity 0.2): before, every product of the brand was found
        self.assertNotIn(self.shower.pk, found("boyler"))
        self.assertIn(self.shower.pk, found("boou"))


class RelevanceTests(ApiTestCase):
    def test_words(self):
        self.assertEqual(search.relevance("клинкерная плитка", "Плитка керамическая 30x30"), 0.5)
        self.assertEqual(search.relevance("холодный асфальт", "Холодный АСФАЛЬТ WEBER"), 1.0)
        self.assertEqual(search.relevance("boyler", "Otboy bolg'a"), 0.0)
        self.assertEqual(search.relevance("вентум", "PPR ventil KAS"), 0.0)

    def test_endings_typos_and_scripts(self):
        self.assertEqual(search.relevance("двери межкомнатные", "Дверь межкомнатная Белая"), 0.8)
        self.assertEqual(search.relevance("цемнт", "Цемент М400 50 кг"), 0.7)
        self.assertEqual(search.relevance("Dusel lampa", "Лампа светодиодная LED Dusel D55"), 1.0)
        self.assertEqual(search.relevance("қувур", "PPR quvur 20 mm Труба PPR 20 мм"), 1.0)

    def test_code(self):
        self.assertEqual(search.relevance("ai91303", "Краска AI-91303"), 1.0)


class AssistantSearchRelevanceTests(ApiTestCase):
    def setUp(self):
        _, category = make_item_category("Plitka")
        self.tile = make_product("T1", category, 50_000)
        self.tile.name_ru, self.tile.name_uz = "Плитка керамическая 30x30", "Keramik plitka 30x30"
        self.tile.save()
        self.clinker = make_product("T2", category, 90_000)
        self.clinker.name_ru, self.clinker.name_uz = "Плитка клинкерная фасадная", "Klinker plitka"
        self.clinker.save()
        self.ctx = tools.ToolContext(language="ru")

    def test_all_words_first_partial_marked(self):
        result = tools.search_products(self.ctx, queries=["клинкерная плитка"])
        rows = {row["id"]: row for row in result["products"]}
        self.assertEqual(result["products"][0]["id"], self.clinker.pk)
        self.assertEqual((rows[self.clinker.pk]["relevance"], rows[self.clinker.pk]["match"]), (1.0, "all_words"))
        if self.tile.pk in rows:
            self.assertEqual(rows[self.tile.pk]["match"], "partial")

    def test_only_partial(self):
        self.clinker.delete()
        result = tools.search_products(self.ctx, queries=["клинкерная плитка"])
        self.assertEqual([row["match"] for row in result["products"]], ["partial"])
        self.assertIn("partly", result["note"])

    def test_nothing_carries_the_words(self):
        result = tools.search_products(self.ctx, queries=["boyler", "бойлер"])
        self.assertEqual((result["total"], result["products"]), (0, []))
        self.assertIn("nothing found", result["note"])
