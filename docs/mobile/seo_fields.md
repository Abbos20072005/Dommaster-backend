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
{ "result": { "status": "current", "type": "product", "id": 571, "slug": "...", "redirect": null }, "ok": true }
```

| `status` | Sayt nima qiladi |
| --- | --- |
| `current` | slug joriy — sahifani shu manzilda ochadi |
| `moved` | slug eski/o'zgargan — `result.slug` (joriy slug) ga **301** qiladi |
| `gone` | (faqat tovar) tovar yashirilgan yoki o'chirilgan — `redirect` bo'lsa unga **301**, `redirect: null` bo'lsa **410** |
| `not_found` | bunday slug (va tarixda ham) yo'q — **404** |

`redirect` faqat `gone` da to'ladi, boshqa holatlarda `null`.

Faqat ko'rinadigan obyektlar `current` / `moved` bo'ladi (tovar/kategoriya `is_active`, brend `is_visible`).
Noto'g'ri `type` yoki bo'sh `slug` → `400` (`error_code: 5`).

Kategoriya va brend slug'i nom o'zgarsa ham o'zgarmaydi; qo'lda o'zgartirilsa eski slug tarixda qoladi va
`moved` beradi. **Tovar** slug'i esa nom o'zgarganda **yangi nomdan qayta yasaladi** (`…-asfora-antratsit-571`
→ `…-asfora-10-a-antratsit-571`). Tovarning tarixi yo'q — eski slug **oxiridagi id** bo'yicha topiladi va
`moved` + joriy `slug` qaytadi. Shuning uchun eski tovar manzili ham 301 bo'ladi, 404 emas. Tovar **faqat
id** bilan ham topiladi (`slug=571` — eski `/product/<id>` havolalari, merchant feed'lar uchun).

### O'chirilgan / yashirilgan tovar (`gone`)

Tovar nofaol bo'lsa (`is_active=false`) yoki bazadan o'chirilgan bo'lsa (backend o'chirilgan tovar id'sini,
uning item kategoriyasini va qo'lda tanlangan analoglarini eslab qoladi):

```json
{
  "result": {
    "status": "gone", "type": "product", "id": 571, "slug": null,
    "redirect": {
      "type": "item_category", "id": 42, "slug": "vyklyuchateli",
      "breadcrumbs": [
        {"id": 3, "slug": "elektrika", "name": "Электрика", "level": "product_category"},
        {"id": 17, "slug": "elektroustanovochnye-izdeliya", "name": "...", "level": "product_sub_category"},
        {"id": 42, "slug": "vyklyuchateli", "name": "Выключатели", "level": "product_item_category"}
      ]
    }
  },
  "ok": true
}
```

`redirect` qanday tanlanadi:
1. admin panelda qo'lda tanlangan **analog** (`alternative_products`, birinchi faoli) → `type: "product"`,
   `breadcrumbs` oxirida tovarning o'zi;
2. bo'lmasa tovarning **item kategoriyasi**, u nofaol bo'lsa **sub kategoriya**, u ham nofaol bo'lsa
   **kategoriya** (birinchi faol daraja) → `type: "item_category" | "sub_category" | "category"`;
3. hech biri yo'q → `redirect: null` → sayt **410** beradi.

`redirect` manzili har doim joriy (faol obyekt, joriy slug) — 301 zanjiri bo'lmaydi. URL'ni `breadcrumbs`
dan yig'ing (`/catalog/<cat>/<sub>/<item>`, tovar — `/product/<slug>`), xuddi kategoriya sahifalaridagidek.

**Oqim**: foydalanuvchi `/product/<slug>` ga kirsa, sayt `resolve` ni chaqiradi. `current` → sahifa;
`moved` → yangi slugga 301; `gone` → `redirect` ga 301 yoki 410; `not_found` → 404 (qidiruvli 404 sahifa).

## O'chirilgan yangilik — 410

`GET /api/v1/base/news/<id>/` o'chirilgan yangilik uchun **`410`** (`error_code: 40`) qaytaradi, umuman
bo'lmagan id uchun avvalgidek **`404`** (`error_code: 4`). Sayt shu statusni o'zi ham qaytaradi. Bu
o'zgarishdan oldin o'chirilgan yangiliklar backendga ma'lum emas — ular 404 bo'lib qoladi.

## 304 (o'zgarmagan)

Barcha `GET` javoblarida `ETag` bor: so'rovda `If-None-Match: <etag>` yuborilsa va javob o'zgarmagan bo'lsa
`304` (bo'sh tana) qaytadi. `feeds/google.xml` / `feeds/yandex.yml` da `Last-Modified` ham bor
(`If-Modified-Since` → `304`). Sayt sahifalarining o'z `Last-Modified` i uchun tovar / yangilik javobidagi
`updated_at` dan foydalaning.
