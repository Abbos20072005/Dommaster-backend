# Reklama bloklari (AddsBrands) — admin panel uchun

Reklama bloki = bosh sahifadagi mahsulotlar bo'limi (masalan "Yozgi chegirmalar"): nomi, tanlangan mahsulotlar va
kampaniya sahifasi (`title` + `description`). Brendga bog'lash ixtiyoriy.

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET adds-brands/` | bloklar ro'yxati (paginatsiyali) |
| `POST adds-brands/` | blok yaratish |
| `GET / PUT / PATCH / DELETE adds-brands/{id}/` | bitta blok |

Swagger: `/swagger/admin/` → **adds-brands**. Fayl yo'q — hammasi JSON.

---

## Obyekt (`GET adds-brands/{id}/`, `POST`, `PATCH` javobi)

```json
{
  "id": 5,
  "name": "Летняя распродажа",
  "name_uz": "Yozgi chegirmalar",
  "name_ru": "Летняя распродажа",
  "name_en": null,
  "title": "Лето",
  "title_uz": "Yoz",
  "title_ru": "Лето",
  "title_en": null,
  "description": "<p>Условия акции...</p>",
  "description_uz": "<p>Aksiya shartlari...</p>",
  "description_ru": "<p>Условия акции...</p>",
  "description_en": null,
  "brand": { "id": 15, "name": "Knauf" },
  "products": [
    { "id": 102, "name": "Смеситель для ванной", "product_code": "000001234", "price": 80000.0, "discount_price": null, "is_active": true },
    { "id": 103, "name": "Унитаз напольный", "product_code": "000001235", "price": 124000.0, "discount_price": 105400.0, "is_active": true }
  ],
  "is_visible": true,
  "created_at": "2026-10-02T15:35:24",
  "updated_at": "2026-10-02T15:35:24"
}
```

| Maydon | Izoh |
| --- | --- |
| `name_ru` * | blok nomi (bosh sahifadagi bo'lim sarlavhasi), majburiy, 450 belgigacha |
| `name_uz`, `name_en` | ixtiyoriy |
| `title_ru` * | kampaniya sahifasi sarlavhasi, majburiy, 350 belgigacha |
| `title_uz`, `title_en` | ixtiyoriy |
| `description_ru` * | kampaniya sahifasi matni, majburiy, HTML (rich text) |
| `description_uz`, `description_en` | ixtiyoriy, HTML |
| `brand` | ixtiyoriy; `{"id": 15}` yoki shunchaki `15`; `null` = brendsiz. Bitta brendga faqat **bitta** blok |
| `products` * | mahsulotlar ro'yxati, kamida bitta; har biri `{"id": 102}` yoki shunchaki `102` |
| `is_visible` | default `true`; `false` = mijozga ko'rinmaydi |

Faqat o'qiladi: `id`, `name`, `title`, `description` (joriy tildagi qiymat), `created_at`, `updated_at`; `brand` va
`products` ichida faqat `id` yoziladi, qolgani ko'rsatish uchun.

### Yaratish

`POST adds-brands/`

```json
{
  "name_ru": "Летняя распродажа",
  "name_uz": "Yozgi chegirmalar",
  "title_ru": "Лето",
  "description_ru": "<p>Условия акции...</p>",
  "brand": 15,
  "products": [102, 103]
}
```

### Tahrirlash

`PATCH adds-brands/{id}/` — faqat yuborilgan maydonlar o'zgaradi.

`products` yuborilsa, ro'yxat **to'liq almashtiriladi** (qo'shish / olib tashlash uchun yangi to'liq ro'yxat yuboriladi):

```json
{ "products": [102, 103, 110] }
```

Brenddan uzish: `{ "brand": null }`. Yashirish: `{ "is_visible": false }`.

`PUT` da `products` ham majburiy.

### O'chirish

`DELETE adds-brands/{id}/` → `204`. Mahsulotlar va brend o'chmaydi, faqat blok.

---

## Ro'yxat

`GET adds-brands/?page=&page_size=` — ro'yxatda `description*` va `products` **kelmaydi**, o'rniga `products_count`:

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "next_page": null,
  "previous_page": null,
  "results": [
    {
      "id": 5,
      "name": "Летняя распродажа",
      "name_uz": "Yozgi chegirmalar",
      "name_ru": "Летняя распродажа",
      "name_en": null,
      "title": "Лето",
      "title_uz": "Yoz",
      "title_ru": "Лето",
      "title_en": null,
      "brand": { "id": 15, "name": "Knauf" },
      "products_count": 2,
      "is_visible": true,
      "created_at": "2026-10-02T15:35:24",
      "updated_at": "2026-10-02T15:35:24"
    }
  ]
}
```

- Qidiruv: `?search=` (nomi va sarlavhasi uz/ru/en, brend nomi)
- Filtrlar: `is_visible`, `brand` (brend id), `has_brand` (`true` / `false`)
- Tartib: `?ordering=` `id`, `name`, `products_count`, `is_visible`, `created_at`, `updated_at` (teskari: `-products_count`); default — yangilari birinchi

---

## Xatolar

Oddiy DRF formati — maydon nomi bo'yicha:

```json
{ "brand": ["This brand already has an ad block."] }
```

```json
{ "products": { "non_field_errors": ["Этот список не может быть пустым."] } }
```

```json
{ "products": [ { "id": "Object with id=999 does not exist." } ] }
```

## Eslatmalar

- Mijoz tomoni o'zgarmagan: `GET /api/v1/adds/brands/` (ro'yxat) va bosh sahifa (`homepage_data`) faqat `is_visible=true` bloklarni,
  ular ichida faqat **faol** (`is_active=true`) mahsulotlarni ko'rsatadi. Shuning uchun `products` ichidagi `is_active: false`
  mahsulot blokda turadi, lekin mijozga chiqmaydi.
- Bosh sahifa ~17 daqiqa keshlanadi — o'zgarish u yerda darhol ko'rinmasligi mumkin (`adds/brands/` da darhol ko'rinadi).
- Bloklar tartibini boshqarish (`position`) hozircha yo'q.
- `description` ichiga rasm yuklash endpointi admin API'da yo'q — rasm tashqi havola (`<img src="https://...">`) bo'lishi kerak.
