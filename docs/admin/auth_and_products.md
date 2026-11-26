# Login va mahsulotlar (CRUD) — admin panel uchun

Bitta fayl: admin panelga kirish (login, token yangilash, profil, parol almashtirish) va mahsulotlar bo'limi — ro'yxat, filtrlar, statistika, detail, yaratish, tahrirlash, o'chirish, rasmlar. Boshqa docsga qarash shart emas.

Base URL: `{{host}}/api/v1/admin/`
Swagger: `/swagger/admin/` → **auth**, **products**.

| Endpoint | Token | Nima uchun |
| --- | --- | --- |
| `POST auth/login/` | yo'q | login + parol → tokenlar + admin profili |
| `POST auth/token/refresh/` | yo'q | refresh token → yangi tokenlar juftligi |
| `GET auth/me/` | bor | joriy admin profili |
| `POST auth/change-password/` | bor | o'z parolini almashtirish |
| `GET products/` | bor | mahsulotlar ro'yxati (paginatsiya, filtr, qidiruv, tartib) |
| `GET products/stats/` | bor | ro'yxat ustidagi kartochkalar (jami / faol / ...) |
| `GET products/{id}/` | bor | mahsulot detail |
| `POST products/` | bor | mahsulot yaratish (JSON, **rasmsiz**) |
| `PATCH products/{id}/` | bor | tahrirlash (faqat yuborilgan maydonlar o'zgaradi) |
| `DELETE products/{id}/` | bor | o'chirish (buyurtmada bo'lmasa) |
| `POST products/{id}/images/` | bor | bitta rasm yuklash (multipart) |
| `POST products/{id}/images/reorder/` | bor | rasmlar tartibi / asosiy rasm |
| `DELETE products/{id}/images/{image_id}/` | bor | rasmni o'chirish |

Xato javoblari oddiy DRF ko'rinishida: `{"detail": "..."}` yoki maydon bo'yicha `{"<maydon>": ["..."]}`. `{"result", "ok"}` o'rami **yo'q** (u faqat mobil / sayt API'da).

---

## 1. Login va token

### 1.1 Token qanday ishlatiladi

Login'dan keyin har bir so'rovga header qo'shiladi:

```
Authorization: Bearer <access>
```

| Token | Amal qilish muddati | Nima uchun |
| --- | --- | --- |
| `access` | **1 kun** (serverda `ACCESS_TOKEN_LIFETIME_DAYS`) | har bir so'rovda |
| `refresh` | **2 kun** (`REFRESH_TOKEN_LIFETIME_DAYS`) | faqat `auth/token/refresh/` ga |

- Token yo'q / muddati o'tgan / noto'g'ri → `401`.
- Token bor, lekin akkaunt bloklangan yoki xodim emas → `401` (`Admin not found`) yoki `403`.
- Admin tokeni mijoz (mobil ilova) API'sida ishlamaydi va aksincha.

### 1.2 `POST auth/login/`

```json
{ "username": "kamola.e", "password": "S3cret-pass" }
```

| Maydon | |
| --- | --- |
| `username` * | ≤ 150; harf registri farq qilmaydi (`Kamola.E` = `kamola.e`) |
| `password` * | ≤ 128 |

Javob `200`:

```json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "refresh": "eyJhbGciOiJIUzI1NiIs...",
  "admin": {
    "id": 3,
    "username": "kamola.e",
    "first_name": "",
    "last_name": "",
    "email": "",
    "is_superuser": false,
    "last_login": "2026-11-24T09:12:40.512301",
    "full_name": "Kamola Ergasheva",
    "position": "Kontent menejer",
    "access_level": "staff",
    "must_change_password": true
  }
}
```

| `admin` maydoni | Izoh |
| --- | --- |
| `id` | admin id |
| `username` | login |
| `full_name`, `position` | xodim kartasidan (bo'sh bo'lishi mumkin) |
| `access_level` | `staff` yoki `super_admin` (= `is_superuser`). `super_admin` faqat "Xodimlar" bo'limiga kirish uchun kerak; mahsulotlar bo'limi ikkalasiga ham ochiq |
| `must_change_password` | `true` → admin yangi parol o'rnatishi kerak (frontga belgi, server majburlamaydi) — 1.5 ga qarang |
| `last_login` | oxirgi kirish vaqti (Toshkent vaqti, timezone'siz) |

Xatolar:

| Status | Javob | Qachon |
| --- | --- | --- |
| `400` | `{"username": ["Обязательное поле."]}` | maydon yo'q / bo'sh |
| `401` | `{"detail": "Incorrect username or password"}` | login yoki parol noto'g'ri |
| `403` | `{"detail": "Account is blocked"}` | akkaunt bloklangan (parol to'g'ri bo'lsa ham shu javob) |
| `403` | `{"detail": "..."}` | foydalanuvchi xodim emas |

**Bloklash:** ketma-ket **5 marta** noto'g'ri parol → akkaunt bloklanadi, 5-urinishning o'zidayoq `403 Account is blocked` qaytadi. Blokdan faqat super admin "Xodimlar" bo'limida chiqaradi. To'g'ri login hisoblagichni nolga qaytaradi.

### 1.3 `POST auth/token/refresh/`

```json
{ "refresh": "eyJhbGciOiJIUzI1NiIs..." }
```

Javob `200` — **yangi juftlik**, ikkalasini ham saqlang:

```json
{ "access": "eyJ...", "refresh": "eyJ..." }
```

Xato: `401 {"detail": "...", "code": "token_not_valid"}` — refresh muddati o'tgan / noto'g'ri, yoki akkaunt bloklangan / o'chirilgan → login sahifasiga.

### 1.4 `GET auth/me/`

Javob `200` — login javobidagi `admin` obyektining o'zi. Sahifa yangilanganda (F5) profilni shu bilan oling; `access_level` bo'yicha menyuni ko'rsating.

### 1.5 `POST auth/change-password/`

Admin **o'z** parolini almashtiradi.

```json
{ "old_password": "S3cret-pass", "new_password": "N3w-strong-pass" }
```

Javob `200` — `auth/me/` obyekti, `must_change_password: false`. Tokenlar o'zgarmaydi, qayta login shart emas.

| Status | Javob | Qachon |
| --- | --- | --- |
| `400` | `{"old_password": ["Incorrect password"]}` | eski parol noto'g'ri |
| `400` | `{"new_password": ["The new password must differ from the old one"]}` | yangi = eski |
| `400` | `{"new_password": ["..."]}` | parol talablari: kamida 8 belgi, faqat raqamlardan iborat emas, juda oddiy (`12345678`, `password`) emas, login / ismga o'xshamasin |

### 1.6 Frontda

1. Login → `access`, `refresh`, `admin` ni saqlang. `must_change_password: true` bo'lsa parol almashtirish oynasini oching.
2. Har so'rovga `Authorization: Bearer <access>`.
3. Biror so'rov `401` qaytarsa → bir marta `auth/token/refresh/`, yangi `access` + `refresh` ni saqlab so'rovni qaytaring. Refresh ham `401` → login sahifasiga.
4. Bir vaqtda bir nechta so'rov `401` olsa, refresh'ni **bitta** qiling (qolganlari uning natijasini kutsin).
5. Chiqish (logout) — tokenlarni frontda o'chirish yetarli, server endpointi yo'q.

---

## 2. Mahsulotlar ro'yxati — `GET products/`

### 2.1 Paginatsiya

`?page=1&page_size=20` (default 20, max 100).

```json
{
  "count": 8214,
  "next": "https://api.buildex.uz/api/v1/admin/products/?page=2",
  "previous": null,
  "next_page": 2,
  "previous_page": null,
  "results": [ ... ]
}
```

### 2.2 Ro'yxat qatori

```json
{
  "id": 11532,
  "name": "Перфоратор Bosch GBH 2-26",
  "images": [
    { "id": 15, "image": "https://api.buildex.uz/media/product_image/a.png", "alt_uz": null, "alt_ru": null, "position": 0, "created_at": "2026-11-12T11:02:10" }
  ],
  "product_code": "00-00012345",
  "articul_code": "GBH 2-26",
  "barcode": "4059952512345",
  "brand": { "id": 7, "name": "Bosch" },
  "product_model": { "id": 3, "name": "GBH" },
  "badges": [ { "id": 2, "name": "Yangi", "color": "#22C55E", "kind": "manual" } ],
  "product_item_category": {
    "id": 427,
    "name": "Перфораторы",
    "product_sub_category": {
      "id": 147,
      "name": "Электроинструмент",
      "product_category": { "id": 7, "name": "Инструменты" }
    }
  },
  "price": 1500000.0,
  "discount_price": 1350000.0,
  "discount": 10,
  "unit": "pcs",
  "quantity": 5,
  "rating": 4.5,
  "comments_quantity": 2,
  "is_active": true,
  "erp_active": true,
  "publish_status": "published",
  "purchasable": false,
  "on_order": false,
  "created_at": "2026-11-12T10:51:25.358869",
  "updated_at": "2026-11-20T08:00:11.120000"
}
```

`images[0]` — asosiy rasm (jadvaldagi kichik rasm). Ro'yxatda `description`, `attribute_values`, bog'liq mahsulotlar **yo'q** — ular detail'da.

### 2.3 Filtrlar

| Parametr | Misol | Izoh |
| --- | --- | --- |
| `category` | `?category=7` | 1-daraja kategoriya |
| `sub_category` | `?sub_category=147` | 2-daraja |
| `product_item_category` | `?product_item_category=427` | 3-daraja (predmet kategoriya) |
| `brand` | `?brand=7` | |
| `product_model` | `?product_model=3` | |
| `badge` | `?badge=2` | shu tegli mahsulotlar |
| `is_active` | `?is_active=true` | "Holat": Faol (`true`) / Qoralama (`false`) |
| `erp_active` | `?erp_active=true` | 1C dagi faollik |
| `publish_status` | `?publish_status=review` | `draft` / `review` / `published` |
| `purchasable` | `?purchasable=true` | |
| `on_order` | `?on_order=true` | "Под заказ" |
| `unit` | `?unit=pcs` | `kg` `l` `sm` `pcs` `m` `g` `pkg` `set` |
| `min_price`, `max_price` | `?min_price=10000&max_price=500000` | `price` bo'yicha (so'm) |
| `in_stock` | `?in_stock=true` | `true` = `quantity > 0`, `false` = qoldiq yo'q |
| `has_discount` | `?has_discount=true` | `discount_price` bor / yo'q |
| `from_created`, `to_created` | `?from_created=2026-11-01&to_created=2026-11-24` | yaratilgan sana (`YYYY-MM-DD`, ikkala chegara kiradi) |

Bir nechta filtr birga ishlaydi (AND).

### 2.4 Qidiruv

`?search=bosch` — `name_ru`, `name_uz`, `product_code` (1C kodi), `articul_code`, `barcode` bo'yicha (qism ham topiladi, registr farq qilmaydi).

### 2.5 Tartib

`?ordering=<maydon>`, kamayish bo'yicha `-` bilan (`?ordering=-price`).

| Maydon | |
| --- | --- |
| `id` | |
| `name` | nom |
| `price` | narx |
| `quantity` | qoldiq |
| `rating` | reyting |
| `created_at` | **default: `-created_at`** (yangilari birinchi) |
| `updated_at` | |

### 2.6 `GET products/stats/`

Ro'yxat bilan **bir xil filtr / qidiruv** qabul qiladi, paginatsiyasiz:

```json
{ "total": 8214, "active": 7930, "inactive": 284, "out_of_stock": 512, "discounted": 140 }
```

| Maydon | |
| --- | --- |
| `total` | jami |
| `active` / `inactive` | `is_active` true / false |
| `out_of_stock` | `quantity ≤ 0` |
| `discounted` | `discount_price` bor |

---

## 3. Mahsulot detail — `GET products/{id}/`

Yaratish (`POST`) va tahrirlash (`PATCH`) javobi ham aynan shu obyekt.

```json
{
  "id": 11532,
  "name": "Перфоратор Bosch GBH 2-26",
  "name_uz": "Bosch GBH 2-26 perforatori",
  "name_ru": "Перфоратор Bosch GBH 2-26",
  "short_description_uz": "Uy va qurilish uchun perforator",
  "short_description_ru": "Перфоратор для дома и стройки",
  "description_uz": "<p>...</p>",
  "description_ru": "<p>...</p>",
  "slug_uz": "bosch-gbh-2-26-perforatori-11532",
  "slug_ru": "perforator-bosch-gbh-2-26-11532",
  "meta_title_uz": null,
  "meta_title_ru": "Перфоратор Bosch GBH 2-26 — купить в Ташкенте",
  "meta_description_uz": null,
  "meta_description_ru": null,
  "brand": { "id": 7, "name": "Bosch" },
  "product_model": { "id": 3, "name": "GBH" },
  "badges": [ { "id": 2, "name": "Yangi", "color": "#22C55E", "kind": "manual" } ],
  "product_item_category": {
    "id": 427,
    "name": "Перфораторы",
    "product_sub_category": {
      "id": 147,
      "name": "Электроинструмент",
      "product_category": { "id": 7, "name": "Инструменты" }
    }
  },
  "price": 1500000.0,
  "discount_price": 1350000.0,
  "discount": 10,
  "unit": "pcs",
  "quantity": 5,
  "is_active": true,
  "erp_active": true,
  "publish_status": "published",
  "purchasable": false,
  "on_order": false,
  "product_code": "00-00012345",
  "articul_code": "GBH 2-26",
  "barcode": "4059952512345",
  "weight": "2.900",
  "length": "0.400",
  "width": "0.100",
  "height": "0.250",
  "rating": 4.5,
  "comments_quantity": 2,
  "questions_quantity": 1,
  "characteristics": [
    { "id": 145993, "name_uz": "Размер шва", "name_ru": "Размер шва", "value_uz": "800", "value_ru": "800", "unit_uz": "мм", "unit_ru": "мм" }
  ],
  "attribute_values": [
    {
      "id": 145993,
      "attribute": { "id": 3123, "name": "Размер шва", "value_type": "number", "unit": "мм" },
      "value_uz": "800",
      "value_ru": "800"
    }
  ],
  "images": [
    { "id": 15, "image": "https://api.buildex.uz/media/product_image/a.png", "alt_uz": "Bosch perforatori", "alt_ru": "Перфоратор Bosch", "position": 0, "created_at": "2026-11-12T11:02:10" }
  ],
  "related_products": [
    { "id": 101, "name": "Бур SDS-plus 8x160", "image": "https://api.buildex.uz/media/product_image/bur.png", "product_code": "00-00012346", "articul_code": "2608680268", "price": 25000.0, "discount_price": null, "quantity": 40, "is_active": true }
  ],
  "alternative_products": [],
  "cross_sell_products": [],
  "last_moderation": {
    "id": 51,
    "status": "approved",
    "submitted_at": "2026-11-12T11:10:00",
    "reviewed_by": "Kamola Ergasheva",
    "reviewed_at": "2026-11-12T12:00:00",
    "reason": null
  },
  "created_at": "2026-11-12T10:51:25.358869",
  "updated_at": "2026-11-20T08:00:11.120000"
}
```

- `name` — so'rov tilidagi nom (faqat o'qiladi); formada `name_uz` / `name_ru` ishlatiladi.
- `characteristics` — **eskirgan**, faqat o'qiladi (`attribute_values` ning eski ko'rinishi). Yangi formada `attribute_values`.
- `last_moderation` — oxirgi moderatsiyaga yuborish (`status` `pending` / `approved` / `rejected`, `reason` — rad etilgan bo'lsa), hech qachon yuborilmagan bo'lsa `null`.
- `404` — mahsulot topilmadi.

---

## 4. Formadagi tanlov ro'yxatlari qayerdan olinadi

Hamma ro'yxatlar paginatsiyali (`?page=&page_size=`, max 100), qidiruv `?search=`.

| Forma maydoni | Endpoint | Yuboriladigan qiymat |
| --- | --- | --- |
| Brend | `GET brands/?search=` | `brand: <id>` |
| Kategoriya (1-daraja) | `GET categories/` | — (keyingi darajani topish uchun) |
| Subkategoriya (2-daraja) | `GET sub-categories/?product_category=<id>` | — |
| Predmet kategoriya (3-daraja) | `GET item-categories/?product_sub_category=<id>` | `product_item_category: <id>` |
| Model | `GET product-models/?brand=<brand_id>&is_active=true` | `product_model: <id>` |
| Teglar | `GET product-badges/?kind=manual&is_active=true` | `badges: [<id>, ...]` |
| Xarakteristikalar | `GET item-categories/<id>/attributes/` (predmet kategoriya tanlangach) | `attribute_values: [...]` |
| Bog'liq / muqobil / cross-sell | `GET products/?search=` | `related_products` / `alternative_products` / `cross_sell_products: [<id>, ...]` |

Mahsulot faqat **3-darajaga** (predmet kategoriya) biriktiriladi.

### 4.1 Xarakteristikalar (atributlar) formasi

`GET item-categories/{id}/attributes/`:

```json
{
  "id": 427,
  "attributes": [
    {
      "id": 3123, "name": "Размер шва", "value_type": "number", "unit": "мм", "options": [],
      "is_filterable": true, "is_active": true, "is_quick_filter": false, "max_quick_filters": null, "is_required": true
    },
    {
      "id": 51, "name": "Цвет", "value_type": "list", "unit": null,
      "options": [
        { "id": 7, "value_uz": "Oq", "value_ru": "Белый" },
        { "id": 8, "value_uz": "Qora", "value_ru": "Чёрный" }
      ],
      "is_filterable": true, "is_active": true, "is_quick_filter": true, "max_quick_filters": 6, "is_required": false
    }
  ]
}
```

Ro'yxat tartibi = formadagi tartib. `value_type` bo'yicha input va `attribute_values` ga yozilishi:

| `value_type` | Input | `value_uz` / `value_ru` |
| --- | --- | --- |
| `number` | son (yonida `unit`) | ikkalasi bir xil son matni: `"2.5"` (kasr nuqta bilan) |
| `boolean` | ha / yo'q | ikkalasi bir xil: `"true"` yoki `"false"` |
| `list` | `options` dan tanlash | tanlangan variantning `value_uz` va `value_ru` si aynan |
| `text` | erkin matn | ikki tilda alohida |

`is_required: true` — bu atributsiz mahsulot moderatsiyadan o'tmaydi (saqlashga to'sqinlik qilmaydi). Qiymat kiritilmagan atribut `attribute_values` ga qo'shilmaydi (bo'sh qiymat yubormang).

---

## 5. Yaratish — `POST products/`

### 5.1 Tartib: avval mahsulot, keyin rasmlar

`POST products/` rasm **qabul qilmaydi** (body JSON). Rasm mahsulot `id`si bilan yuklanadi. "Saqlash" bosilganda:

1. **`POST products/`** — JSON. Javob `201`, ichida `id`.
2. **`POST products/{id}/images/`** — har rasm alohida, **ketma-ket** (parallel emas): yangi rasm oxiriga qo'shiladi, demak yuklash tartibi = rasmlar tartibi, **birinchi yuklangan — asosiy rasm**.
3. **`POST products/{id}/images/reorder/`** — faqat tartib o'zgargan / boshqa rasm asosiy qilingan bo'lsa.
4. **`PATCH products/{id}/`** `{"is_active": true}` — saytda / ilovada ko'rinishi uchun (yoki moderatsiyaga: `{"publish_status": "review"}`).

**Xato bo'lsa:** 1-qadam o'tdi, rasmda xato → mahsulot bazada bor. Formani qayta "yaratish" rejimida yubormang (ikkinchi nusxa paydo bo'ladi) — olingan `id` bilan tahrirlash rejimiga o'ting va faqat yuklanmagan rasmlarni qayta yuboring.

### 5.2 So'rov

Minimal:

```json
{ "name_ru": "Перфоратор Bosch GBH 2-26", "description_ru": "<p>Описание</p>" }
```

To'liq:

```json
{
  "name_uz": "Bosch GBH 2-26 perforatori",
  "name_ru": "Перфоратор Bosch GBH 2-26",
  "short_description_uz": "Uy va qurilish uchun perforator",
  "short_description_ru": "Перфоратор для дома и стройки",
  "description_uz": "<p>...</p>",
  "description_ru": "<p>...</p>",
  "brand": 7,
  "product_model": 3,
  "product_item_category": 427,
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
    { "attribute": 3123, "value_uz": "800", "value_ru": "800" },
    { "attribute": 51, "value_uz": "Oq", "value_ru": "Белый" }
  ],
  "related_products": [101, 102],
  "alternative_products": [],
  "cross_sell_products": [{ "id": 300 }],
  "meta_title_ru": "Перфоратор Bosch GBH 2-26 — купить в Ташкенте",
  "meta_description_ru": "...",
  "publish_status": "draft",
  "purchasable": false,
  "on_order": false
}
```

Bog'lanishlar (`brand`, `product_model`, `product_item_category`, `badges`, `attribute_values[].attribute`, bog'liq mahsulotlar) **bare id** (`7`) yoki **`{"id": 7}`** ko'rinishida yuboriladi; javobda obyekt bo'lib qaytadi.

### 5.3 Maydonlar

`*` = majburiy (yaratishda). Yuborilmagan maydon default oladi.

| Maydon | Turi | Default | Izoh |
| --- | --- | --- | --- |
| `name_ru` * | string, ≤ 500 | — | asosiy til |
| `description_ru` * | string (HTML) | — | |
| `name_uz` | string ≤ 500, null | null | bo'sh bo'lsa uz tilida ru nomi ko'rinadi |
| `short_description_uz`, `short_description_ru` | string, null | null | kartochkadagi qisqa matn |
| `description_uz` | string (HTML), null | null | |
| `brand` | id, null | null | |
| `product_model` | id, null | null | shu `brand` ning modeli bo'lishi shart |
| `product_item_category` | id, null | null | 3-daraja; `attribute_values` uchun kerak |
| `badges` | id ro'yxati | `[]` | faqat qo'lda (`kind: manual`) teglar; auto teglar yuborilsa e'tiborsiz (o'z qoidasi bilan biriktiriladi) |
| `price` | number ≥ 0 | `0` | so'm; server 100 so'mgacha **tepaga** yaxlitlaydi (12 340 → 12 400), javobda yaxlitlangani |
| `discount_price` | number ≥ 0, null | null | chegirmadagi narx (savatda shu olinadi); `price` dan katta bo'lmasin; null = chegirma yo'q; 100 gacha tepaga yaxlitlanadi |
| `discount` | int 0–100, null | null | chegirma foizi (ko'rsatish uchun) |
| `unit` | `kg` `l` `sm` `pcs` `m` `g` `pkg` `set` | `pcs` | o'lchov birligi |
| `quantity` | int ≥ 0 | `0` | qoldiq |
| `articul_code` | string ≤ 100, null | null | artikul |
| `barcode` | string ≤ 100, null | null | shtrix-kod |
| `product_code` | string ≤ 100, null | null | **1C kodi**, unikal — yubormang (pastga qarang) |
| `weight` | decimal string, null | null | kg, 3 xonagacha kasr |
| `length`, `width`, `height` | decimal string, null | null | metr, 3 xonagacha kasr |
| `attribute_values` | ro'yxat | `[]` | `[{"attribute": id, "value_uz", "value_ru"}]`, 4.1 qoidalari; atribut `product_item_category` ga biriktirilgan va takrorlanmagan bo'lishi shart |
| `related_products` | id ro'yxati, ≤ 20 | `[]` | "birga xarid qilinadi" |
| `alternative_products` | id ro'yxati, ≤ 20 | `[]` | "o'rniga olish mumkin" |
| `cross_sell_products` | id ro'yxati, ≤ 20 | `[]` | savatda taklif qilinadi |
| `is_active` | bool | **`false`** | saytda / ilovada ko'rinishi ("Holat": Faol / Qoralama) |
| `erp_active` | bool | `false` | 1C dagi faollik (faqat ko'rsatish) |
| `publish_status` | `draft` / `review` / `published` | `draft` | `review` → moderatsiya navbatiga tushadi |
| `purchasable` | bool | `false` | "Sotib olish mumkin" belgisi |
| `on_order` | bool | `false` | "Под заказ" belgisi |
| `slug_uz`, `slug_ru` | string, null | nomdan avtomatik | URL qismi: `<nom-lotincha>-<id>` (`perforator-bosch-gbh-2-26-11532`); yuborilmasa avtomatik (bo'sh `""` yubormang); qo'lda kiritilsa unikal bo'lsin |
| `meta_title_uz`, `meta_title_ru`, `meta_description_uz`, `meta_description_ru` | string, null | null | SEO; bo'sh qolsa sayt o'zi to'ldiradi |

Faqat o'qiladi (yuborilsa e'tiborsiz): `id`, `name`, `images`, `characteristics`, `rating`, `comments_quantity`, `questions_quantity`, `last_moderation`, `created_at`, `updated_at`.

Bog'liq mahsulot ro'yxatlarida ro'yxat tartibi = saytda ko'rinish tartibi. Mahsulot o'zini o'ziga bog'lay olmaydi.

### 5.4 Muhim

- **Yangi mahsulot yashirin** (`is_active: false`), agar `is_active` yuborilmasa. Rasmlardan keyin `PATCH {"is_active": true}`.
- **`product_code` yubormang.** Paneldan yaratilgan mahsulot 1C bilan bog'lanmaydi: 1C keyinchalik shu tovarni o'z kodi bilan yuborsa **ikkinchi alohida kartochka** paydo bo'ladi. Kodni faqat 1C dagi kod aniq ma'lum bo'lsa kiriting.
- Moderatsiyadan o'tish uchun: nom uz / ru, tavsif uz / ru, kamida 1 rasm, predmet kategoriya, brend va majburiy (`is_required`) atributlar to'ldirilgan bo'lishi kerak — odatda `draft` bilan yaratib, rasmlardan keyin `review` ga o'tkaziladi.

Javob `201` — 3-bo'limdagi detail obyekti (`images: []`).

---

## 6. Tahrirlash — `PATCH products/{id}/`

Body — 5.3 dagi maydonlarning **istalgan qismi**, faqat yuborilganlari o'zgaradi. Javob `200` — detail obyekti.

```json
{ "price": 1450000, "discount_price": null, "is_active": true }
```

Qoidalar:

| Maydon | Yuborilsa | Yuborilmasa |
| --- | --- | --- |
| `attribute_values` | **hammasi almashtiriladi** (ro'yxatda yo'q qiymatlar o'chadi; `[]` = hammasini o'chirish) | o'zgarmaydi |
| `badges` | qo'lda teglar almashtiriladi; auto teglar joyida qoladi | o'zgarmaydi |
| `related_products` / `alternative_products` / `cross_sell_products` | shu turdagi bog'lanishlar almashtiriladi (tartib = ro'yxat tartibi) | o'zgarmaydi |
| `product_item_category` | o'zgarsa va `attribute_values` yuborilmasa → yangi kategoriyada yo'q atributlarning qiymatlari **o'chadi** | — |
| `brand` | o'zgarsa va `product_model` yuborilmasa → eski brendning modeli **olib tashlanadi** (`null`) | — |
| `name_uz` / `name_ru` | nom o'zgarsa slug ham yangi nomga moslashadi (qo'lda yozilgan slug saqlanadi) | — |
| `publish_status` | `review` → moderatsiya navbatiga; `published` → qo'lda tasdiqlangan (tekshiruvsiz); `draft` → navbatdan chiqadi | — |

- `PUT` ham bor, lekin u `name_ru` / `description_ru` ni majburiy qiladi — formada `PATCH` ishlating.
- Rasmlar `PATCH` bilan o'zgarmaydi — 8-bo'lim.
- **1C** kodli (`product_code` bor) mahsulotni qayta yuborsa, o'zi yuboradigan maydonlarni (nom, narx, qoldiq, `is_active`, ...) qaytadan yozadi — bunday mahsulotda narx / qoldiqni paneldan o'zgartirish keyingi 1C yuborishigacha amal qiladi. SEO, rasmlar, atributlar, bog'lanishlarga 1C tegmaydi.

---

## 7. O'chirish — `DELETE products/{id}/`

- `204` — o'chirildi (rasmlar, atribut qiymatlari, bog'lanishlar bilan birga).
- `400 {"detail": "Product is used in orders, deactivate it instead (is_active=false)."}` — mahsulot biror buyurtmada bor; o'chirib bo'lmaydi, o'rniga `PATCH {"is_active": false}`.
- `404` — topilmadi.

O'chirilgan mahsulot sahifasi saytda 410 bo'ladi (muqobil mahsulot / kategoriyaga yo'naltiriladi) — bu sayt tomonida, panelga ta'siri yo'q.

---

## 8. Rasmlar

Rasmlar `images` da **tartib bo'yicha** keladi. **Birinchi rasm — asosiy** (`is_main` maydoni yo'q); sayt va ilovada ham shu tartib.

| Maydon | Izoh |
| --- | --- |
| `image` * | fayl (yuklashda), javobda to'liq URL |
| `alt_uz`, `alt_ru` | alt matni (SEO); bo'sh bo'lsa sayt mahsulot nomini qo'yadi |
| `position` | faqat o'qiladi (0 dan); o'zgartirish — `reorder/` |

### 8.1 Yuklash — `POST products/{id}/images/`

`multipart/form-data`, bitta so'rovda **bitta** rasm: `image` *, `alt_uz`, `alt_ru`. Yangi rasm **oxiriga** qo'shiladi. Javob `201` — rasm obyekti.

```js
const form = new FormData();
form.append("image", file);
form.append("alt_ru", "Перфоратор Bosch");
await fetch(`${host}/api/v1/admin/products/${id}/images/`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },  // Content-Type ni qo'lda qo'ymang
  body: form,
});
```

Xatolar: `400 {"image": [...]}` — fayl yo'q / rasm emas; `404` — mahsulot topilmadi.

### 8.2 Tartib / asosiy rasm — `POST products/{id}/images/reorder/`

```json
{ "ids": [12, 9, 15] }
```

- `ids` — rasm id'lari yangi tartibda; birinchisi asosiy bo'ladi. Asosiy rasmni almashtirish = uni ro'yxat **boshiga** qo'yish.
- Yuborilmagan rasmlar yuborilganlardan **keyin**, o'z tartibida qoladi.

Javob `200` — yakuniy to'liq tartib `{"ids": [12, 9, 15]}`.

Xatolar: `400 {"ids": ["Not found: [17]"]}` — shu mahsulotning rasmi emas; `400 {"ids": ["Duplicate ids."]}`; `400` — `ids` bo'sh; `404` — mahsulot topilmadi.

### 8.3 O'chirish — `DELETE products/{id}/images/{image_id}/`

`204`, fayl ham o'chadi. Asosiy rasm o'chirilsa keyingisi asosiy bo'ladi. `404` — rasm shu mahsulotniki emas.

---

## 9. Xatolar (mahsulot)

| Status | Javob | Qachon |
| --- | --- | --- |
| `400` | `{"name_ru": ["Обязательное поле."], "description_ru": ["Обязательное поле."]}` | yaratishda majburiy maydon yo'q / bo'sh |
| `400` | `{"discount_price": ["Must not be greater than price."]}` | chegirma narxi narxdan katta |
| `400` | `{"product_model": ["Model belongs to another brand."]}` | model boshqa brendniki |
| `400` | `{"attribute_values": ["Attributes [51] are not attached to the product's item category."]}` | atribut predmet kategoriyaga biriktirilmagan (yoki kategoriya tanlanmagan) |
| `400` | `{"attribute_values": ["Attributes must be unique."]}` | bir atribut ikki marta |
| `400` | `{"attribute_values": [{"value_ru": ["Must be one of the attribute's options."]}]}` | `list` qiymati variantlarda yo'q |
| `400` | `{"attribute_values": [{"value_ru": ["A number is required, e.g. \"2.5\"."]}]}` | `number` ga son emas |
| `400` | `{"attribute_values": [{"value_ru": ["\"true\" or \"false\" is required."]}]}` | `boolean` ga boshqa qiymat |
| `400` | `{"attribute_values": [{"value_uz": ["Must be the same as value_ru for the number type."]}]}` | `number` / `boolean` da uz ≠ ru |
| `400` | `{"related_products": ["Products must be unique."]}` | ro'yxatda takror (har uch ro'yxat uchun) |
| `400` | `{"related_products": ["A product can't be linked to itself."]}` | mahsulot o'ziga bog'langan |
| `400` | `{"related_products": [...]}` | 20 tadan ko'p yoki mavjud bo'lmagan id |
| `400` | `{"product_code": [...]}` / `{"slug_ru": [...]}` | kod yoki slug boshqa mahsulotda band |
| `400` | `{"brand": [...]}` va h.k. | mavjud bo'lmagan id |
| `400` | `{"detail": "Product is used in orders, ..."}` | buyurtmadagi mahsulotni o'chirish |
| `401` | `{"detail": "..."}` | token yo'q / muddati o'tgan → 1.6 |
| `403` | `{"detail": "..."}` | admin emas |
| `404` | `{"detail": "..."}` | mahsulot / rasm topilmadi |

`400` javobidagi kalitlar maydon nomlari bilan bir xil — xatoni shu maydon ostida ko'rsating.

---

## 10. Frontda qilinadigan ishlar

1. Login → tokenlarni saqlash, `401` da bitta refresh, refresh ham `401` → login sahifasi (1.6).
2. Mahsulotlar jadvali: `GET products/` + filtrlar / qidiruv / tartib; ustidagi kartochkalar — `GET products/stats/` xuddi shu parametrlar bilan.
3. "Saqlash" (yangi): `POST products/` → `id` → rasmlarni ketma-ket yuklash → kerak bo'lsa `reorder/` → `PATCH {"is_active": true}`.
4. `POST` muvaffaqiyatli bo'lgach forma tahrirlash rejimiga o'tsin (keyingi saqlashlar `PATCH products/{id}/`).
5. Tahrirlashda faqat o'zgargan maydonlarni yuboring; `attribute_values` / `badges` / bog'liq ro'yxatlarni yuborsangiz — to'liq ro'yxatni yuboring (almashtiriladi).
6. Predmet kategoriya tanlanganda `GET item-categories/{id}/attributes/` dan xarakteristika maydonlarini chizing; kategoriya o'zgarsa eski qiymatlarni tozalang.
7. Model ro'yxatini tanlangan brend bo'yicha yuklang; brend o'zgarsa modelni tozalang.
8. `product_code` ni yaratish formasida ko'rsatmang (yoki faqat o'qiladigan qiling).
9. O'chirishda `400` (buyurtmada bor) bo'lsa — "Qoralamaga o'tkazish" (`is_active: false`) taklif qiling.
