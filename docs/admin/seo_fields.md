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
- **Nom o'zgarganda**:
  - **kategoriya va brend** slug'i **o'zgarmaydi** (eski manzillar buzilmasin);
  - **tovar** slug'i **yangi nomdan qayta yasaladi** (`Asfora антрацит` → `Asfora 10 А, антрацит` bo'lsa
    `…-asfora-antratsit-571` → `…-asfora-10-a-antratsit-571`). Oxiridagi id o'zgarmaydi, shuning uchun eski
    manzil `seo/resolve/` da `moved` beradi. Til bo'yicha alohida: o'zbekcha nomi bo'sh tovarning `slug_uz`
    i ruscha nomga ergashadi;
  - **qo'lda kiritilgan** tovar slug'i (nomdan yasalganiga teng bo'lmagani) nom o'zgarsa ham **qoladi**;
    nom bilan birga yangi slug yuborilsa — yuborilgani olinadi.
- **Unikal**: har `slug_<til>` o'z tili ustunida model bo'yicha unikal. Takrorlangan slug yuborilsa
  serializer xato beradi (`unique` validatsiya).
- **Tovarda id qo'shimchasi**: tovar slug'i `<nom>-<id>` (`kley-ventum-571`) — nomlar takrorlanadi,
  id esa unikallikni kafolatlaydi. Kategoriya va brendda qo'shimcha yo'q, takror bo'lsa `-2`, `-3`.

### Transliteratsiya jadvali

Kelishilgan jadval (BLD-243 URL rejasi), kod: `utils/slug.py` → `CYRILLIC_TO_LATIN`:

| ж | ы | х | ц | щ | ч | ш | ё | ю | я | ъ / ь |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `zh` | `y` | `h` | `ts` | `sch` | `ch` | `sh` | `yo` | `yu` | `ya` | tashlanadi |

Misol: `Крепеж` → `krepezh`, `Сантехника` → `santehnika`, `Строительные материалы` →
`stroitelnye-materialy`. Jadvalni o'zgartirish = barcha manzil o'zgarishi, SEO rejasidan tashqari
tegmaslik kerak; o'zgartirilsa `backfill_seo_slugs --rebuild` ishga tushadi.

## Slug tarixi va 301

`slug_uz` yoki `slug_ru` **o'zgartirilsa**, eski qiymat `SlugHistory` ga yoziladi (obyekt + til + eski slug).
Buni model o'zi qiladi (admin tomondan qo'shimcha ish yo'q). Sayt eski/yangi manzilni client'dagi
`GET /api/v1/seo/resolve/` orqali hal qiladi (301 uchun) — qarang `docs/mobile/seo_fields.md`.

Tarix **faqat kategoriya va brend** uchun yuritiladi (22.10 qarori). Tovarning slug'i o'zgarsa tarixga
yozilmaydi — tovar nomi tez o'zgaradi, slug'da esa id turadi.

Eski slug yana bo'shagan bo'lsa va boshqa obyekt uni olsa, tarixda eng oxirgi obyekt yozib qoladi.

## Backfill

Migratsiya 0121 faqat ustunlarni qo'shadi (bo'sh). Mavjud ma'lumotni to'ldirish buyrug'i:

```
python manage.py backfill_seo_slugs                      # bo'sh slug'larni to'ldiradi
python manage.py backfill_seo_slugs --dry-run            # nechta qator to'lishini ko'rsatadi
python manage.py backfill_seo_slugs --rebuild            # hamma slug'ni jadval bo'yicha qayta yasaydi
python manage.py backfill_seo_slugs --rebuild --dry-run
python manage.py backfill_seo_slugs --products --dry-run # nomiga mos kelmay qolgan tovar slug'lari
python manage.py backfill_seo_slugs --products
```

Oddiy rejim har tovar/brend/kategoriya uchun **bo'sh** `slug_uz`/`slug_ru` ni nomdan yasaydi, mavjudiga
tegmaydi. Qayta ishga tushirish xavfsiz.

`--rebuild` — transliteratsiya jadvali o'zgarganda: db'dagi hamma slug tashlanadi (qo'lda kiritilganlari
ham) va nomdan qaytadan yasaladi. Kategoriya/brendning eski slug'i `SlugHistory` ga tushadi, ya'ni
`seo/resolve/` eski manzilga `moved` beradi va sayt 301 qiladi. Eski bitta `slug` ustuni ham tozalanadi
(uni hech kim o'qimaydi, slug'lar — til bo'yicha ustunlar).

`--products` — faqat tovarlar: hozirgi nomdan chiqadigan slug'ga teng bo'lmagan har `slug_<til>` qayta
yasaladi. Tovar slug'i ilgari nom o'zgarsa ham eskicha qolardi (audit nomlarni tuzatgandan keyin 8 264 tadan
~1 760 tovarning slug'i nomiga mos emas edi), bu — shu eski slug'larni **bir marta** tuzatish. Qo'lda
kiritilgan tovar slug'ini ajratib bo'lmaydi, u ham qayta yasaladi. Tarix yozilmaydi — id o'zgarmaydi,
`seo/resolve/` eski slug'ni id bo'yicha topadi. Qayta ishga tushirish xavfsiz (ikkinchi marta 0 qator).

## 1C

1C slug/meta/alt yubormaydi (bu kutilgan — digital-only). 1C yangi tovar/kategoriya/brend yaratganda slug
avtomatik yasaladi. 1C brendni o'zgartirsa model/slug qayta hisoblanmaydi.
