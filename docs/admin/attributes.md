# Atributlar (xususiyatlar) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

Uchta joyda ishlatiladi:

- **Atributlar ma'lumotnomasi** — "Xususiyat" formasi: nom, qiymat turi, birlik, ruxsat etilgan qiymatlar, "Filtr sifatida".
- **Kategoriya atributlari** — qaysi atributlar qaysi kategoriyada (item category) ishlatilishi va tartibi.
- **Mahsulot kartasi** — mahsulotga shu kategoriya atributlarining qiymatlarini kiritish.

| Endpoint | Nima uchun |
| --- | --- |
| `GET attributes/` | atributlar ro'yxati |
| `POST / PATCH / DELETE attributes/{id}/` | atributni boshqarish (CRUD) |
| `GET item-categories/{id}/attributes/` | kategoriyaning atributlari (mahsulot formasi shu bilan chiziladi) |
| `PUT item-categories/{id}/attributes/` | kategoriyaga atributlarni biriktirish / tartiblash / ajratish |
| `GET products/{id}/` | mahsulot detali — `attribute_values` shu yerda keladi |
| `POST products/`, `PATCH products/{id}/` | mahsulotga atribut qiymatlarini yozish |

Swagger: `/swagger/admin/` → **attributes**, **item-categories**, **products**.

> Mahsulotga kiritilgan qiymatlar mijozga (mobil/web) mahsulot detalida `attributes` maydonida ko'rinadi — `docs/mobile/product_attributes.md`. Filtrlarda hali ishlamaydi.

---

## 1. Atributlar ma'lumotnomasi

### Obyekt

```json
{
  "id": 5,
  "name": "Тип управления",
  "name_uz": "Boshqaruv turi",
  "name_ru": "Тип управления",
  "name_en": null,
  "value_type": "list",
  "unit": "",
  "options": [
    { "id": 1, "value_uz": "Pult (simli)", "value_ru": "Пульт (проводной)", "value_en": null },
    { "id": 2, "value_uz": "Radio pult", "value_ru": "Радиопульт", "value_en": null }
  ],
  "is_filterable": false,
  "is_active": true,
  "item_categories": [
    {
      "id": 33,
      "name": "Смесители для кухни",
      "product_sub_category": { "id": 17, "name": "Смесители", "product_category": { "id": 9, "name": "Сантехника" } }
    }
  ],
  "item_categories_count": 1,
  "products_count": 12,
  "created_at": "2026-10-02T10:29:57.808000",
  "updated_at": "2026-10-02T10:29:57.808000"
}
```

| Maydon | Maketda | Turi | Izoh |
| --- | --- | --- | --- |
| `name_uz` | Nomi (UZ) | string, majburiy | maks. 150 belgi |
| `name_ru` | Nomi (RU) | string, majburiy | maks. 150 belgi |
| `name_en` | — | string | ixtiyoriy |
| `name` | — | faqat o'qish | joriy tildagi nom (default — ruscha) |
| `value_type` | Qiymat turi | string | `number` (Son), `list` (Ro'yxat), `text` (Matn), `boolean` (Ha / yo'q); default `list` |
| `unit` | Birlik | string | faqat `number` uchun, o'shanda majburiy; maks. 50 belgi |
| `options` | Ruxsat etilgan qiymatlar | massiv | faqat `list` uchun, o'shanda kamida 1 ta |
| `is_filterable` | Filtr sifatida | bool | default `false` |
| `is_active` | — | bool | default `true` |
| `item_categories` | Ishlatiladigan kategoriyalar | faqat o'qish | kategoriya tomonidan biriktiriladi (2-bo'lim) |
| `item_categories_count` | "N ta kategoriyada ishlatilmoqda" | faqat o'qish | |
| `products_count` | — | faqat o'qish | shu atributga qiymat kiritilgan mahsulotlar soni |

- `value_type` `number` bo'lmasa, yuborilgan `unit` e'tiborga olinmaydi (`""` bo'ladi).
- `value_type` `list` bo'lmasa, yuborilgan `options` e'tiborga olinmaydi (`[]` bo'ladi).

### Ro'yxat — `GET attributes/`

| Query | Misol | Izoh |
| --- | --- | --- |
| `value_type` | `?value_type=list` | |
| `is_filterable` | `?is_filterable=true` | |
| `is_active` | `?is_active=true` | |
| `in_use` | `?in_use=false` | `true` — kamida bitta kategoriyaga biriktirilgan |
| `item_category` | `?item_category=33` | shu kategoriyaga biriktirilganlar |
| `sub_category`, `category` | `?category=9` | yuqori darajadagi kategoriya bo'yicha |
| `search` | `?search=quvvat` | `name_uz`, `name_ru`, `name_en` bo'yicha |
| `ordering` | `?ordering=-products_count` | `id`, `name`, `value_type`, `item_categories_count`, `products_count`, `created_at`, `updated_at`; default `-created_at` |
| `page`, `page_size` | `?page=1&page_size=100` | default 20, maksimum 100 |

Javob — standart admin pagination (`count, next, previous, next_page, previous_page, results`), `results` ichida yuqoridagi obyektlar.

### Yaratish — `POST attributes/`

Son:

```json
{
  "name_uz": "Yuk ko'tarish quvvati",
  "name_ru": "Грузоподъёмность",
  "value_type": "number",
  "unit": "t",
  "is_filterable": true
}
```

Ro'yxat:

```json
{
  "name_uz": "Boshqaruv turi",
  "name_ru": "Тип управления",
  "value_type": "list",
  "options": [
    { "value_uz": "Pult (simli)", "value_ru": "Пульт (проводной)" },
    { "value_uz": "Radio pult", "value_ru": "Радиопульт" },
    { "value_uz": "Qo'lda", "value_ru": "Ручное" }
  ]
}
```

Matn va Ha / yo'q uchun faqat nom va `value_type` (`text` / `boolean`) yetarli.

Javob — `201 Created` + to'liq obyekt.

### O'zgartirish — `PATCH attributes/{id}/`

Faqat o'zgargan maydonlar yuboriladi. `options` yuborilmasa, qiymatlar o'zgarmaydi.

`options` yuborilsa, **butun ro'yxat** yuboriladi:

| Element | Natija |
| --- | --- |
| `id` bilan | shu qiymat yangilanadi |
| `id` siz | yangi qiymat yaratiladi |
| ro'yxatda yo'q | o'chiriladi |

Massivdagi tartib = ko'rsatish tartibi.

```json
{
  "options": [
    { "id": 3, "value_uz": "Qo'lda", "value_ru": "Вручную" },
    { "id": 1, "value_uz": "Pult (simli)", "value_ru": "Пульт (проводной)" },
    { "value_uz": "Yangi", "value_ru": "Новый" }
  ]
}
```

Qoidalar:

- Har bir qiymatda `value_uz` va `value_ru` majburiy; bitta atribut ichida takrorlanmasligi kerak (katta-kichik harf farqlanmaydi).
- Qiymat nomi o'zgartirilsa, uni ishlatayotgan mahsulotlardagi qiymat ham avtomatik yangilanadi.
- Mahsulotda ishlatilayotgan qiymatni ro'yxatdan olib tashlab bo'lmaydi → `400`.
- Atribut kategoriyaga biriktirilgan yoki mahsulotlarda qiymati bor bo'lsa, `value_type` ni o'zgartirib bo'lmaydi → `400`. Formada bunday atribut uchun "Qiymat turi"ni bloklab qo'ying (`item_categories_count > 0` yoki `products_count > 0`).

### O'chirish — `DELETE attributes/{id}/`

`204`, body yo'q. Atribut kategoriyaga biriktirilgan yoki mahsulotlarda qiymati bor bo'lsa → `400`. "O'chirish" tugmasini `item_categories_count > 0` yoki `products_count > 0` bo'lganda o'chirib qo'ying.

---

## 2. Kategoriya atributlari

Atribut formasidagi "Ishlatiladigan kategoriyalar" faqat ko'rsatiladi. Biriktirish kategoriya (item category) tomonidan qilinadi.

### Olish — `GET item-categories/{id}/attributes/`

```json
{
  "id": 33,
  "attributes": [
    {
      "id": 4,
      "name": "Грузоподъёмность",
      "value_type": "number",
      "unit": "t",
      "options": [],
      "is_filterable": true,
      "is_active": true
    },
    {
      "id": 5,
      "name": "Тип управления",
      "value_type": "list",
      "unit": "",
      "options": [
        { "id": 1, "value_uz": "Pult (simli)", "value_ru": "Пульт (проводной)", "value_en": null },
        { "id": 2, "value_uz": "Radio pult", "value_ru": "Радиопульт", "value_en": null }
      ],
      "is_filterable": false,
      "is_active": true
    }
  ]
}
```

Pagination yo'q. Atributlar kategoriyadagi tartibda keladi.

### Saqlash — `PUT item-categories/{id}/attributes/`

Butun ro'yxat yuboriladi; massivdagi tartib = kategoriyadagi tartib. Har bir element `4` yoki `{"id": 4}` ko'rinishida.

```bash
curl -X PUT {{host}}/api/v1/admin/item-categories/33/attributes/ \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"attributes": [4, 5]}'
```

| Amal | Body |
| --- | --- |
| Biriktirish | ro'yxatga atribut `id` sini qo'shish |
| Tartibni o'zgartirish | o'sha `id` larni yangi tartibda yuborish |
| Ajratish | `id` ni ro'yxatdan olib tashlash |
| Hammasini ajratish | `{"attributes": []}` |

Javob — `200 OK`, `GET` bilan bir xil.

- Bitta atribut ikki marta yuborilsa → `400`.
- Shu kategoriya mahsulotlarida qiymati bor atributni ajratib bo'lmaydi → `400` (avval mahsulotlardagi qiymatlarni tozalash kerak).

---

## 3. Mahsulotdagi atribut qiymatlari

Mahsulot detalida (`GET products/{id}/`) `attribute_values` massivi keladi. Ro'yxatda (`GET products/`) **yo'q**.

```json
"attribute_values": [
  {
    "id": 1,
    "attribute": { "id": 4, "name": "Грузоподъёмность", "value_type": "number", "unit": "t" },
    "value_uz": "2.5",
    "value_ru": "2.5"
  },
  {
    "id": 2,
    "attribute": { "id": 5, "name": "Тип управления", "value_type": "list", "unit": "" },
    "value_uz": "Pult (simli)",
    "value_ru": "Пульт (проводной)"
  }
]
```

Bitta mahsulotda bitta atributga bitta qiymat. Birlik mahsulotda saqlanmaydi — `attribute.unit` dan olinadi.

### Yozish — `POST products/`, `PATCH products/{id}/`

```json
{
  "attribute_values": [
    { "attribute": 4, "value_uz": "2.5", "value_ru": "2.5" },
    { "attribute": 5, "value_uz": "Pult (simli)", "value_ru": "Пульт (проводной)" },
    { "attribute": 7, "value_uz": "Po'lat", "value_ru": "Сталь" },
    { "attribute": 9, "value_uz": "true", "value_ru": "true" }
  ]
}
```

`attribute` — `4` yoki `{"id": 4}`. `value_uz` va `value_ru` har doim majburiy va **string**.

| `value_type` | `value_uz` / `value_ru` |
| --- | --- |
| `number` | son, string ko'rinishida (`"2.5"`, kasr nuqta bilan); ikkalasi bir xil |
| `list` | atributning `options` idan biri: o'sha qiymatning `value_uz` va `value_ru` si |
| `text` | erkin matn, har bir tilda alohida; maks. 255 belgi |
| `boolean` | `"true"` yoki `"false"`; ikkalasi bir xil |

| Amal | Body |
| --- | --- |
| Qiymatlarni saqlash | `attribute_values` — **butun ro'yxat** (yuborilmagan atribut qiymati o'chadi) |
| Hammasini tozalash | `{"attribute_values": []}` |
| Qiymatlarga tegmaslik | `attribute_values` maydonini yubormaslik |

- To'ldirilmagan atributni ro'yxatga qo'shmang (bo'sh qiymat yuborib bo'lmaydi).
- Atribut mahsulotning kategoriyasiga (`product_item_category`) biriktirilgan bo'lishi kerak, aks holda → `400`.
- Mahsulot kategoriyasi o'zgartirilsa va `attribute_values` yuborilmasa, yangi kategoriyada yo'q atributlarning qiymatlari avtomatik o'chadi. Kategoriya `null` qilinsa, hammasi o'chadi.

### Formani chizish

1. Mahsulot kategoriyasi tanlanganda `GET item-categories/{id}/attributes/` — shu ro'yxat bo'yicha inputlar chiziladi:

   | `value_type` | Input | Yuboriladi |
   | --- | --- | --- |
   | `number` | son input, yonida `unit` | kiritilgan son ikkala maydonga |
   | `list` | select, variantlar — `options` | tanlangan variantning `value_uz` va `value_ru` si |
   | `text` | ikkita matn input (UZ, RU) | har biri o'z maydoniga |
   | `boolean` | switch / checkbox | `"true"` yoki `"false"` ikkala maydonga |

2. Tahrirlashda `GET products/{id}/` dagi `attribute_values` ni `attribute.id` bo'yicha inputlarga joylang. `list` uchun tanlangan variantni `value_ru` bo'yicha `options` dan toping.
3. Saqlashda to'ldirilgan inputlarning hammasini `attribute_values` qilib yuboring.

---

## Xatolar

Admin API'da xatolar oddiy DRF formatida (klient API'dagi `{"ok", "error_code"}` o'rami yo'q). Xabar matnlari tilga bog'liq, shuning uchun matnga emas, HTTP status va maydon nomiga tayaning.

| Holat | HTTP | Body |
| --- | --- | --- |
| Token yo'q yoki yaroqsiz | 401 | `{"detail": "..."}` |
| `name_uz` / `name_ru` yuborilmadi | 400 | `{"name_uz": ["Обязательное поле."]}` |
| `number` turida `unit` yo'q | 400 | `{"unit": ["This field is required for the number type."]}` |
| `list` turida `options` yo'q yoki bo'sh | 400 | `{"options": ["At least one value is required for the list type."]}` |
| Qiymatning bir tili bo'sh | 400 | `{"options": [{"value_ru": ["Это поле не может быть пустым."]}]}` |
| Takroriy qiymat | 400 | `{"options": ["Values must be unique (value_uz)."]}` |
| Begona yoki takroriy option `id` | 400 | `{"options": ["Option ids must be unique and belong to this attribute."]}` |
| Ishlatilayotgan qiymatni olib tashlash | 400 | `{"options": ["Options used in products can't be removed: Пульт."]}` |
| Ishlatilayotgan atribut turini o'zgartirish | 400 | `{"value_type": ["Attribute is used in categories or products, its value type can't be changed."]}` |
| Ishlatilayotgan atributni o'chirish | 400 | `{"detail": "Attribute is used in categories, detach it from them first."}` |
| Kategoriyada takroriy atribut | 400 | `{"attributes": ["Attributes must be unique."]}` |
| Mavjud bo'lmagan atributni biriktirish | 400 | `{"attributes": [{"id": "Object with id=999999 does not exist."}]}` |
| Qiymati bor atributni kategoriyadan ajratish | 400 | `{"attributes": ["Attributes with values in the category's products can't be detached: Мощность."]}` |
| Mahsulot: atribut kategoriyaga biriktirilmagan | 400 | `{"attribute_values": ["Attributes [10] are not attached to the product's item category."]}` |
| Mahsulot: atribut takrorlangan | 400 | `{"attribute_values": ["Attributes must be unique."]}` |
| Mahsulot: qiymat yuborilmadi yoki bo'sh | 400 | `{"attribute_values": [{"value_ru": ["Это поле не может быть пустым."]}]}` |
| Mahsulot: `number` ga son emas | 400 | `{"attribute_values": [{"value_ru": ["A number is required, e.g. \"2.5\"."]}]}` |
| Mahsulot: `number` / `boolean` da `value_uz` ≠ `value_ru` | 400 | `{"attribute_values": [{"value_uz": ["Must be the same as value_ru for the number type."]}]}` |
| Mahsulot: `list` ga variantlarda yo'q qiymat | 400 | `{"attribute_values": [{"value_ru": ["Must be one of the attribute's options."]}]}` |
| Mahsulot: `boolean` ga boshqa qiymat | 400 | `{"attribute_values": [{"value_ru": ["\"true\" or \"false\" is required."]}]}` |
| Mavjud bo'lmagan `id` | 404 | `{"detail": "..."}` |

`attribute_values` va `options` xatolarida massivdagi tartib yuborilgan tartibga mos: xatosiz elementlar o'rnida `{}` keladi.

---

## Eslatmalar

- Atribut javobida avvalgi `item_category` maydoni endi yo'q — o'rniga `item_categories` (faqat o'qish). Atributni yaratish/tahrirlashda kategoriya yuborilmaydi.
- `is_active: false` atribut mijozga ko'rsatilmaydi (mahsulot detalida kelmaydi). Admin panelda esa uni ham kategoriyaga biriktirish va mahsulotga qiymat kiritish mumkin — backend cheklamaydi.
- `is_filterable` hozircha faqat saqlanadi — mijoz filtrlariga hali ta'sir qilmaydi.
- `list` turidagi mahsulot qiymati — variant matnining nusxasi (variant `id` si saqlanmaydi). Variant nomi admin paneldan o'zgartirilsa, mahsulotlardagi qiymat ham yangilanadi.
