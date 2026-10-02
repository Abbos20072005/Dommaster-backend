# Badge (teg)lar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET product-badges/` | ro'yxat (paginatsiyali, default tartib — `position`) |
| `POST product-badges/` | yaratish |
| `GET / PATCH / DELETE product-badges/{id}/` | bitta badge |
| `POST product-badges/reorder/` | tartibni o'zgartirish (`{"ids": [...]}`) |

Swagger: `/swagger/admin/` → **product-badges**.

Bitta mahsulotda **bir nechta** badge bo'lishi mumkin (`products/` dagi `badges` ro'yxati).

---

## Obyekt

```json
{
  "id": 5,
  "name": "Акция",
  "name_uz": "Aksiya",
  "name_ru": "Акция",
  "name_en": null,
  "kind": "auto",
  "rule_field": "discount",
  "rule_operator": "gt",
  "rule_value": 0,
  "color": "#DC2626",
  "position": 1,
  "is_active": true,
  "products_count": 342,
  "created_at": "2026-10-02T13:26:43",
  "updated_at": "2026-10-02T13:26:43"
}
```

| Maydon | Izoh |
| --- | --- |
| `name_ru` * | majburiy (asosiy til); `name_uz`, `name_en` ixtiyoriy |
| `kind` | Turi: `manual` (Qo'lda, default) / `auto` (Avtomatik) |
| `rule_field` | `discount` — Chegirma, %; `created_days` — Qo'shilgan, kun; `quantity` — Qoldiq, dona; `sales_30d` — Sotuvlar (30 kun) |
| `rule_operator` | `gt` `>`, `gte` `≥`, `lt` `<`, `lte` `≤`, `eq` `=` |
| `rule_value` | butun son, `>= 0` (`discount` uchun `<= 100`) |
| `color` | Nishon rangi, HEX: `#RRGGBB` (default `#2563EB`) |
| `position` | badge'larning tartibi (mahsulot kartochkasida ham shu tartibda); yuborilmasa yangi badge oxiriga qo'shiladi |
| `is_active` | Holat: `true` — Faol, `false` — Qoralama |

Faqat o'qiladi: `id`, `name`, `products_count`, `created_at`, `updated_at`.

`kind=auto` bo'lsa uchala `rule_*` majburiy. `kind=manual` bo'lsa `rule_*` e'tiborga olinmaydi va `null` bo'lib saqlanadi.

Filtrlar: `?is_active=`, `?kind=`, `?rule_field=`, `?search=`, `?ordering=position|name|products_count|created_at`.

---

## Qoidalar qanday hisoblanadi

| `rule_field` | Nima solishtiriladi |
| --- | --- |
| `discount` | mahsulotning chegirma foizi (bo'sh = 0) |
| `created_days` | mahsulot qo'shilganidan beri o'tgan to'liq kunlar. "Yangi: 30 kun" = `created_days` `lt` `30` |
| `quantity` | qoldiq (`quantity`) |
| `sales_30d` | oxirgi 30 kunda bekor qilinmagan buyurtmalarda sotilgan dona (sotilmagan = 0) |

- `auto` badge'ning mahsulotlari — qoidaga mos keladigan **barcha** mahsulotlar. Bitta mahsulot bir nechta avtomatik badge'ga tushishi mumkin, shuning uchun `products_count` lar kesishadi.
- `manual` badge'ning mahsulotlari faqat qo'lda (mahsulot formasida) belgilanadi, qayta hisoblash ularga tegmaydi.
- `is_active=false` (Qoralama) badge ham hisoblanadi (`products_count` ko'rinadi), lekin mijozga ko'rsatilmasligi kerak.
- Badge yaratilganda / o'zgartirilganda qoida darhol qo'llanadi (javobdagi `products_count` yangi). 1C ma'lumotlari o'zgarganda — har 15 daqiqada (cron, `manage.py recalculate_badges`). Yangi mahsulot ham avtomatik badge'larni shu paytda oladi.
- `auto` → `manual`: o'sha paytdagi mahsulotlar badge'da qoladi. `manual` → `auto`: qo'lda tanlanganlar o'rniga qoidaga mos mahsulotlar qo'yiladi.

## Tartib

```json
POST product-badges/reorder/
{ "ids": [6, 5, 7] }
```

Ro'yxatdagi tartib = `position` (1 dan). Javob: `200 {"ids": [6, 5, 7]}`.

## Mahsulot formasi

`products/` da `badges` — ro'yxat (`position` bo'yicha):

```json
"badges": [
  { "id": 7, "name": "Хит", "kind": "manual", "color": "#2563EB" },
  { "id": 5, "name": "Акция", "kind": "auto", "color": "#DC2626" }
]
```

Yozishda: `"badges": [{"id": 7}]` yoki `"badges": [7]`.

- Yuborilgan ro'yxat mahsulotning **qo'lda** qo'yilgan badge'larini almashtiradi (`[]` — hammasini olib tashlaydi).
- Ro'yxatdagi `auto` badge'lar e'tiborga olinmaydi — ular faqat qoida bo'yicha qo'yiladi/olinadi. Formada tanlash uchun `product-badges/?kind=manual` dan foydalaning.
- `badges` yuborilmasa, hech narsa o'zgarmaydi.
- Ro'yxat filtri: `products/?badge=<id>`.

> Badge'lar hozircha faqat admin API'da — mijoz (sayt / ilova) API'lariga chiqarilmagan.
