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
| `products` | array | `[{"id": pk}, ...]` — sent list replaces all products |

`products` item:
```json
{"id": 1, "name": "...", "product_code": "...", "price": 100.0, "discount_price": 80.0, "is_active": true}
```

---

## Business rules

- `is_main=true` — faqat bitta Sale bo'lishi mumkin. Agar boshqa Sale allaqachon `is_main=true` bo'lsa, `400` qaytadi.
- `products` ro'yxati to'liq almashtiriladi (set). Bo'sh ro'yxat (`[]`) ham qabul qilinadi.
- Multipart form (`image`, `bg_image`) yoki JSON + alohida PATCH orqali yuklash mumkin.

---

## Model

`apps/service/models/marketing.py` — `Sale`.

Fields: `products` (M2M → `Product`), `name`, `image`, `bg_image`, `discount_from`, `discount_to`, `is_main`, `is_visible`.
