from django.db import models
from abstract_model.base_model import BaseModel

class ProductCategory(BaseModel):
    name = models.CharField(max_length=150, verbose_name="")
    image = models.ImageField(upload_to='product_category', verbose_name="")

    def __str__(self):
        return self.name

class ProductSubCategory(BaseModel):
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, verbose_name="")
    name = models.CharField(max_length=255, verbose_name="")

    def __str__(self):
        return self.name

class ProductItemCategory(BaseModel):
    product_sub_category = models.ForeignKey(ProductSubCategory, on_delete=models.CASCADE, verbose_name="")
    name = models.CharField(max_length=255, verbose_name="")

    def __str__(self):
        return self.name

class Product(BaseModel):
    product_item_category = models.ForeignKey(ProductItemCategory, on_delete=models.CASCADE, verbose_name="")
    code = models.CharField(max_length=9, verbose_name="")
    name = models.CharField(max_length=500, verbose_name="")
    price = models.FloatField(default=0, verbose_name="")
    #TODO: need to add rating for the item

    def __str__(self):
        return str(self.id)

class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="")
    image = models.ImageField(upload_to="product_image", verbose_name="")

    def __str__(self):
        return str(self.id)