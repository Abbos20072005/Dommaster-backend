# Katalog javoblarining tili (uz / ru)

Base URL: `{{host}}/api/v1/`

Mijoz API'sidagi hamma matn `Accept-Language` sarlavhasiga qarab qaytadi: mahsulot nomi va tavsifi, brend, kategoriyalar, atributlar, yangiliklar, bannerlar, do'konlar — hammasi.

## Til qanday aniqlanadi

- `Accept-Language` dagi birinchi ma'lum til olinadi: `uz`, `ru`. `uz-UZ` → `uz`, brauzerning to'liq sarlavhasi (`uz-UZ,uz;q=0.9,ru;q=0.8`) ham ishlaydi.
- Sarlavha yo'q yoki boshqa til (`en` va h.k.) → **ru**.
- Tanlangan tildagi matn bo'sh bo'lsa → **ru** ga tushadi. Shuning uchun `name_uz` to'ldirilmagan mahsulot uz tilida ham o'qiladigan nom bilan keladi.
- Javobda qaytgan til `Content-Language` sarlavhasida ko'rsatiladi.

Ilova uchun amaliy xulosa: har bir so'rovda `Accept-Language: uz` yoki `ru` yuborish kifoya — qolgan hammasini backend hal qiladi.

## Qaysi maydonlar tilga moslangan

| Endpoint | Maydonlar |
| --- | --- |
| `products/`, `products/<id>/`, `products/recommended/`, `product/filter/`, savat, sevimlilar, buyurtma tarkibi | `name`, `short_description`, `description`, `slug`, `meta_title`, `meta_description`, `images[].alt`, `attributes` / `characteristics`, `breadcrumbs`, `brand.name`, `variant_groups[].name` va `items[].display_value` |
| `categories/`, `sub/categories/<id>/`, `item/categories/<id>/` (menyu, daraxt, brend bo'yicha) | `name`, `slug`, `meta_title`, `meta_description`, `image_alt`, `breadcrumbs` |
| `brands/`, `brands/<id>/` | `name`, `slug`, `image_alt`, `meta_*` |
| `search/?q=`, `most/search/`, `most/sold/` | mahsulot nomlari, kategoriya va brend nomlari |
| `home/`, `main/`, `banner/` | blok sarlavhalari, banner `title`, kategoriya / brend nomlari |
| `base/news/`, `base/video/`, `base/about-us/`, `base/notifications/`, promokod nomi | `title`, `description`, `name` |
| `base/stores/`, `base/branches/` | `name`, `address`, `landmark`, `location_name`, `description` |
| `services/`, `adds/brands/<id>/`, `filter-pages/<slug>/` | `name`, `title`, `description`, `text` |

Qidirish har doim ikkala tilda ishlaydi (`name_uz` va `name_ru` bo'yicha), javobdagi nom esa so'rov tilida.

## Tilga bog'liq bo'lmagan joylar

- Mahsulotning `unit` (o'lchov birligi) — 1C beradigan erkin matn, tarjimasi yo'q.
- Buyurtma holati pushlari va bildirishnoma pushlari — faqat ru (mijozning tili saqlanmaydi).
- `base/articles/`, `base/reviews/` — modelda tarjima yo'q, bitta tilda.
- Aksiya (`sales/`) nomi — modelda tarjima yo'q.

## Eski ilova versiyalari buziladimi

Yo'q — maydonlar, ularning nomlari va javob shakli o'zgarmagan. `Accept-Language` yubormaydigan mijozlar avvalgidek ru oladi. Bitta yaxshilanish: ilgari `uz-UZ` yoki brauzer uslubidagi sarlavha yuborilganda `base/*` endpointlari ru qaytarardi — endi ular ham uz beradi.

## Deploydan keyin (backend uchun)

1. `manage.py backfill_empty_translations` — bir marta. `null=True` ustunda saqlangan bo'sh string modeltranslation uchun "to'ldirilgan" qiymat bo'lib, ru matnini yashiradi (`MarketBranch.address`, `Product.short_description` kabi ustunlar). Komanda faqat shunday satrlarni NULL qiladi: uz ustuni bo'sh, ru'da matn bor. ru ustunining o'ziga va ru'da ham matn bo'lmagan satrlarga tegmaydi, shuning uchun javobdagi `""` hech qachon `null`ga aylanib ketmaydi. `--dry-run` bor, qayta ishga tushirish xavfsiz.
2. Keshlangan javoblarning kalitida til bor (`home:main:data`, `products:most_sold`, `products:most_search`, `search:v2:<q>`, `categories:list*`, `home:blocks`), shuning uchun alohida tozalash kerak emas — birinchi so'rovlar keshni qaytadan to'ldiradi.
