# Tovar fidlari — Google Merchant Center va Yandex

Merchant Center va Yandex'ga ulash uchun ikkita ochiq URL (token kerak emas):

| URL | Format |
| --- | --- |
| `{{host}}/api/v1/feeds/google.xml` | Google Merchant Center: RSS 2.0, `g:` maydonlari |
| `{{host}}/api/v1/feeds/yandex.yml` | Yandex: YML (`yml_catalog`) |

`{{host}}` = backend manzili (`BACKEND_URL`). Merchant Center'da: **Mahsulotlar → Ma'lumot manbalari →
Fayl (URL orqali, "Scheduled fetch")**, URL = `.../feeds/google.xml`, kuniga kamida bir marta yuklash.

## Qachon yangilanadi

Fidlar tayyor fayl (`media/feeds/`), so'rov paytida qurilmaydi. Celery beat ularni **kuniga 4 marta** qayta
quradi (00:50, 06:50, 12:50, 18:50, Toshkent vaqti; `tasks.build_merchant_feeds`). Qo'lda:

```bash
env/Scripts/python.exe manage.py build_merchant_feeds
```

Fayl hali yo'q bo'lsa, birinchi so'rov uni o'zi quradi. Fayl bir qadamda almashtiriladi — yarim yozilgan fid
hech qachon berilmaydi.

**Havolalar va nom kodda qattiq yozilgan** (`apps/service/merchant_feed.py`, env'dan o'qilmaydi): tovar
havolasi `https://buildex.uz/product/<slug>` (tovarning ruscha slug'i, oxirida id: `…/product/kley-ventum-571`), rasm `https://api.buildex.uz/media/...`. Do'kon nomi **BUILDEX**
(Google kanalining `title` / `description`, Yandex `<name>`), yuridik shaxs **«ENERGOSNAB» MChJ** (Yandex
`<company>`).

## Qaysi tovarlar tushadi

`is_active` **va** narxi > 0 **va** kamida bitta rasmi bor. Qoldig'i yo'q tovar ham tushadi:
`out_of_stock` / `available="false"`.

## Maydonlar

| Ma'nosi | Google | Yandex | Qayerdan |
| --- | --- | --- | --- |
| tovar kodi | `g:id` | `offer id` | `Product.id` |
| nomi | `g:title` (≤ 150 belgi) | `name` | `name_ru` |
| tavsif | `g:description` (≤ 5000) | `description` (≤ 3000) | `description_ru` HTML'siz; bo'sh bo'lsa nom |
| havola | `g:link` | `url` | `https://buildex.uz/product/<slug_ru>` (`…-<id>`) |
| rasm | `g:image_link` + `g:additional_image_link` | `picture` | tovar rasmlari tartibda, 10 tagacha |
| narx | `g:price` (+ `g:sale_price`) | `price` (+ `oldprice`) | quyida |
| valyuta | `UZS` narx ichida | `currencyId` = `UZS` | — |
| mavjudlik | `g:availability` | `available` | `quantity > 0` |
| brend | `g:brand` | `vendor` | `brand.name_ru` |
| artikul | `g:mpn` | `vendorCode` | `articul_code` |
| shtrixkod | `g:gtin` | `barcode` | `barcode`, faqat to'g'ri GTIN bo'lsa (8/12/13/14 raqam, nazorat raqami to'g'ri) |
| kategoriya | `g:product_type` ("A > B > C") | `categoryId` + `categories` daraxti | 3 darajali katalog |
| holati | `g:condition` = `new` | — | — |

Google GTIN yoki brend + MPN so'raydi. Ikkalasi ham bo'lmagan tovarga `g:identifier_exists=no` yoziladi —
shunda tovar rad etilmaydi.

## Narx

Fid narxi = savat oladigan narx: `discount_price` bo'lsa u, aks holda `price`. Chegirma bo'lsa (`discount_price`
< `price`): Google'da `g:price` = eski narx, `g:sale_price` = chegirmali narx; Yandex'da `price` = chegirmali,
`oldprice` = eski narx. Butun summalar kasrsiz yoziladi (`13110 UZS`).

Sayt ham narxni xuddi shu maydonlardan oladi. Shuning uchun fid va API narxi bir xil bo'ladi. Faqat fid kuniga
4 marta yangilanadi: 1C narxni o'zgartirsa, fid keyingi qurilishgacha eski narxni ko'rsatadi (6 soatgacha).

## Sayt (frontend) tomonida

- Tovar sahifasidagi `schema.org/Product` JSON-LD: `offers.price` = yuqoridagi narx (chegirma bo'lsa
  chegirmali), `priceCurrency: "UZS"`, `availability`. Google fid narxini sahifadagi narx bilan solishtiradi —
  farq bo'lsa tovarni rad etadi.
- Sahifa keshi narx o'zgargandan keyin 1 soat ichida yangilanishi kerak.
- Tovar sahifasining manzili `/product/<slug>` (ruscha slug, `products/<id>/` dagi `slug`) redirect'siz 200
  qaytarishi kerak — Merchant Center va Yandex yo'naltiriladigan havolani rad etadi. Eski `/product/<id>` 301
  bilan yangisiga o'tadi, fidda u yo'q (format o'zgarsa — backend'da `merchant_feed.PRODUCT_PATH`).

## Fidda yo'q narsalar

- **Yetkazish narxi**: fidda yo'q. Yetkazish narxi har buyurtmaga Yandex orqali hisoblanadi. Merchant Center'da
  **Yetkazish sozlamalari** (mamlakat O'zbekiston, narx / bepul) akkaunt darajasida beriladi.
- Fid faqat **ru** tilida.
- Google tovar kategoriyasi (`g:google_product_category`) yozilmaydi — Google uni o'zi aniqlaydi.
