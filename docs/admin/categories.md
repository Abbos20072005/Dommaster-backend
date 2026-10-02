# Kategoriyalar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

Katalog 3 darajali: **L1** `categories/` → **L2** `sub-categories/` → **L3** `item-categories/`. Mahsulot faqat L3 ga biriktiriladi.

| Endpoint | Nima uchun |
| --- | --- |
| `GET categories/tree/` | butun daraxt bitta javobda (jadval sahifasi) |
| `GET / POST categories/`, `GET / PATCH / DELETE categories/{id}/` | L1 CRUD |
| `GET / POST sub-categories/`, `GET / PATCH / DELETE sub-categories/{id}/` | L2 CRUD |
| `GET / POST item-categories/`, `GET / PATCH / DELETE item-categories/{id}/` | L3 CRUD |
| `POST categories/reorder/`, `sub-categories/reorder/`, `item-categories/reorder/` | drag & drop tartiblash |

Swagger: `/swagger/admin/` → **categories**, **sub-categories**, **item-categories**.

---

## 1. Daraxt — `GET categories/tree/`

Paginatsiyasiz, oddiy massiv. Har darajada `position`, keyin `id` bo'yicha tartiblangan. L1 va L2 da `children` bor, L3 da yo'q.

```json
[
  {
    "id": 6,
    "name_uz": "Elektr jihozlari",
    "name_ru": "Электрика",
    "slug": "elektr-jihozlari",
    "code": "000000012",
    "position": 1,
    "show_on_site": true,
    "show_in_app": true,
    "is_active": true,
    "products_count": 4820,
    "filters_count": 6,
    "children": [
      {
        "id": 2,
        "name_uz": "Avtomatlar",
        "...": "...",
        "children": [
          { "id": 1, "name_uz": "Bir qutbli avtomatlar", "...": "..." }
        ]
      }
    ]
  }
]
```

| Jadval ustuni | Maydon |
| --- | --- |
| Nomi (UZ) | `name_uz` |
| RU | `name_ru` bo'sh / `null` bo'lsa → "yo'q" |
| Mahsulot | `products_count` — shu kategoriya ostidagi barcha mahsulotlar |
| Sayt | `show_on_site` |
| Ilova | `show_in_app` |
| Filtrlar | `filters_count` — ostidagi L3 kategoriyalarning turli (unikal) filtrlari soni |
| Holat | `is_active`: `true` = Faol, `false` = Qoralama |

`code` — 1C kodi (bitta kategoriya = bitta 1C guruh). "1C guruhlari" soni hozircha yo'q.

---

## 2. Forma (yaratish / tahrirlash)

Uchala darajada maydonlar bir xil, farqi faqat ota kategoriya va rasmlarda.

| Maydon | Izoh |
| --- | --- |
| `name_uz` * | Nomi (UZ) — majburiy |
| `name_ru` * | Nomi (RU) — majburiy |
| `name_en` | ixtiyoriy |
| `slug` | faqat `a-z 0-9 - _`, shu daraja ichida unikal. Yuborilmasa yoki bo'sh (`""`) bo'lsa `name_uz` dan avtomatik yasaladi (`Rozetka va o'chirgichlar` → `rozetka-va-ochirgichlar`, band bo'lsa `-2`, `-3`) |
| `meta_title_uz`, `meta_title_ru`, `meta_title_en` | SEO sarlavha (tavsiya ≤ 60 belgi, backend 255 gacha qabul qiladi) |
| `meta_description_uz`, `meta_description_ru`, `meta_description_en` | SEO tavsif (tavsiya ≤ 160 belgi) |
| `show_on_site` | "Sayt" toggle, default `true` |
| `show_in_app` | "Buildex Go ilovasi" toggle, default `true` |
| `is_active` | Holat: `true` = Faol, `false` = Qoralama |
| `position` | tartib raqami (odatda `reorder/` orqali o'zgaradi) |
| `code` | 1C kodi, ixtiyoriy |
| `product_category` | **faqat L2** — ota L1: `{"id": 6}` yoki `6` |
| `product_sub_category` | **faqat L3** — ota L2: `{"id": 2}` yoki `2` |
| `icon`, `image` | **L1** da ikkalasi majburiy (multipart); L2 / L3 da faqat `image`, ixtiyoriy |

Faqat o'qiladi: `id`, `name`, `products_count`, `filters_count`, `children_count` (L1, L2), `created_at`, `updated_at`.

Misol — `POST sub-categories/`:

```json
{
  "name_uz": "Avtomatlar",
  "name_ru": "Автоматы",
  "product_category": 6,
  "meta_title_uz": "Avtomatlar — Toshkentda sotib olish | Buildex",
  "meta_description_uz": "",
  "show_on_site": true,
  "show_in_app": false,
  "is_active": true
}
```

Xatolar (`400`):

```json
{ "name_uz": ["This field is required."] }
{ "slug": ["Предметная категория продуктов с таким Slug уже существует."] }
```

O'chirish: ostida mahsulot bor kategoriya o'chirilmaydi → `400 {"detail": "Category has products, move them to another category first."}`.

> `show_on_site` / `show_in_app` hozircha faqat saqlanadi — mijoz (sayt / ilova) API'lari hali ularga qaramaydi, ko'rinishni `is_active` boshqaradi. `slug` va SEO maydonlari ham mijoz API'lariga hali chiqarilmagan.

---

## 3. Tartiblash — `POST {daraja}/reorder/`

Drag & drop'dan keyin bitta ota ichidagi (bir darajadagi) kategoriyalar `id` lari yangi tartibda yuboriladi; ro'yxatdagi o'rni `position` bo'ladi (1 dan).

```json
{ "ids": [12, 7, 9] }
```

Javob `200` — xuddi shu body. Takroriy yoki mavjud bo'lmagan id → `400 {"ids": ["Not found: [999]"]}`.

---

## 4. Ro'yxatlar (paginatsiyali)

`GET categories/`, `sub-categories/`, `item-categories/` — `?page=&page_size=`.

- Qidiruv: `?search=` (nomi uz/ru/en, `code`, `slug`)
- Filtrlar: `is_active`, `show_on_site`, `show_in_app`, `has_products`, `has_children` (L1, L2), `product_category` (L2), `product_sub_category`, `category` (L3)
- Tartib: `?ordering=position` (`id`, `name`, `products_count`, `children_count`, `created_at`, `updated_at`)
