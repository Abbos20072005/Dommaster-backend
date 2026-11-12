# Mahsulot qo'shish — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `POST products/` | mahsulot yaratish (JSON, **rasmsiz**) |
| `POST products/{id}/images/` | rasm yuklash (multipart, bitta so'rovda bitta rasm) |
| `POST products/{id}/images/reorder/` | rasmlar tartibi / asosiy rasm |
| `PATCH products/{id}/` | keyin tahrirlash (xuddi shu maydonlar) |

Swagger: `/swagger/admin/` → **products**.

---

## Tartib: avval mahsulot, keyin rasmlar

`POST products/` rasm qabul **qilmaydi** (`images` faqat o'qiladi, JSON body). Rasmlar mahsulotning `id`si bilan alohida yuklanadi, shuning uchun forma "Saqlash" bosilganda:

1. `POST products/` — JSON body bilan mahsulot yaratiladi → javobda `id`.
2. Har bir rasm uchun `POST products/{id}/images/` (multipart, maydon `image`, ixtiyoriy `alt_uz`, `alt_ru`). Rasmlar **ketma-ket** yuborilsin — har yangi rasm ro'yxat oxiriga tushadi, birinchi yuklangani asosiy rasm bo'ladi.
3. Kerak bo'lsa `POST products/{id}/images/reorder/` `{"ids": [...]}` — tartib / asosiy rasmni o'zgartirish.
4. Hammasi tayyor bo'lgach `PATCH products/{id}/` `{"is_active": true}` (yoki moderatsiyaga `{"publish_status": "review"}`).

1-qadam o'tib, rasm yuklash xato bersa — mahsulot allaqachon bor. Formani qayta "yaratish" rejimida yubormang (ikkinchi nusxa paydo bo'ladi): shu `id` bilan rasmlarni qayta yuklang yoki formani tahrirlash rejimiga o'tkazing.

Rasm endpointlari batafsil: `docs/admin/product_images.md`.

---

## `POST products/`

Minimal so'rov:

```json
{
  "name_ru": "Перфоратор Bosch GBH 2-26",
  "description_ru": "<p>Описание</p>"
}
```

To'liq misol:

```json
{
  "name_uz": "Bosch GBH 2-26 perforatori",
  "name_ru": "Перфоратор Bosch GBH 2-26",
  "short_description_uz": "...",
  "short_description_ru": "...",
  "description_uz": "<p>...</p>",
  "description_ru": "<p>...</p>",
  "brand": 7,
  "product_model": 3,
  "product_item_category": 120,
  "badges": [2],
  "price": 1500000,
  "discount_price": 1350000,
  "discount": 10,
  "unit": "pcs",
  "quantity": 5,
  "articul_code": "GBH 2-26",
  "barcode": "4059952512345",
  "weight": "2.900",
  "length": "0.400",
  "width": "0.100",
  "height": "0.250",
  "attribute_values": [
    { "attribute": 14, "value_uz": "800", "value_ru": "800" }
  ],
  "related_products": [101, 102],
  "alternative_products": [],
  "cross_sell_products": [{ "id": 300 }],
  "publish_status": "draft"
}
```

Javob `201` — mahsulotning to'liq detail obyekti (`GET products/{id}/` bilan bir xil), `images: []`.

### Maydonlar

`*` = majburiy.

| Maydon | Turi | Izoh |
| --- | --- | --- |
| `name_ru` * | string | ≤ 500 belgi |
| `description_ru` * | string (HTML) | |
| `name_uz` | string | bo'sh bo'lsa uz tilida ru nomi ko'rinadi |
| `short_description_uz` / `_ru`, `description_uz` | string | |
| `brand` | id yoki `{"id"}`, null | |
| `product_model` | id yoki `{"id"}`, null | shu brendning modeli bo'lishi shart (`product-models/?brand=`) |
| `product_item_category` | id yoki `{"id"}`, null | predmet kategoriya (3-daraja) |
| `badges` | id ro'yxati | faqat qo'lda (`manual`) teglar, auto teglar e'tiborsiz |
| `price` | number ≥ 0 | default `0` |
| `discount_price` | number ≥ 0, null | `price` dan katta bo'lmasin |
| `discount` | int 0–100, null | |
| `unit` | `kg` `l` `sm` `pcs` `m` `g` `pkg` `set` | default `pcs` |
| `quantity` | int ≥ 0 | default `0` |
| `articul_code`, `barcode` | string | |
| `product_code` | string, null | **1C kodi** — paneldan yaratilganda yubormang (pastga qarang) |
| `weight`, `length`, `width`, `height` | decimal string | kg / m |
| `attribute_values` | ro'yxat | `product_item_category` ga biriktirilgan atributlar (`GET item-categories/{id}/attributes/`); `number` → `"2.5"`, `boolean` → `"true"`/`"false"` (uz = ru), `list` → variantning `value_uz` / `value_ru`; atribut takrorlanmasin |
| `related_products`, `alternative_products`, `cross_sell_products` | id / `{"id"}` ro'yxati | ≤ 20 tadan, takrorlanmasin; ro'yxat tartibi = ko'rinish tartibi |
| `is_active` | bool | **yubormasangiz `false`** (yashirin) |
| `erp_active` | bool | yubormasangiz `false` |
| `publish_status` | `draft` / `review` / `published` | default `draft`; `review` → moderatsiya navbatiga tushadi |
| `purchasable`, `on_order` | bool | default `false` |
| `slug_uz`, `slug_ru` | string | yubormasangiz nomdan avtomatik: `<nom>-<id>` |
| `meta_title_uz/_ru`, `meta_description_uz/_ru` | string | |

Faqat o'qiladigan: `id`, `name`, `images`, `characteristics`, `rating`, `comments_quantity`, `questions_quantity`, `last_moderation`, `created_at`, `updated_at`.

### Muhim

- **Yangi mahsulot yashirin yaratiladi** (`is_active=false`), toki `is_active: true` yuborilmaguncha. Saytda / ilovada ko'rinishi uchun rasmlar yuklangandan keyin `PATCH products/{id}/` `{"is_active": true}`.
- **`product_code` yubormang.** Paneldan yaratilgan mahsulot 1C bilan bog'lanmaydi: 1C keyinchalik shu tovarni o'z kodi bilan yuborsa, u **ikkinchi alohida kartochka** bo'lib qo'shiladi. Kodni faqat 1C dagi kod aniq ma'lum bo'lsa kiriting (kod unikal — band bo'lsa `400`).
- Rasm `POST products/` ichida yuborilmaydi — yuqoridagi tartib bo'yicha alohida.

---

## Xatolar

| Status | Qachon |
| --- | --- |
| `400 {"name_ru": [...], "description_ru": [...]}` | majburiy maydon yo'q |
| `400 {"discount_price": ["Must not be greater than price."]}` | chegirma narxi narxdan katta |
| `400 {"product_model": ["Model belongs to another brand."]}` | model boshqa brendniki |
| `400 {"attribute_values": ["Attributes [..] are not attached to the product's item category."]}` | atribut kategoriyaga biriktirilmagan |
| `400 {"attribute_values": [...{"value_ru": [...]}]}` | qiymat atribut turiga mos emas |
| `400 {"product_code": [...]}` | 1C kodi band (boshqa mahsulotda bor) |
| `400 {"related_products": ["Products must be unique."]}` | ro'yxatda takror |
| `401` / `403` | token yo'q / admin emas |
