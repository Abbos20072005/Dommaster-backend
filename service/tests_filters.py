from django.test import TestCase, Client
from django.urls import reverse
from .models import Product, ProductCategory, ProductSubCategory, ProductItemCategory, CategoryAttribute, CategoryAttributeValue, ProductAttributeValue
import json

class ProductFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = ProductCategory.objects.create(name="Tools", image="path/to/img", icon="path/to/icon")
        self.sub_category = ProductSubCategory.objects.create(name="Power Tools", product_category=self.category)
        self.item_category = ProductItemCategory.objects.create(name="Drills", product_sub_category=self.sub_category)

        # Create two products
        self.p1 = Product.objects.create(
            name="Hammer Drill",
            description="A powerful drill",
            product_item_category=self.item_category,
            price=100.0,
            quantity=10
        )
        self.p2 = Product.objects.create(
            name="Impact Driver",
            description="A compact driver",
            product_item_category=self.item_category,
            price=150.0,
            quantity=5
        )

        # Add predefined attributes
        self.attr_color = CategoryAttribute.objects.create(category=self.item_category, name="Color", is_filterable=True, position=1)
        self.attr_power = CategoryAttribute.objects.create(category=self.item_category, name="Power", is_filterable=True, position=2)

        self.val_red = CategoryAttributeValue.objects.create(attribute=self.attr_color, value="Red")
        self.val_blue = CategoryAttributeValue.objects.create(attribute=self.attr_color, value="Blue")
        self.val_500w = CategoryAttributeValue.objects.create(attribute=self.attr_power, value="500W")
        self.val_700w = CategoryAttributeValue.objects.create(attribute=self.attr_power, value="700W")

        # Assign attributes to products
        ProductAttributeValue.objects.create(product=self.p1, attribute=self.attr_color, attribute_value=self.val_red)
        ProductAttributeValue.objects.create(product=self.p1, attribute=self.attr_power, attribute_value=self.val_500w)
        
        ProductAttributeValue.objects.create(product=self.p2, attribute=self.attr_color, attribute_value=self.val_blue)
        ProductAttributeValue.objects.create(product=self.p2, attribute=self.attr_power, attribute_value=self.val_700w)

    def test_filter_by_characteristic(self):
        url = reverse("product_filter")
        data = {
            "attributes": {str(self.attr_color.id): [self.val_red.id]},
            "page": 1,
            "page_size": 10
        }
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        results = response.json()["result"]["products"]["content"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.p1.id)

    def test_filter_by_multiple_characteristics(self):
        url = reverse("product_filter")
        data = {
            "attributes": {str(self.attr_color.id): [self.val_red.id], str(self.attr_power.id): [self.val_500w.id]},
            "page": 1,
            "page_size": 10
        }
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        results = response.json()["result"]["products"]["content"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.p1.id)

    def test_filter_by_multiple_values(self):
        url = reverse("product_filter")
        data = {
            "attributes": {str(self.attr_color.id): [self.val_red.id, self.val_blue.id]},
            "page": 1,
            "page_size": 10
        }
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        results = response.json()["result"]["products"]["content"]
        self.assertEqual(len(results), 2)

    def test_available_filters_no_category(self):
        url = reverse("product_filter")
        data = {
            "page": 1,
            "page_size": 10
        }
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        filters = response.json()["result"]["available_filters"]
        # Fallback dynamic logic (no category provided)
        self.assertEqual(len(filters), 0) # Fallback uses ProductCharacteristics which are empty now

    def test_category_attributes_endpoint(self):
        url = reverse("category_attributes", kwargs={"pk": self.item_category.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        filters = response.json()["result"]
        
        self.assertEqual(len(filters), 2)
        self.assertEqual(filters[0]["name"], "Color")
        self.assertEqual(filters[1]["name"], "Power")
        self.assertEqual(len(filters[0]["values"]), 2)
        self.assertEqual(filters[0]["values"][0]["value"], "Red")
        self.assertEqual(filters[0]["values"][1]["value"], "Blue")
