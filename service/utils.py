from .models import ProductItemCategory, ProductSubCategory, ProductCategory, Product


def build_breadcrumbs(obj):
    breadcrumbs = []

    if isinstance(obj, Product):
        breadcrumbs.insert(0, {"id": obj.id, "name": obj.name, "level": "product"})
        obj = obj.product_item_category

    if isinstance(obj, ProductItemCategory):
        breadcrumbs.insert(0, {"id": obj.id, "name": obj.name, "level": "product_item_category"})
        obj = obj.product_sub_category

    if isinstance(obj, ProductSubCategory):
        breadcrumbs.insert(0, {"id": obj.id, "name": obj.name, "level": "product_sub_category"})
        obj = obj.product_category

    if isinstance(obj, ProductCategory):
        breadcrumbs.insert(0, {"id": obj.id, "name": obj.name, "level": "product_category"})

    return breadcrumbs
