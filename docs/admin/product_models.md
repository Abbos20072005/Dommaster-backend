# Modellar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET product-models/` | modellar ro'yxati (paginatsiyali) |
| `POST product-models/` | model yaratish |
| `GET / PATCH / DELETE product-models/{id}/` | bitta model |

Swagger: `/swagger/admin/` → **product-models**.

Model — brendning model qatori (masalan Chint → `NXB-63`). Har bir model **bitta brendga** tegishli, mahsulot esa faqat **o'z brendining** modelini tanlaydi.

---

## Obyekt

```json
{
  "id": 4,
  "name": "NXB-63",
  "brand": { "id": 24, "name": "Chint" },
  "is_active": true,
  "products_count": 48,
  "created_at": "2026-10-02T13:48:45",
  "updated_at": "2026-10-02T13:48:45"
}
```

| Maydon | Izoh |
| --- | --- |
| `name` * | nomi, 150 belgigacha (tarjimasiz); bitta brend ichida unikal (katta-kichik harf farqsiz) |
| `brand` * | brend: `{"id": 24}` yoki shunchaki `24` |
| `is_active` | Holat: `true` — Faol (default), `false` — Qoralama |

Faqat o'qiladi: `id`, `products_count`, `created_at`, `updated_at`.

Yaratish:

```json
{ "name": "NXB-63", "brand": { "id": 24 } }
```

Xatolar (`400`):

- `{"name": ["This brand already has a model with this name."]}` — shu brendda bunday model bor
- `{"brand": ["Model has products, its brand can't be changed."]}` — mahsuloti bor modelning brendini o'zgartirib bo'lmaydi
- O'chirish: mahsuloti bor model o'chirilmaydi → `{"detail": "Model has products, deactivate it instead (is_active=false)."}`

Brend o'chirilsa, uning modellari ham o'chadi (mahsuloti bor brend baribir o'chirilmaydi).

---

## Ro'yxat

`GET product-models/?page=&page_size=`

- Qidiruv: `?search=` (nomi)
- Filtrlar: `brand` (brend id), `is_active`, `has_products`
- Tartib: `?ordering=` `id`, `name`, `products_count`, `created_at`, `updated_at` (teskari: `-name`)

---

## Mahsulotda

`products/` (ro'yxat va detail) da `product_model` maydoni bor:

```json
{ "brand": { "id": 24, "name": "Chint" }, "product_model": { "id": 4, "name": "NXB-63" } }
```

- Yozish (detail): `"product_model": {"id": 4}` yoki `4`; `null` — modelni olib tashlash.
- Model mahsulot brendiga tegishli bo'lishi shart, aks holda `400 {"product_model": ["Model belongs to another brand."]}`.
- Mahsulot formasi uchun tanlov ro'yxati: `GET product-models/?brand=<brand_id>&is_active=true`.
- Mahsulotning brendi o'zgartirilsa-yu `product_model` yuborilmasa, eski brendning modeli avtomatik olib tashlanadi (`null`).
- Filtr: `GET products/?product_model=<id>`.

> Modellar hozircha faqat admin API'da — mijoz (sayt / ilova) API'lariga chiqarilmagan.
