# SEO maydonlari va 301 — client (sayt / ilova)

Base URL: `{{host}}/api/v1/`
Til: `Accept-Language: uz` yoki `ru` (bo'sh uz → ru). Hamma SEO matni so'rov tilida keladi.

## Maydonlar

Tovar, brend va kategoriya javoblariga qo'shildi:

| Maydon | Qayerda |
| --- | --- |
| `slug` | tovar (`products/`, `products/{id}/`), brend, kategoriya (barcha darajalar, ro'yxat va detalda) |
| `meta_title`, `meta_description` | tovar detali, brend detali, kategoriya detallari |
| `image_alt` | brend detali, kategoriya detallari |
| `images[].alt` | tovar rasmlari |

`meta_title` / `meta_description` **bo'sh bo'lsa `null`** keladi — bunda sahifa sarlavhasi/tavsifini
kelishilgan shablondan yasang (BLD-238). `image_alt` / `images[].alt` bo'sh bo'lsa alt o'rniga nom ishlating.

`slug` manzil qurish uchun: `/product/<slug>`, `/brand/<slug>`, `/catalog/<cat>/<sub>/<item>` (kategoriya
darajalarining slug'laridan). Tovar slug'i `<nom>-<id>` ko'rinishida (`kley-ventum-571`).

### Breadcrumbs

Tovar va kategoriya detallarining `breadcrumbs` ro'yxatida har daraja uchun `slug` ham keladi — manzilni
qo'shimcha so'rovsiz shu ro'yxatdan quramiz:

```json
"breadcrumbs": [
  { "id": 3, "slug": "krepezh", "name": "Крепеж", "level": "product_category" },
  { "id": 12, "slug": "ankery", "name": "Анкеры", "level": "product_sub_category" },
  { "id": 44, "slug": "ankernyy-bolt", "name": "Анкерный болт", "level": "product_item_category" },
  { "id": 571, "slug": "kley-ventum-571", "name": "Клей Ventum", "level": "product" }
]
```

## Slug resolve (301 redirect)

```
GET /api/v1/seo/resolve/?type=<type>&slug=<slug>
```

`type`: `product | category | sub_category | item_category | brand`. Til — `Accept-Language` dan.

Javob:

```json
{ "result": { "status": "current", "type": "product", "id": 571, "slug": "..." }, "ok": true }
```

| `status` | Sayt nima qiladi |
| --- | --- |
| `current` | slug joriy — sahifani shu manzilda ochadi |
| `moved` | slug eski/o'zgargan — `result.slug` (joriy slug) ga **301** qiladi |
| `not_found` | bunday slug (va tarixda ham) yo'q — **404** |

Faqat ko'rinadigan obyektlar hal qilinadi (tovar/kategoriya `is_active`, brend `is_visible`). Noto'g'ri
`type` yoki bo'sh `slug` → `400` (`error_code: 5`).

`moved` **faqat kategoriya va brend** uchun bo'ladi — slug tarixi shu ikkisida yuritiladi. Tovarning eski
slug'i `not_found` qaytaradi (404): tovar slug'ida id turadi, shuning uchun `/product/<yangi-slug>` manzili
o'zgarmaydi.

**Oqim**: foydalanuvchi `/product/<slug>` ga kirsa, sayt `resolve` ni chaqiradi. `current` → sahifa;
`moved` → yangi slugga 301; `not_found` → 404.
