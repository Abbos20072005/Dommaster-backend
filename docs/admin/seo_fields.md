# SEO maydonlari (slug, meta, alt) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>`.

Har bir **tovar**, **brend** va **kategoriya** (3 daraja) uchun qidiruvga oid maydonlar qo'shildi:
o'qiladigan manzil (`slug`), `meta title`, `meta description` va rasm `alt` matni. Bular 1C'da bo'lishi
shart emas — faqat digital kanalga tegishli. Alohida endpoint yo'q: maydonlar mavjud CRUD serializerlarida
(`products/`, `brands/`, `categories/`, `sub-categories/`, `item-categories/`) keladi.

## Maydonlar

Hamma matn maydoni **til bo'yicha** (`*_uz` / `*_ru`), nom kabi. ru — asosiy (fallback) til.

| Maydon | Obyektlar | Izoh |
| --- | --- | --- |
| `slug_uz`, `slug_ru` | tovar, brend, kategoriya | o'qiladigan manzil, har til uchun alohida |
| `meta_title_uz`, `meta_title_ru` | tovar, brend, kategoriya | sahifa sarlavhasi (bo'sh bo'lsa front shablondan to'ldiradi) |
| `meta_description_uz`, `meta_description_ru` | tovar, brend, kategoriya | qisqa tavsif (bo'sh bo'lsa front shablondan) |
| `image_alt_uz`, `image_alt_ru` | brend, kategoriya | bitta rasmning alt matni |
| `alt_uz`, `alt_ru` | tovar rasmi (`products/{id}/images/`) | har rasmga alohida alt |

**Meta bo'sh qolsa** — backend bo'sh (`null`/`""`) qaytaradi, front tasdiqlangan shablonlardan to'ldiradi
(BLD-238). Backend fallback yasamaydi.

## Slug — qoidalar

- **Avtomatik**: `slug_uz` / `slug_ru` bo'sh yuborilsa (yoki umuman yuborilmasa), model saqlanganda nomdan
  avtomatik yasaladi (kirill va lotin o'zbekcha → ASCII transliteratsiya). Shuning uchun 1C yaratgan
  tovar/kategoriya ham slug oladi.
- **Qo'lda**: istalgan `slug_<til>` ni yuborib o'zgartirish mumkin.
- **Barqaror**: slug bir marta yaratilgach, nom o'zgarsa **o'zgarmaydi** (eski manzillar buzilmasin).
- **Unikal**: har `slug_<til>` o'z tili ustunida model bo'yicha unikal. Takrorlangan slug yuborilsa
  serializer xato beradi (`unique` validatsiya). Avtomatik yasashda takror bo'lsa `-2`, `-3` qo'shiladi.

## Slug tarixi va 301

`slug_uz` yoki `slug_ru` **o'zgartirilsa**, eski qiymat `SlugHistory` ga yoziladi (obyekt + til + eski slug).
Buni model o'zi qiladi (admin tomondan qo'shimcha ish yo'q). Sayt eski/yangi manzilni client'dagi
`GET /api/v1/seo/resolve/` orqali hal qiladi (301 uchun) — qarang `docs/mobile/seo_fields.md`.

Eski slug yana bo'shagan bo'lsa va boshqa obyekt uni olsa, tarixda eng oxirgi obyekt yozib qoladi.

## Backfill

Migratsiya 0121 faqat ustunlarni qo'shadi (bo'sh). Mavjud ma'lumotni to'ldirish buyrug'i:

```
python manage.py backfill_seo_slugs            # haqiqiy
python manage.py backfill_seo_slugs --dry-run  # nechta qator to'lishini ko'rsatadi
```

Har tovar/brend/kategoriya uchun bo'sh `slug_uz`/`slug_ru` ni nomdan yasaydi; kategoriyalarning eski bitta
`slug` qiymati `slug_ru` ga ko'chiriladi. Qayta ishga tushirish xavfsiz (faqat bo'shlarni to'ldiradi).

## 1C

1C slug/meta/alt yubormaydi (bu kutilgan — digital-only). 1C yangi tovar/kategoriya/brend yaratganda slug
avtomatik yasaladi. 1C brendni o'zgartirsa model/slug qayta hisoblanmaydi.
