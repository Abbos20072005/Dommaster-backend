# Mahsulot qo'shish — admin panel uchun

Mahsulot qo'shish formasi uchun kerak bo'ladigan hamma narsa shu faylda: mahsulot yaratish, rasmlarni yuklash va tartiblash, formadagi tanlov ro'yxatlari (brend, kategoriya, model, teg, atributlar, bog'liq mahsulotlar) qayerdan olinishi, javob obyekti va xatolar.

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`, admin bo'lmasa → `403`).

Swagger: `/swagger/admin/` → **products**.

| Endpoint | Nima uchun |
| --- | --- |
| `POST products/` | mahsulot yaratish (JSON, **rasmsiz**) |
| `POST products/{id}/images/` | bitta rasm yuklash (multipart) |
| `POST products/{id}/images/reorder/` | rasmlar tartibi / asosiy rasmni almashtirish |
| `DELETE products/{id}/images/{image_id}/` | rasmni o'chirish |
| `GET products/{id}/` | mahsulot detail (yaratilgandan keyin formani ochish) |
| `PATCH products/{id}/` | tahrirlash (yaratishdagi maydonlarning o'zi, faqat yuborilganlari o'zgaradi) |

---

## 1. Tartib: avval mahsulot, keyin rasmlar

`POST products/` rasm **qabul qilmaydi**: body JSON, `images` maydoni faqat o'qiladi. Rasm mahsulotning `id`si bilan yuklanadi, `id` esa mahsulot yaratilgandan keyingina paydo bo'ladi. Shuning uchun formada "Saqlash" bosilganda:

1. **`POST products/`** — JSON body bilan mahsulot yaratiladi. Javob `201`, ichida `id`.
2. **`POST products/{id}/images/`** — har bir rasm alohida so'rov bilan (multipart, maydon `image`). Rasmlarni **ketma-ket** yuboring (bittasi tugagach keyingisi), parallel emas: har yangi rasm ro'yxat oxiriga qo'shiladi, shuning uchun yuklash tartibi = rasmlar tartibi, **birinchi yuklangan rasm asosiy rasm** bo'ladi.
3. **`POST products/{id}/images/reorder/`** — faqat foydalanuvchi formada tartibni o'zgartirgan bo'lsa yoki boshqa rasmni asosiy qilmoqchi bo'lsa.
4. **`PATCH products/{id}/`** `{"is_active": true}` — mahsulot saytda / ilovada ko'rinishi uchun (yoki moderatsiyaga yuborish uchun `{"publish_status": "review"}`). Yangi mahsulot **yashirin** yaratiladi, pastga qarang.

**Xato bo'lsa:** 1-qadam o'tdi, lekin rasm yuklashda xato chiqdi → mahsulot bazada allaqachon bor. Formani yana "yaratish" rejimida yubormang — ikkinchi nusxa paydo bo'ladi. Formani olingan `id` bilan tahrirlash rejimiga o'tkazing va faqat yuklanmagan rasmlarni qayta yuboring.

---

## 2. Formadagi tanlov ro'yxatlari qayerdan olinadi

Hamma ro'yxatlar paginatsiyali (`?page=&page_size=`, default 20, max 100; javob `count, next, previous, next_page, previous_page, results`), qidiruv `?search=`.

| Forma maydoni | Endpoint | Yuboriladigan qiymat |
| --- | --- | --- |
| Brend | `GET brands/?search=` | `brand: <id>` |
| Kategoriya (1-daraja) | `GET categories/` | — (faqat keyingi darajani tanlash uchun) |
| Subkategoriya (2-daraja) | `GET sub-categories/?product_category=<id>` | — |
| Predmet kategoriya (3-daraja) | `GET item-categories/?product_sub_category=<id>` | `product_item_category: <id>` |
| Model | `GET product-models/?brand=<brand_id>&is_active=true` | `product_model: <id>` |
| Teglar | `GET product-badges/?kind=manual&is_active=true` | `badges: [<id>, ...]` |
| Xarakteristikalar | `GET item-categories/<id>/attributes/` (predmet kategoriya tanlangandan keyin) | `attribute_values: [...]` |
| Bog'liq / muqobil / cross-sell mahsulotlar | `GET products/?search=` | `related_products` / `alternative_products` / `cross_sell_products: [<id>, ...]` |

Mahsulot faqat **3-darajaga** (predmet kategoriya) biriktiriladi; 1- va 2-daraja shu tanlovni topish uchun.

### Xarakteristikalar (atributlar) formasi

`GET item-categories/{id}/attributes/` javobi:

```json
{
  "id": 427,
  "attributes": [
    {
      "id": 3123,
      "name": "Размер шва",
      "value_type": "number",
      "unit": "мм",
      "options": [],
      "is_filterable": true,
      "is_active": true,
      "is_quick_filter": false,
      "max_quick_filters": null,
      "is_required": true
    },
    {
      "id": 51,
      "name": "Цвет",
      "value_type": "list",
      "unit": null,
      "options": [
        { "id": 7, "value_uz": "Oq", "value_ru": "Белый" },
        { "id": 8, "value_uz": "Qora", "value_ru": "Чёрный" }
      ],
      "is_filterable": true,
      "is_active": true,
      "is_quick_filter": true,
      "max_quick_filters": 6,
      "is_required": false
    }
  ]
}
```

Ro'yxat tartibi = formadagi tartib. Har bir atribut uchun `value_type` bo'yicha input chiziladi va `attribute_values` ga quyidagicha yoziladi:

| `value_type` | Input | `value_uz` / `value_ru` |
| --- | --- | --- |
| `number` | son (yonida `unit`) | ikkalasi bir xil son matni: `"2.5"` (kasr nuqta bilan) |
| `boolean` | ha / yo'q | ikkalasi bir xil: `"true"` yoki `"false"` |
| `list` | `options` dan tanlash | tanlangan variantning `value_uz` va `value_ru` si aynan |
| `text` | erkin matn | ikki tilda alohida matn |

`is_required: true` — bu atributsiz mahsulot moderatsiyadan o'tmaydi (yaratishga to'sqinlik qilmaydi). Qiymat kiritilmagan atribut `attribute_values` ga umuman qo'shilmaydi (bo'sh qiymat yuborilmaydi).

---

## 3. `POST products/` — mahsulot yaratish

Minimal so'rov:

```json
{
  "name_ru": "Перфоратор Bosch GBH 2-26",
  "description_ru": "<p>Описание</p>"
}
```

To'liq so'rov:

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

Bog'lanishlar (`brand`, `product_model`, `product_item_category`, `badges`, `attribute_values[].attribute`, bog'liq mahsulotlar) **bare id** (`7`) yoki **`{"id": 7}`** ko'rinishida yuboriladi — ikkalasi ham qabul qilinadi. Javobda esa ular obyekt bo'lib qaytadi.

### Maydonlar

`*` = majburiy. Yuborilmagan maydon default qiymatini oladi.

| Maydon | Turi | Default | Izoh |
| --- | --- | --- | --- |
| `name_ru` * | string, ≤ 500 | — | asosiy til (ru) |
| `description_ru` * | string (HTML) | — | |
| `name_uz` | string, ≤ 500, null | null | bo'sh bo'lsa uz tilida ru nomi ko'rinadi |
| `short_description_uz`, `short_description_ru` | string, null | null | ro'yxat / kartochkadagi qisqa matn |
| `description_uz` | string (HTML), null | null | |
| `brand` | id, null | null | |
| `product_model` | id, null | null | shu `brand` ning modeli bo'lishi shart |
| `product_item_category` | id, null | null | predmet kategoriya (3-daraja); `attribute_values` uchun kerak |
| `badges` | id ro'yxati | `[]` | faqat qo'lda (`kind: manual`) teglar; auto teglar yuborilsa e'tiborsiz qoladi (ular o'z qoidasi bilan biriktiriladi) |
| `price` | number ≥ 0 | `0` | so'm; server 100 so'mgacha **tepaga** yaxlitlab saqlaydi (12 340 → 12 400), javobda yaxlitlangani qaytadi |
| `discount_price` | number ≥ 0, null | null | chegirmadagi narx; `price` dan katta bo'lmasin; null = chegirma yo'q; `price` kabi 100 so'mgacha tepaga yaxlitlanadi |
| `discount` | int 0–100, null | null | chegirma foizi (ko'rsatish uchun) |
| `unit` | `kg` `l` `sm` `pcs` `m` `g` `pkg` `set` | `pcs` | o'lchov birligi |
| `quantity` | int ≥ 0 | `0` | qoldiq |
| `articul_code` | string ≤ 100, null | null | artikul |
| `barcode` | string ≤ 100, null | null | shtrix-kod |
| `product_code` | string ≤ 100, null | null | **1C kodi** — yubormang (pastga qarang); unikal |
| `weight` | decimal string, null | null | kg, 3 xonagacha kasr |
| `length`, `width`, `height` | decimal string, null | null | metr, 3 xonagacha kasr |
| `attribute_values` | ro'yxat | `[]` | `[{"attribute": id, "value_uz", "value_ru"}]`, 2-bo'limdagi qoidalar bo'yicha; atribut `product_item_category` ga biriktirilgan bo'lishi va takrorlanmasligi shart |
| `related_products` | id ro'yxati, ≤ 20 | `[]` | "birga xarid qilinadi" (mahsulot sahifasida) |
| `alternative_products` | id ro'yxati, ≤ 20 | `[]` | "o'rniga olish mumkin" (mahsulot sahifasida) |
| `cross_sell_products` | id ro'yxati, ≤ 20 | `[]` | savatda taklif qilinadi |
| `is_active` | bool | **`false`** | saytda / ilovada ko'rinishi ("Holat": Faol / Qoralama) |
| `erp_active` | bool | `false` | 1C dagi faollik belgisi (faqat ko'rsatish uchun) |
| `publish_status` | `draft` / `review` / `published` | `draft` | `review` → moderatsiya navbatiga tushadi |
| `purchasable` | bool | `false` | "Sotib olish mumkin" belgisi |
| `on_order` | bool | `false` | "Под заказ" belgisi |
| `slug_uz`, `slug_ru` | string, null | nomdan avtomatik | URL qismi; yuborilmasa nomdan yasaladi (bo'sh `""` yubormang, maydonni umuman qo'shmang): `<nom-lotincha>-<id>`, masalan `perforator-bosch-gbh-2-26-11532`; qo'lda kiritilsa unikal bo'lishi kerak |
| `meta_title_uz`, `meta_title_ru`, `meta_description_uz`, `meta_description_ru` | string, null | null | SEO; bo'sh qolsa sayt o'zi to'ldiradi |

Faqat o'qiladigan (yuborilsa e'tiborsiz): `id`, `name` (so'rov tilidagi nom), `images`, `characteristics` (eski ko'rinish), `rating`, `comments_quantity`, `questions_quantity`, `last_moderation`, `created_at`, `updated_at`.

Bog'liq mahsulot ro'yxatlarida (`related_products`, ...) ro'yxat tartibi = saytda ko'rinish tartibi.

### Muhim

- **Yangi mahsulot yashirin yaratiladi** (`is_active: false`), agar `is_active` yuborilmasa. Rasmlar yuklangandan keyin `PATCH products/{id}/` `{"is_active": true}`. `is_active: true` ni darhol `POST` da ham yuborish mumkin, lekin unda mahsulot rasmsiz holda bir zum ko'rinib turadi.
- **`product_code` yubormang.** Paneldan yaratilgan mahsulot 1C bilan bog'lanmaydi: keyinchalik 1C shu tovarni o'z kodi bilan yuborsa, u **ikkinchi alohida kartochka** bo'lib qo'shiladi. Kodni faqat 1C dagi kod aniq ma'lum bo'lsa kiriting.
- Moderatsiya: `publish_status: "review"` bilan yaratilsa mahsulot "Moderatsiya" navbatiga tushadi. Tasdiqlash uchun nom uz / ru, tavsif uz / ru, kamida 1 rasm, predmet kategoriya, brend va majburiy (`is_required`) atributlar to'ldirilgan bo'lishi kerak — shuning uchun odatda `draft` bilan yaratib, rasmlardan keyin `review` ga o'tkaziladi.

### Javob

`201` — mahsulotning to'liq obyekti (`GET products/{id}/` bilan bir xil), `images: []`:

```json
{
  "id": 11532,
  "name": "Перфоратор Bosch GBH 2-26",
  "name_uz": "Bosch GBH 2-26 perforatori",
  "name_ru": "Перфоратор Bosch GBH 2-26",
  "short_description_uz": null,
  "short_description_ru": null,
  "description_uz": null,
  "description_ru": "<p>Описание</p>",
  "slug_uz": "bosch-gbh-2-26-perforatori-11532",
  "slug_ru": "perforator-bosch-gbh-2-26-11532",
  "meta_title_uz": null,
  "meta_title_ru": null,
  "meta_description_uz": null,
  "meta_description_ru": null,
  "brand": { "id": 7, "name": "Bosch" },
  "product_model": null,
  "badges": [],
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
  "discount_price": null,
  "discount": null,
  "unit": "pcs",
  "quantity": 5,
  "is_active": false,
  "erp_active": false,
  "publish_status": "draft",
  "purchasable": false,
  "on_order": false,
  "product_code": null,
  "articul_code": null,
  "barcode": null,
  "weight": null,
  "length": null,
  "width": null,
  "height": null,
  "rating": 0.0,
  "comments_quantity": 0,
  "questions_quantity": 0,
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
  "images": [],
  "related_products": [],
  "alternative_products": [],
  "cross_sell_products": [],
  "last_moderation": null,
  "created_at": "2026-11-12T10:51:25.358869",
  "updated_at": "2026-11-12T10:51:25.358869"
}
```

`characteristics` — eskirgan, faqat o'qiladi (`attribute_values` ning eski ko'rinishi); yangi formada `attribute_values` ishlatiladi.

Bog'liq mahsulotlar javobda shunday keladi:

```json
"related_products": [
  { "id": 101, "name": "Бур SDS-plus 8x160", "image": "https://.../media/product_image/bur.png", "product_code": "00-00012345", "articul_code": "2608680268", "price": 25000.0, "discount_price": null, "quantity": 40, "is_active": true }
]
```

### Xatolar

| Status | Javob | Qachon |
| --- | --- | --- |
| `400` | `{"name_ru": ["Обязательное поле."], "description_ru": ["Обязательное поле."]}` | majburiy maydon yo'q / bo'sh |
| `400` | `{"discount_price": ["Must not be greater than price."]}` | chegirma narxi narxdan katta |
| `400` | `{"product_model": ["Model belongs to another brand."]}` | model boshqa brendniki |
| `400` | `{"attribute_values": ["Attributes [51] are not attached to the product's item category."]}` | atribut tanlangan predmet kategoriyaga biriktirilmagan (yoki kategoriya tanlanmagan) |
| `400` | `{"attribute_values": ["Attributes must be unique."]}` | bir atribut ikki marta |
| `400` | `{"attribute_values": [{"value_ru": ["Must be one of the attribute's options."]}]}` | `list` qiymati variantlarda yo'q |
| `400` | `{"attribute_values": [{"value_ru": ["A number is required, e.g. \"2.5\"."]}]}` | `number` ga son emas |
| `400` | `{"attribute_values": [{"value_ru": ["\"true\" or \"false\" is required."]}]}` | `boolean` ga boshqa qiymat |
| `400` | `{"attribute_values": [{"value_uz": ["Must be the same as value_ru for the number type."]}]}` | `number` / `boolean` da uz ≠ ru |
| `400` | `{"related_products": ["Products must be unique."]}` | ro'yxatda takror (har uch ro'yxat uchun) |
| `400` | `{"related_products": [...]}` | 20 tadan ko'p yoki mavjud bo'lmagan id |
| `400` | `{"product_code": [...]}` / `{"slug_ru": [...]}` | kod yoki slug boshqa mahsulotda band |
| `400` | `{"brand": [...]}` va h.k. | mavjud bo'lmagan id |
| `401` / `403` | | token yo'q / admin emas |

---

## 4. Rasmlar

Rasmlar mahsulotning `images` maydonida (ro'yxat va detail) **tartib bo'yicha** keladi. **Birinchi rasm — asosiy rasm** (alohida `is_main` maydoni yo'q); sayt va ilovada ham shu tartib.

Rasm obyekti:

```json
{ "id": 15, "image": "https://api.buildex.uz/media/product_image/a.png", "alt_uz": "Bosch perforatori", "alt_ru": "Перфоратор Bosch", "position": 0, "created_at": "2026-11-12T11:02:10" }
```

| Maydon | Izoh |
| --- | --- |
| `image` * | rasm fayli (yuklashda), javobda to'liq URL |
| `alt_uz`, `alt_ru` | rasm alt matni (SEO); bo'sh bo'lsa sayt mahsulot nomini qo'yadi |
| `position` | faqat o'qiladi, tartib raqami (0 dan); o'zgartirish — `reorder/` orqali |

### 4.1 Yuklash — `POST products/{id}/images/`

`Content-Type: multipart/form-data`, bitta so'rovda **bitta** rasm:

| Form maydoni | |
| --- | --- |
| `image` * | fayl |
| `alt_uz` | matn, ixtiyoriy |
| `alt_ru` | matn, ixtiyoriy |

Yangi rasm har doim ro'yxat **oxiriga** qo'shiladi. Javob `201` — rasm obyekti.

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

Xatolar: `400 {"image": [...]}` — fayl yo'q yoki rasm emas; `404` — mahsulot topilmadi.

### 4.2 Tartib / asosiy rasm — `POST products/{id}/images/reorder/`

```json
{ "ids": [12, 9, 15] }
```

- `ids` — rasm id'lari yangi tartibda; birinchisi asosiy rasm bo'ladi.
- Asosiy rasmni almashtirish: tanlangan id ni ro'yxat **boshiga** qo'ying.
- Ro'yxatda yo'q rasmlar (masalan faqat `{"ids": [15]}`) o'z tartibida yuborilganlardan **keyin** qoladi.

Javob `200` — yakuniy to'liq tartib: `{"ids": [12, 9, 15]}`.

Xatolar: `400 {"ids": ["Not found: [17]"]}` — id shu mahsulotning rasmi emas; `400 {"ids": ["Duplicate ids."]}` — takror; `400` — `ids` bo'sh; `404` — mahsulot topilmadi.

### 4.3 O'chirish — `DELETE products/{id}/images/{image_id}/`

`204`, fayl ham o'chadi. Asosiy rasm o'chirilsa keyingisi asosiy bo'ladi. `404` — rasm shu mahsulotniki emas.

---

## 5. Frontda qilinadigan ishlar

1. "Saqlash" (yangi mahsulot): `POST products/` → javobdagi `id` ni saqlang → rasmlarni `POST products/{id}/images/` bilan ketma-ket yuklang → tartib o'zgargan bo'lsa `reorder/` → kerak bo'lsa `PATCH {"is_active": true}`.
2. `POST` muvaffaqiyatli bo'lgach forma tahrirlash rejimiga o'tsin (keyingi saqlashlar `PATCH products/{id}/`), shunda xato / qayta bosishda ikkinchi mahsulot yaratilmaydi.
3. Predmet kategoriya tanlanganda `GET item-categories/{id}/attributes/` dan xarakteristika maydonlarini chizing; kategoriya o'zgarsa eski qiymatlarni tozalang.
4. Model ro'yxatini tanlangan brend bo'yicha yuklang; brend o'zgarsa modelni tozalang.
5. `product_code` maydonini yaratish formasida ko'rsatmang (yoki faqat o'qiladigan qiling).
6. `400` javobidagi kalitlar maydon nomlari bilan bir xil — xatoni shu maydon ostida ko'rsating.
