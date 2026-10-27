# Mahsulotlar matni uz / ru (XLSX eksport) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET products/i18n-export/` | mahsulotlarning uz / ru matnlarini XLSX qilib yuklab olish (tarjimani ko'rib chiqish uchun) |

Swagger: `/swagger/admin/` → **products** (`i18n-export`).

Bu faqat ko'rish / tekshirish uchun fayl — qayta yuklab (import qilib) bo'lmaydi. Kontentni Excel orqali o'zgartirish kerak bo'lsa — `products/content-export/` + `content-imports/` (`content_import.md`).

---

## `GET products/i18n-export/`

Javob — fayl (`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `Content-Disposition: attachment; filename="products_i18n_20261027_1530.xlsx"`), JSON emas. Frontda `blob` qilib yuklab olinadi.

Query parametrlari — **`products/` ro'yxatining hamma filtrlari** (`category`, `sub_category`, `product_item_category`, `brand`, `is_active`, `publish_status`, `badge`, `in_stock`, `search`, ...) ishlaydi, shular ustiga:

| Parametr | Izoh |
| --- | --- |
| `raw_html` | `true` → tavsiflar bazadagi HTML holida chiqadi. Default `false` — HTML oddiy matnga aylantiriladi (`<p>`, `<br>` → yangi qator, `<li>` → `• `) |

Noto'g'ri qiymat (`raw_html=xx`) → `400` `{"raw_html": ["Must be a valid boolean."]}`.

Pagination yo'q — filtrga tushgan hamma mahsulot bitta faylga, `id` bo'yicha tartibda (butun katalog, ~8 ming mahsulot, ~8–10 soniya). Filtrsiz so'rov = butun katalog.

### Fayl

Bitta varaq `Products`, birinchi qator — sarlavha (qalin), `ID` ustuni va sarlavha qotirilgan, avto-filtr yoqilgan:

| Ustun | Nima |
| --- | --- |
| `ID` | mahsulot id |
| `Nomi (uz)` / `Название (ru)` | nomi |
| `Kategoriya (uz)` / `Категория (ru)` | 1-daraja kategoriya |
| `Subkategoriya (uz)` / `Подкатегория (ru)` | 2-daraja |
| `Predmet kategoriya (uz)` / `Предметная категория (ru)` | 3-daraja (mahsulotning o'z kategoriyasi) |
| `Qisqa tavsif (uz)` / `Краткое описание (ru)` | qisqa tavsif |
| `Tavsif (uz)` / `Описание (ru)` | to'liq tavsif |
| `Rasm bor` | `Ha` / `Yo'q` — kamida bitta rasmi bormi |

Bo'sh maydon = bo'sh katak (ru ga fallback **qilinmaydi** — tarjima yo'qligi shundan ko'rinadi). Bitta katakka sig'maydigan uzun matn 32 000 belgida kesiladi.

## Front uchun

Mahsulotlar sahifasida «Eksport» menyusiga «Matnlar uz / ru» bandi — joriy filtrlar bilan `products/i18n-export/` ni yuklab olish (ixtiyoriy «HTML holida» belgisi → `raw_html=true`).
