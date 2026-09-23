import io
import random
import secrets
import uuid
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from authorization.models import Customer, CustomerAddresses, FcmToken, OTP, PasswordResetToken
from base.models import (
    MarketBranch, Banner, Chat, Messages, LoyaltyCard, Notification,
    AboutUs, News, Articles, Reviews, Video, Promocodes, DeleteButton,
    BaseInformation,
)
from service.models import (
    AddsBrands, Brand, Order, ProductCategory, ProductSubCategory,
    ProductItemCategory, Tag, Sale, Product, ProductUnit, ProductRemaining,
    Favourites, Announcements, OrderItem, ProductImage, Comment, CommentReply,
    CommentImages, Service, ProductCharacteristics, ProductItemCategoryFilterSchema,
    ProductFilterNumericValue, Cart, CartItem, Questions, QuestionsReply,
    RecentlyViewedProducts, ProductVariantGroup, ProductVariantItem,
)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


CATALOG = {
    "Сантехника": {
        "subs": {
            "Смесители": ["Смесители для кухни", "Смесители для ванной"],
            "Унитазы": ["Унитазы напольные", "Унитазы подвесные"],
        },
    },
    "Электрика": {
        "subs": {
            "Кабели и провода": ["Силовой кабель", "Провод ПВС"],
            "Розетки и выключатели": ["Розетки", "Выключатели"],
        },
    },
    "Инструменты": {
        "subs": {
            "Ручной инструмент": ["Молотки", "Отвертки"],
            "Электроинструмент": ["Дрели", "Болгарки"],
        },
    },
    "Стройматериалы": {
        "subs": {
            "Сухие смеси": ["Штукатурка", "Шпаклевка"],
            "Пиломатериалы": ["Доска", "Брус"],
        },
    },
}

BRANDS = ["Makita", "Bosch", "Knauf", "Legrand", "Uponor", "Cersanit"]

MARKET_BRANCHES = [
    {"name": "Филиал Чиланзар", "address": "г. Ташкент, Чиланзарский р-н", "latitude": 41.2789, "longitude": 69.2001},
    {"name": "Филиал Юнусабад", "address": "г. Ташкент, Юнусабадский р-н", "latitude": 41.3547, "longitude": 69.2878},
]

DEMO_CUSTOMERS = [
    {"phone_number": "+998901234567", "full_name": "Test Customer", "role": Customer.Role.USER},
    {"phone_number": "+998901234568", "full_name": "Aziz Karimov", "role": Customer.Role.USER},
    {"phone_number": "+998901234569", "full_name": "Prorab Usta Sherzod", "role": Customer.Role.PRORAB},
    {"phone_number": "+998901234570", "full_name": "Dilnoza Rashidova", "role": Customer.Role.USER},
]

COMMENT_TEXTS = [
    "Отличный товар, качество на высоте!",
    "Пользуюсь уже месяц, все работает исправно.",
    "Цена соответствует качеству, рекомендую.",
    "Доставили быстро, упаковка целая.",
    "Есть небольшие замечания, но в целом хорошо.",
]

QUESTION_TEXTS = [
    "Какая гарантия на этот товар?",
    "Есть ли этот товар в наличии на складе?",
    "Можно ли забрать самовывозом?",
    "Какой у товара срок службы?",
]

TAGS = ["Новинка", "Хит продаж", "Скидка", "Рекомендуем"]

VARIANT_COLORS = ["Красный", "Синий", "Черный", "Белый", "Серый"]


def make_placeholder_image(text, size=(600, 400)):
    if not HAS_PIL:
        return ContentFile(b"", name="placeholder.jpg")
    color = (random.randint(120, 220), random.randint(120, 220), random.randint(120, 220))
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    safe_name = "".join(c for c in text if c.isalnum())[:40] or "image"
    return ContentFile(buf.read(), name=f"{safe_name}_{random.randint(1000, 9999)}.jpg")


class Command(BaseCommand):
    help = "Seed the database with demo data for (almost) every model in the project."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded demo data before creating new data.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        with transaction.atomic():
            customers = self._create_customers()
            branches = self._create_branches()
            brands = self._create_brands()
            self._create_adds_brands(brands)
            products = self._create_catalog(brands, branches)
            self._create_filter_schemas_and_values(products)
            self._create_variants(products)
            self._create_product_units()
            self._create_tags(products)
            self._create_sales(products)
            self._create_comments(customers, products)
            self._create_questions(customers, products)
            self._create_favourites(customers, products)
            self._create_recently_viewed(customers, products)
            carts = self._create_carts(customers, products)
            self._create_orders(customers, products, branches)
            self._create_announcements()
            self._create_service_entries()
            self._create_customer_addresses(customers)
            self._create_fcm_tokens(customers)
            self._create_otps(customers)
            self._create_password_reset_tokens(customers)
            self._create_base_content(customers, products)

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))

    # ---------- helpers ----------

    def _img(self, text):
        content = make_placeholder_image(text)
        return content.name, content

    def _flush(self):
        self.stdout.write("Removing old demo data...")
        for model in [
            OrderItem, Order, CartItem, Cart, Favourites, RecentlyViewedProducts,
            QuestionsReply, Questions, CommentImages, CommentReply, Comment,
            ProductFilterNumericValue, ProductItemCategoryFilterSchema,
            ProductVariantItem, ProductVariantGroup, ProductCharacteristics,
            ProductImage, ProductRemaining, Product, ProductItemCategory,
            ProductSubCategory, ProductCategory, Tag, Sale, AddsBrands, Brand,
            ProductUnit, Announcements, Service, MarketBranch,
            Messages, Chat, LoyaltyCard, Notification, Banner, News, Articles,
            Reviews, Video, Promocodes, DeleteButton, BaseInformation,
            PasswordResetToken, OTP, FcmToken, CustomerAddresses,
        ]:
            model.objects.all().delete()
        Customer.objects.filter(phone_number__in=[c["phone_number"] for c in DEMO_CUSTOMERS]).delete()

    # ---------- authorization ----------

    def _create_customers(self):
        customers = []
        for data in DEMO_CUSTOMERS:
            customer, created = Customer.objects.get_or_create(
                phone_number=data["phone_number"],
                defaults={
                    "full_name": data["full_name"],
                    "verified": True,
                    "role": data["role"],
                },
            )
            if created:
                customer.password = make_password("test12345")
                customer.save(update_fields=["password"])
            customers.append(customer)
        self.stdout.write(f"Customers: {len(customers)} (password: test12345)")
        return customers

    def _create_customer_addresses(self, customers):
        names = ["Дом", "Офис", "Дача"]
        count = 0
        for customer in customers:
            for i, name in enumerate(random.sample(names, k=random.randint(1, 2))):
                _, created = CustomerAddresses.objects.get_or_create(
                    customer=customer,
                    name=name,
                    defaults={
                        "location_name": f"г. Ташкент, ул. Примерная {random.randint(1, 100)}",
                        "latitude": 41.3 + random.uniform(-0.05, 0.05),
                        "longitude": 69.25 + random.uniform(-0.05, 0.05),
                        "is_default": i == 0,
                    },
                )
                count += created
        self.stdout.write(f"Customer addresses: {count}")

    def _create_fcm_tokens(self, customers):
        count = 0
        for customer in customers:
            _, created = FcmToken.objects.get_or_create(
                customer=customer,
                device_id=f"device-{customer.id}",
                defaults={"fcm_token": secrets.token_hex(32)},
            )
            count += created
        self.stdout.write(f"FCM tokens: {count}")

    def _create_otps(self, customers):
        count = 0
        for customer in customers[:2]:
            _, created = OTP.objects.get_or_create(
                customer=customer,
                otp_key=str(uuid.uuid4()),
                defaults={
                    "otp_code": random.randint(10000, 99999),
                    "expire_at": timezone.now() + timedelta(minutes=5),
                },
            )
            count += created
        self.stdout.write(f"OTPs: {count}")

    def _create_password_reset_tokens(self, customers):
        count = 0
        for customer in customers[:1]:
            _, created = PasswordResetToken.objects.get_or_create(
                customer=customer,
                token=secrets.token_hex(32),
                defaults={"expires_at": timezone.now() + timedelta(hours=1)},
            )
            count += created
        self.stdout.write(f"Password reset tokens: {count}")

    # ---------- branches / brands ----------

    def _create_branches(self):
        branches = []
        for data in MARKET_BRANCHES:
            branch, _ = MarketBranch.objects.get_or_create(
                name=data["name"],
                defaults={
                    "address": data["address"],
                    "latitude": data["latitude"],
                    "longitude": data["longitude"],
                    "branch_type": 1,
                    "working_hours": "09:00 - 20:00",
                    "phone_number": "+998712345678",
                    "is_active": True,
                },
            )
            if not branch.image:
                branch.image.save(*self._img(branch.name), save=True)
            branches.append(branch)
        self.stdout.write(f"Branches: {len(branches)}")
        return branches

    def _create_brands(self):
        brands = []
        for name in BRANDS:
            brand, created = Brand.objects.get_or_create(name=name, defaults={"is_visible": True})
            if created:
                brand.image.save(*self._img(name), save=True)
            brands.append(brand)
        self.stdout.write(f"Brands: {len(brands)}")
        return brands

    def _create_adds_brands(self, brands):
        count = 0
        for brand in brands[:2]:
            ad, created = AddsBrands.objects.get_or_create(
                brand=brand,
                defaults={
                    "name": f"Реклама {brand.name}",
                    "title": f"Лучшие товары {brand.name}",
                    "description": f"Подборка лучших товаров бренда {brand.name}.",
                    "is_visible": True,
                },
            )
            count += created
        self.stdout.write(f"Brand ads: {count}")

    # ---------- catalog ----------

    def _create_catalog(self, brands, branches):
        products = []
        for cat_name, cat_data in CATALOG.items():
            category, created = ProductCategory.objects.get_or_create(name=cat_name, defaults={"position": 0})
            if created:
                category.icon.save(*self._img(cat_name + "_icon"), save=False)
                category.image.save(*self._img(cat_name), save=True)

            for sub_name, items in cat_data["subs"].items():
                sub_category, created = ProductSubCategory.objects.get_or_create(
                    product_category=category, name=sub_name,
                )
                if created:
                    sub_category.image.save(*self._img(sub_name), save=True)

                for item_name in items:
                    item_category, created = ProductItemCategory.objects.get_or_create(
                        product_sub_category=sub_category, name=item_name,
                    )
                    if created:
                        item_category.image.save(*self._img(item_name), save=True)

                    for i in range(1, 4):
                        product_name = f"{item_name} модель {i}"
                        price = float(random.randint(50, 500) * 1000)
                        has_discount = random.random() < 0.3
                        product, created = Product.objects.get_or_create(
                            name=product_name,
                            defaults={
                                "brand": random.choice(brands),
                                "product_item_category": item_category,
                                "description": f"Описание товара {product_name}.",
                                "short_description": f"{product_name} - качественный товар.",
                                "price": price,
                                "discount_price": round(price * 0.85, 2) if has_discount else None,
                                "discount": 15 if has_discount else None,
                                "unit": random.choice(["pcs", "kg", "m", "set"]),
                                "quantity": random.randint(0, 200),
                                "is_active": True,
                                "articul_code": f"ART-{random.randint(10000, 99999)}",
                                "barcode": str(random.randint(1000000000000, 9999999999999)),
                            },
                        )
                        if created:
                            image_content = make_placeholder_image(product_name)
                            ProductImage.objects.create(
                                product=product,
                                image=ContentFile(image_content.read(), name=image_content.name),
                            )
                            for branch in branches:
                                ProductRemaining.objects.get_or_create(
                                    branch=branch, product=product,
                                    defaults={"quantity": random.randint(0, 50)},
                                )
                            for char_name, unit, value in [
                                ("Вес", "кг", str(round(random.uniform(0.1, 20), 2))),
                                ("Материал", "", random.choice(["Металл", "Пластик", "Дерево", "Керамика"])),
                                ("Страна производства", "", random.choice(["Узбекистан", "Турция", "Китай", "Германия"])),
                            ]:
                                ProductCharacteristics.objects.create(
                                    product=product, name=char_name, unit=unit, value=value,
                                )
                        products.append(product)
        self.stdout.write(f"Products: {len(products)}")
        return products

    def _create_filter_schemas_and_values(self, products):
        by_item_category = {}
        for product in products:
            by_item_category.setdefault(product.product_item_category, []).append(product)

        count_schemas = 0
        count_values = 0
        for item_category, item_products in by_item_category.items():
            schema, created = ProductItemCategoryFilterSchema.objects.get_or_create(
                item_category=item_category,
                key="weight",
                defaults={
                    "source_name_ru": "Вес",
                    "label": "Вес, кг",
                    "type": "range",
                    "unit": "кг",
                    "position": 0,
                    "is_filterable": True,
                },
            )
            count_schemas += created
            for product in item_products:
                _, created = ProductFilterNumericValue.objects.get_or_create(
                    product=product, schema=schema,
                    defaults={"value": round(random.uniform(0.5, 25.0), 2)},
                )
                count_values += created
        self.stdout.write(f"Filter schemas: {count_schemas}, filter values: {count_values}")

    def _create_variants(self, products):
        group, _ = ProductVariantGroup.objects.get_or_create(
            name="Цвет", defaults={"display_type": "text"},
        )
        count = 0
        for product in random.sample(products, k=min(15, len(products))):
            _, created = ProductVariantItem.objects.get_or_create(
                group=group, product=product,
                defaults={"display_value": random.choice(VARIANT_COLORS)},
            )
            count += created
        self.stdout.write(f"Product variants: {count}")

    def _create_product_units(self):
        units = [
            ("796", "шт", "штука", "штук", "pieces"),
            ("166", "кг", "килограмм", "килограммов", "kilogram"),
            ("112", "м", "метр", "метров", "meter"),
            ("704", "компл", "комплект", "комплектов", "set"),
        ]
        count = 0
        for code, name, ru, ru_full, en in units:
            _, created = ProductUnit.objects.get_or_create(
                unit_code=code,
                defaults={
                    "name": name,
                    "name_full_ru": ru_full,
                    "name_full_uz": ru_full,
                    "name_full_en": en,
                    "is_active": True,
                },
            )
            count += created
        self.stdout.write(f"Product units: {count}")

    def _create_tags(self, products):
        count = 0
        for tag_name in TAGS:
            tag, created = Tag.objects.get_or_create(name=tag_name, defaults={"is_active": True})
            count += created
            tag.product.add(*random.sample(products, k=min(8, len(products))))
        self.stdout.write(f"Tags: {count}")

    def _create_sales(self, products):
        sale, created = Sale.objects.get_or_create(
            name="Летняя распродажа",
            defaults={
                "discount_from": timezone.now().date(),
                "discount_to": timezone.now().date() + timedelta(days=30),
                "is_main": True,
                "is_visible": True,
            },
        )
        if created:
            sale.image.save(*self._img("sale_image"), save=False)
            sale.bg_image.save(*self._img("sale_bg"), save=True)
            sale.products.add(*random.sample(products, k=min(10, len(products))))
        self.stdout.write(f"Sales: {1 if created else 0}")

    # ---------- comments / questions ----------

    def _create_comments(self, customers, products):
        count_comments = 0
        count_replies = 0
        count_images = 0
        for product in random.sample(products, k=min(20, len(products))):
            customer = random.choice(customers)
            comment, created = Comment.objects.get_or_create(
                customer=customer, product=product,
                defaults={
                    "product_rating": random.randint(3, 5),
                    "comment": random.choice(COMMENT_TEXTS),
                    "is_visible": True,
                },
            )
            if created:
                count_comments += 1
                if random.random() < 0.4:
                    CommentReply.objects.create(
                        comment=comment,
                        customer=None,
                        reply_comment="Спасибо за ваш отзыв!",
                        is_admin=True,
                        is_visible=True,
                    )
                    count_replies += 1
                if random.random() < 0.3:
                    image_content = make_placeholder_image(f"comment_{comment.id}")
                    CommentImages.objects.create(
                        customer=customer, comment=comment,
                        image=ContentFile(image_content.read(), name=image_content.name),
                    )
                    count_images += 1
                product.update_rating()
        self.stdout.write(f"Comments: {count_comments}, replies: {count_replies}, comment images: {count_images}")

    def _create_questions(self, customers, products):
        count_q = 0
        count_a = 0
        for product in random.sample(products, k=min(12, len(products))):
            customer = random.choice(customers)
            question, created = Questions.objects.get_or_create(
                customer=customer, product=product,
                question=random.choice(QUESTION_TEXTS),
                defaults={"is_visible": True},
            )
            if created:
                count_q += 1
                if random.random() < 0.5:
                    QuestionsReply.objects.create(
                        customer=None, question=question,
                        answer="Да, товар есть в наличии, уточните у менеджера.",
                        is_admin=True, is_visible=True,
                    )
                    count_a += 1
                product.update_questions()
        self.stdout.write(f"Questions: {count_q}, answers: {count_a}")

    def _create_favourites(self, customers, products):
        count = 0
        for customer in customers:
            for product in random.sample(products, k=min(5, len(products))):
                _, created = Favourites.objects.get_or_create(customer=customer, product=product)
                count += created
        self.stdout.write(f"Favourites: {count}")

    def _create_recently_viewed(self, customers, products):
        count = 0
        for customer in customers:
            for product in random.sample(products, k=min(6, len(products))):
                _, created = RecentlyViewedProducts.objects.get_or_create(customer=customer, product=product)
                count += created
        self.stdout.write(f"Recently viewed: {count}")

    # ---------- cart / orders ----------

    def _create_carts(self, customers, products):
        carts = []
        for customer in customers:
            cart, _ = Cart.objects.get_or_create(customer=customer)
            for product in random.sample(products, k=min(3, len(products))):
                CartItem.objects.get_or_create(
                    cart=cart, product=product,
                    defaults={"quantity": random.randint(1, 3), "is_checked": True},
                )
            cart.calculate_total_price()
            cart.save()
            carts.append(cart)
        self.stdout.write(f"Carts: {len(carts)}")
        return carts

    def _create_orders(self, customers, products, branches):
        count_orders = 0
        count_items = 0
        for customer in customers:
            address = customer.customeraddresses_set.first() if hasattr(customer, "customeraddresses_set") else None
            address = CustomerAddresses.objects.filter(customer=customer).first()
            for _ in range(random.randint(1, 2)):
                delivery_type = random.choice([0, 1])
                order = Order.objects.create(
                    customer=customer,
                    status=random.choice([0, 1, 2, 3]),
                    payment_status=random.choice([0, 2]),
                    delivery_type=delivery_type,
                    order_location=address if delivery_type == 0 else None,
                    pickup_branch=random.choice(branches) if delivery_type == 1 else None,
                    payment_type=random.choice([1, 2, 4]),
                    payment_method="cash" if random.random() < 0.5 else "card",
                    receiver_name=customer.full_name,
                    receiver_phone=customer.phone_number,
                    delivery_price=15000 if delivery_type == 0 else 0,
                )
                order_products = random.sample(products, k=min(3, len(products)))
                total = 0.0
                for product in order_products:
                    qty = random.randint(1, 3)
                    OrderItem.objects.create(order=order, product=product, quantity=qty)
                    price = product.discount_price or product.price
                    total += price * qty
                    count_items += 1
                order.products_total_price = total
                order.total_price = total + float(order.delivery_price)
                order.save(update_fields=["products_total_price", "total_price"])
                count_orders += 1
        self.stdout.write(f"Orders: {count_orders}, order items: {count_items}")

    # ---------- misc service ----------

    def _create_announcements(self):
        count = 0
        for title in ["Новая коллекция инструментов", "Скидки на сантехнику до 20%"]:
            ann, created = Announcements.objects.get_or_create(
                title=title, defaults={"description": f"{title}. Успейте купить по выгодной цене!"},
            )
            if created:
                ann.image.save(*self._img(title), save=True)
            count += created
        self.stdout.write(f"Announcements: {count}")

    def _create_service_entries(self):
        count = 0
        for name in ["Доставка", "Монтаж", "Гарантийное обслуживание"]:
            service, created = Service.objects.get_or_create(
                name=name, defaults={"description": f"Услуга: {name}."},
            )
            if created:
                service.icon.save(*self._img(name), save=True)
            count += created
        self.stdout.write(f"Services: {count}")

    # ---------- base app ----------

    def _create_base_content(self, customers, products):
        # Banner
        banner, created = Banner.objects.get_or_create(
            title="Главный баннер",
            defaults={
                "link": "https://example.com",
                "is_visible": True,
                "content_type": ContentType.objects.get_for_model(Product),
                "object_id": products[0].id if products else None,
            },
        )
        if created:
            banner.desktop_image.save(*self._img("banner_desktop"), save=True)

        # Chat + messages
        chat, created = Chat.objects.get_or_create(customer=customers[0])
        if created:
            Messages.objects.create(chat=chat, message="Здравствуйте! Чем можем помочь?", is_answer=True)
            Messages.objects.create(chat=chat, message="Хочу узнать статус заказа.", is_answer=False)

        # Loyalty card
        LoyaltyCard.objects.get_or_create(
            customer=customers[0],
            defaults={"full_name": customers[0].full_name, "card_number": random.randint(100000, 999999), "is_active": True},
        )

        # Notifications
        for title in ["Ваш заказ подтвержден", "Специальное предложение для вас"]:
            Notification.objects.get_or_create(title=title, defaults={"description": f"{title}."})

        # About us
        if not AboutUs.objects.exists():
            AboutUs.objects.create(description="Dommaster - магазин строительных материалов и товаров для дома.")

        # News
        for title in ["Открытие нового филиала", "Обновление ассортимента"]:
            news, created = News.objects.get_or_create(title=title, defaults={"description": f"{title}. Подробности внутри."})
            if created:
                news.image.save(*self._img(title), save=True)

        # Articles
        for title in ["Как выбрать смеситель", "Топ-5 инструментов для ремонта"]:
            Articles.objects.get_or_create(
                title=title,
                defaults={"short_description": f"{title} - краткое описание.", "description": f"{title} - полное описание статьи."},
            )

        # Reviews
        for title in ["Обзор перфоратора Bosch", "Обзор смесителя Cersanit"]:
            Reviews.objects.get_or_create(
                title=title,
                defaults={"short_description": f"{title} - обзор.", "description": f"{title} - подробный текст обзора."},
            )

        # Video
        Video.objects.get_or_create(name="Как пользоваться Dommaster", defaults={"url": "https://youtube.com/watch?v=demo"})

        # Promocodes
        Promocodes.objects.get_or_create(
            customer=customers[0], code="WELCOME10",
            defaults={"name": "Приветственная скидка", "discount_precent": 10, "expires_at": timezone.now().date() + timedelta(days=60)},
        )

        # Delete button
        DeleteButton.objects.get_or_create(is_deleted=False)

        # Base information
        if not BaseInformation.objects.exists():
            BaseInformation.objects.create(
                phone_number="+998712345678",
                additional_phone_number="+998901234567",
                email="info@dommaster.uz",
                address="г. Ташкент, ул. Примерная 1",
                working_hours="09:00 - 20:00",
                telegram="https://t.me/dommaster",
                instagram="https://instagram.com/dommaster",
            )

        self.stdout.write("Base app content (banners, news, articles, reviews, chat, etc.) seeded.")
