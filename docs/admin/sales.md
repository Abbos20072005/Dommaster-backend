# Sales (Распродажи) — Admin API

Base URL: `/api/v1/admin/sales/`

Auth: `AdminJwtAuthentication` + `IsAdmin` (inherited from `AdminModelViewSet`).

---

## Endpoints

| Method | URL | Action |
|--------|-----|--------|
| GET | `/api/v1/admin/sales/` | List |
| POST | `/api/v1/admin/sales/` | Create |
| GET | `/api/v1/admin/sales/{id}/` | Retrieve |
| PUT | `/api/v1/admin/sales/{id}/` | Full update |
| PATCH | `/api/v1/admin/sales/{id}/` | Partial update |
| DELETE | `/api/v1/admin/sales/{id}/` | Delete |
| POST | `/api/v1/admin/sales/{id}/products/reorder/` | Mahsulotlar tartibi (drag & drop) |

---

## Pagination

`AdminPagination` (`PageNumberPagination`): `?page=&page_size=`, default 20, max 100.

Response shape:
```json
{
  "count": 10,
  "next": "...",
  "previous": null,
  "next_page": 2,
  "previous_page": null,
  "results": [...]
}
```

---

## Filters

| Param | Type | Description |
|-------|------|-------------|
| `is_main` | bool | Faqat asosiy aksiyani qaytarish |
| `is_visible` | bool | Ko'rinish holati |
| `from_discount` | date (YYYY-MM-DD) | `discount_from >= value` |
| `to_discount` | date (YYYY-MM-DD) | `discount_to <= value` |
| `search` | string | `name` bo'yicha qidirish |
| `ordering` | string | `id`, `name`, `discount_from`, `discount_to`, `is_main`, `is_visible`, `created_at` (minus = desc) |

---

## List serializer fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | |
| `name` | string | |
| `image` | url | |
| `bg_image` | url | |
| `discount_from` | date | |
| `discount_to` | date | |
| `is_main` | bool | |
| `is_visible` | bool | |
| `products_count` | int | annotated |
| `created_at` | datetime | |
| `updated_at` | datetime | |

---

## Detail / Create / Update serializer fields

Same as list plus:

| Field | Type | Notes |
|-------|------|-------|
| `products` | array | `[{"id": pk}, ...]` yoki `[pk, ...]` — yuborilgan ro'yxat hammasini almashtiradi, **ro'yxat tartibi = aksiyadagi tartib** (`position`); javobda ham shu tartibda |

`products` item:
```json
{"id": 1, "name": "...", "product_code": "...", "price": 100.0, "discount_price": 80.0, "is_active": true}
```

---

## Mahsulotlar tartibi (drag & drop)

`POST /api/v1/admin/sales/{id}/products/reorder/`

```json
{"ids": [12, 5, 40]}
```

- `ids` — aksiya mahsulotlarining **product id**lari yangi tartibda (index → `position`).
- Ro'yxatning bir qismini yuborish mumkin: yuborilmaganlar o'z tartibida yuborilganlardan keyin turadi.
- Aksiyada yo'q id → `400` (`Not in the sale: [...]`), takroriy id → `400`.
- Javob: `{"ids": [...]}` — aksiyaning barcha mahsulotlari yakuniy tartibda.

Drag & drop'dan keyin shu endpointni chaqirish kifoya; yoki `PATCH {id}/` bilan `products` ni yangi tartibda yuborish ham bo'ladi (bu ro'yxatni to'liq almashtiradi).

Tartib clientda ham ishlatiladi:
- `GET /api/v1/sales/main/` — `products` shu tartibda;
- `POST /api/v1/product/filter/` `sale_id` bilan, `sort_by` va `q` yuborilmaganda — shu tartibda (`sort_by` yuborilsa, o'sha tartiblash ishlaydi);
- bosh sahifa `sale_products` bloki (`GET /api/v1/home/blocks/{id}/products/`) — shu tartibda.

---

## Business rules

- `is_main=true` — faqat bitta Sale bo'lishi mumkin. Agar boshqa Sale allaqachon `is_main=true` bo'lsa, `400` qaytadi.
- `products` ro'yxati to'liq almashtiriladi (set), tartibi saqlanadi. Bo'sh ro'yxat (`[]`) ham qabul qilinadi, takroriy mahsulot → `400`.
- Multipart form (`image`, `bg_image`) yoki JSON + alohida PATCH orqali yuklash mumkin.

---

## Model

`apps/service/models/marketing.py` — `Sale`.

Fields: `products` (M2M → `Product` through `SaleProduct`: `sale`, `product`, `position`; table `service_sale_products`, migration 0118 numbers the existing rows in the order they were added), `name`, `image`, `bg_image`, `discount_from`, `discount_to`, `is_main`, `is_visible`.
