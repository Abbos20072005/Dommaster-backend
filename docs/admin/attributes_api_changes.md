# Admin API: xususiyatlar va filtrlar — o'zgarishlar va to'liq kontrakt

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (tokensiz → `401`).

Mahsulot xususiyatlari endi faqat **atributlarda** saqlanadi:

- Erkin matnli `characteristics` yozilmaydi — o'rniga `attribute_values`.
- 1C dan kelgan xususiyatlar avtomatik atributga aylanadi.
- Mijoz (mobil / web) filtrlari atributlardan quriladi — alohida filtr sozlash sahifasi yo'q.

Bu hujjat o'zi yetarli: nima o'zgargani ham, atributlar bilan ishlashning to'liq kontrakti ham shu yerda.

## Mundarija

1. [Nima o'zgardi](#1-nima-ozgardi)
2. [Frontda qilinadigan ishlar](#2-frontda-qilinadigan-ishlar)
3. [Atributlar ma'lumotnomasi](#3-atributlar-malumotnomasi)
4. [Kategoriya atributlari](#4-kategoriya-atributlari)
5. [Mahsulotdagi xususiyatlar](#5-mahsulotdagi-xususiyatlar)
6. [Mijoz filtrlari qanday chiqadi](#6-mijoz-filtrlari-qanday-chiqadi)
7. [1C dan kelgan xususiyatlar](#7-1c-dan-kelgan-xususiyatlar)
8. [Hisoblagichlar](#8-hisoblagichlar)
9. [Xatolar](#9-xatolar)

---

## 1. Nima o'zgardi

| Endpoint | O'zgarish | Eski front buziladimi |
| --- | --- | --- |
| `GET products/{id}/` | `characteristics` endi atribut qiymatlaridan yig'iladi | Yo'q |
| `POST products/`, `PATCH products/{id}/` | yuborilgan `characteristics` **saqlanmaydi** | Xato chiqmaydi, lekin tahrir jim yo'qoladi |
| `GET products/{id}/` | `filter_data` maydoni olib tashlandi | Ha, agar o'qilsa |
| `GET item-categories/{id}/attributes/` | `is_quick_filter`, `max_quick_filters` qo'shildi | Yo'q |
| `PUT item-categories/{id}/attributes/` | elementda tezkor filtr sozlamasi; bitta xato shakli o'zgardi | Yo'q |
| `GET attributes/` | kontrakt o'zgarmagan; atributlar soni ~1 900 ga yetadi | Ha, agar hammasi bitta so'rovda yuklansa |
| `attributes/` dagi `is_filterable` | endi mijoz filtrlariga ta'sir qiladi | Yo'q |
| `GET categories/`, `sub-categories/`, `item-categories/` | `filters_count` ma'nosi o'zgardi | Yo'q |
| `GET today/` | `catalog.no_characteristics` ma'nosi o'zgardi | Yo'q |

Qolgan endpointlar o'zgarmagan.

---

## 2. Frontda qilinadigan ishlar

Majburiy:

1. **Mahsulot formasini `characteristics` dan `attribute_values` ga o'tkazish** ([5-bo'lim](#5-mahsulotdagi-xususiyatlar)). Hozir eski forma xato bermaydi, lekin xususiyatlardagi tahrir saqlanmaydi.
2. **`filter_data` ishlatilgan joyni olib tashlash** — maydon endi javobda yo'q.
3. **Atribut tanlash select'larini qidiruv bilan ishlaydigan qilish** (`?search=`). Atributlar ~1 900 ta, `page_size` maksimumi 100 — hammasini bitta so'rovda yuklab bo'lmaydi.

Ixtiyoriy:

4. Kategoriya atributlari sahifasiga tezkor filtr sozlamasini qo'shish ([4-bo'lim](#4-kategoriya-atributlari)).
5. `filters_count` va `no_characteristics` yorliqlari yangi ma'noga mos kelishini tekshirish ([8-bo'lim](#8-hisoblagichlar)).

---

## 3. Atributlar ma'lumotnomasi

Global ro'yxat: "Quvvat", "Rang", "Material" va h.k. Atribut bir marta yaratiladi va istalgancha kategoriyaga biriktiriladi.

| Endpoint | Nima uchun |
| --- | --- |
| `GET attributes/` | ro'yxat |
| `GET attributes/{id}/` | bitta atribut |
| `POST attributes/` | yaratish |
| `PATCH attributes/{id}/` | o'zgartirish |
| `DELETE attributes/{id}/` | o'chirish |

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

| Maydon | Turi | Izoh |
| --- | --- | --- |
| `name_uz` | string, majburiy | maks. 150 belgi |
| `name_ru` | string, majburiy | maks. 150 belgi |
| `name_en` | string | ixtiyoriy |
| `name` | faqat o'qish | joriy tildagi nom (default — ruscha) |
| `value_type` | string | `number` (Son), `list` (Ro'yxat), `text` (Matn), `boolean` (Ha / yo'q); default `list` |
| `unit` | string | faqat `number` uchun, o'shanda majburiy; maks. 50 belgi |
| `options` | massiv | faqat `list` uchun, o'shanda kamida 1 ta |
| `is_filterable` | bool | default `false`. **Endi ishlaydi**: `true` — atribut biriktirilgan kategoriyalarda mijoz filtri bo'lib chiqadi |
| `is_active` | bool | default `true`. `false` — mijozga mahsulot kartasida ham, filtrlarda ham ko'rinmaydi |
| `item_categories` | faqat o'qish | atribut biriktirilgan kategoriyalar; biriktirish kategoriya tomonidan qilinadi ([4-bo'lim](#4-kategoriya-atributlari)) |
| `item_categories_count` | faqat o'qish | nechta kategoriyada ishlatiladi |
| `products_count` | faqat o'qish | shu atributga qiymat kiritilgan mahsulotlar soni |

- `value_type` `number` bo'lmasa, yuborilgan `unit` e'tiborga olinmaydi (`""` bo'ladi).
- `value_type` `list` bo'lmasa, yuborilgan `options` e'tiborga olinmaydi (`[]` bo'ladi).
- `item_categories` uzun bo'lishi mumkin: bitta atribut 100+ kategoriyada ishlatiladi. Ro'yxat sahifasida sanoq uchun `item_categories_count` ni ishlating.

### Ro'yxat — `GET attributes/`

| Query | Misol | Izoh |
| --- | --- | --- |
| `search` | `?search=quvvat` | `name_uz`, `name_ru`, `name_en` bo'yicha |
| `value_type` | `?value_type=list` | |
| `is_filterable` | `?is_filterable=true` | |
| `is_active` | `?is_active=true` | |
| `in_use` | `?in_use=false` | `true` — kamida bitta kategoriyaga biriktirilgan |
| `item_category` | `?item_category=33` | shu kategoriyaga biriktirilganlar |
| `sub_category`, `category` | `?category=9` | yuqori darajadagi kategoriya bo'yicha |
| `ordering` | `?ordering=-products_count` | `id`, `name`, `value_type`, `item_categories_count`, `products_count`, `created_at`, `updated_at`; default `-created_at` |
| `page`, `page_size` | `?page=1&page_size=100` | default 20, maksimum 100 |

Javob — standart admin pagination: `count, next, previous, next_page, previous_page, results`.

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
    { "value_uz": "Radio pult", "value_ru": "Радиопульт" }
  ]
}
```

Matn va Ha / yo'q uchun faqat nom va `value_type` (`text` / `boolean`) yetarli. Javob — `201` + to'liq obyekt.

### O'zgartirish — `PATCH attributes/{id}/`

Faqat o'zgargan maydonlar yuboriladi. `options` yuborilmasa, variantlar o'zgarmaydi. Yuborilsa — **butun ro'yxat**:

| Element | Natija |
| --- | --- |
| `id` bilan | shu variant yangilanadi |
| `id` siz | yangi variant yaratiladi |
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

- Har bir variantda `value_uz` va `value_ru` majburiy; bitta atribut ichida takrorlanmasligi kerak (katta-kichik harf farqlanmaydi).
- Variant nomi o'zgartirilsa, uni ishlatayotgan mahsulotlardagi qiymat ham avtomatik yangilanadi.
- Mahsulotda ishlatilayotgan variantni ro'yxatdan olib tashlab bo'lmaydi → `400`.
- Atribut kategoriyaga biriktirilgan yoki mahsulotlarda qiymati bor bo'lsa, `value_type` ni o'zgartirib bo'lmaydi → `400`. Bunday atributda "Qiymat turi"ni bloklab qo'ying (`item_categories_count > 0` yoki `products_count > 0`).

### O'chirish — `DELETE attributes/{id}/`

`204`, body yo'q. Atribut kategoriyaga biriktirilgan yoki mahsulotlarda qiymati bor bo'lsa → `400`. "O'chirish" tugmasini `item_categories_count > 0` yoki `products_count > 0` bo'lganda o'chirib qo'ying.

---

## 4. Kategoriya atributlari

Qaysi atributlar qaysi kategoriyada (L3, item category) ishlatilishi, tartibi va tezkor filtrlar.

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
      "is_active": true,
      "is_quick_filter": false,
      "max_quick_filters": 0
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
      "is_filterable": true,
      "is_active": true,
      "is_quick_filter": true,
      "max_quick_filters": 3
    }
  ]
}
```

Pagination yo'q. Atributlar kategoriyadagi tartibda keladi.

| Maydon | Izoh |
| --- | --- |
| `id`, `name`, `value_type`, `unit`, `options`, `is_filterable`, `is_active` | atributning o'zi — faqat o'qish, ma'lumotnomada tahrirlanadi |
| `is_quick_filter` | **yangi.** Shu kategoriyada tezkor filtr (mijozda ro'yxat ustidagi chiplar) bo'lsinmi; default `false` |
| `max_quick_filters` | **yangi.** Nechta qiymat chip bo'lib chiqadi (eng ko'p ishlatilganlari); `0` — hammasi |

`is_quick_filter` va `max_quick_filters` — atributning emas, **shu kategoriyadagi** sozlamasi. Faqat `is_filterable: true` va `value_type` `number` bo'lmagan atributlarda ta'sir qiladi; qolganlarida inputni bloklab qo'ysa bo'ladi.

### Saqlash — `PUT item-categories/{id}/attributes/`

Butun ro'yxat yuboriladi; massivdagi tartib = kategoriyadagi tartib. Element uch xil ko'rinishda bo'lishi mumkin:

```json
{
  "attributes": [
    4,
    { "id": 5 },
    { "id": 7, "is_quick_filter": true, "max_quick_filters": 3 }
  ]
}
```

| Amal | Body |
| --- | --- |
| Biriktirish | ro'yxatga atribut `id` sini qo'shish |
| Tartibni o'zgartirish | o'sha `id` larni yangi tartibda yuborish |
| Tezkor filtr | elementga `is_quick_filter` / `max_quick_filters` qo'shish |
| Ajratish | `id` ni ro'yxatdan olib tashlash |
| Hammasini ajratish | `{"attributes": []}` |

Javob — `200`, `GET` bilan bir xil.

- `is_quick_filter` / `max_quick_filters` yuborilmasa, **avvalgi qiymati saqlanadi** — faqat `id` lar yuboradigan eski forma sozlamalarni buzmaydi.
- Bitta atribut ikki marta yuborilsa → `400`.
- Shu kategoriya mahsulotlarida qiymati bor atributni ajratib bo'lmaydi → `400` (avval mahsulotlardagi qiymatlarni tozalash kerak).
- Mavjud bo'lmagan atribut → `400`; bu xatoning shakli o'zgardi:

| | Body |
| --- | --- |
| Avval | `{"attributes": [{"id": "Object with id=999999 does not exist."}]}` |
| Hozir | `{"attributes": ["Attributes [999999] do not exist."]}` |

---

## 5. Mahsulotdagi xususiyatlar

### `attribute_values` — yagona yozish yo'li

Mahsulot detalida (`GET products/{id}/`) keladi. Ro'yxatda (`GET products/`) **yo'q**.

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
| `list` | atributning `options` idan biri: o'sha variantning `value_uz` va `value_ru` si |
| `text` | erkin matn, har bir tilda alohida; maks. 255 belgi |
| `boolean` | `"true"` yoki `"false"`; ikkalasi bir xil |

| Amal | Body |
| --- | --- |
| Qiymatlarni saqlash | `attribute_values` — **butun ro'yxat** (yuborilmagan atribut qiymati o'chadi) |
| Hammasini tozalash | `{"attribute_values": []}` |
| Qiymatlarga tegmaslik | `attribute_values` maydonini yubormaslik |

- To'ldirilmagan atributni ro'yxatga qo'shmang (bo'sh qiymat yuborib bo'lmaydi).
- Atribut mahsulotning kategoriyasiga (`product_item_category`) biriktirilgan bo'lishi kerak, aks holda → `400`.
- Mahsulot kategoriyasi o'zgartirilsa va `attribute_values` yuborilmasa, yangi kategoriyada yo'q atributlarning qiymatlari **avtomatik o'chadi**. Kategoriya `null` qilinsa, hammasi o'chadi. Kategoriyani o'zgartirishdan oldin foydalanuvchini ogohlantirgan ma'qul.

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
4. Ba'zi kategoriyalarda 50–100 ta atribut bo'ladi — forma uzun chiqishini hisobga oling.

### `characteristics` — eskirgan, faqat o'qiladi

Avval — erkin matnli ro'yxat, yozish mumkin edi. Hozir — `attribute_values` ning eski ko'rinishdagi nusxasi:

```json
"characteristics": [
  {
    "id": 71074,
    "name_uz": "Бренд", "name_ru": "Бренд", "name_en": null,
    "value_uz": "Schneider Electric", "value_ru": "Schneider Electric", "value_en": null,
    "unit_uz": "", "unit_ru": "", "unit_en": ""
  }
]
```

| | Avval | Hozir |
| --- | --- | --- |
| Manba | alohida erkin matnli yozuvlar | mahsulotning atribut qiymatlari |
| `id` | xususiyat yozuvi ID'si | atribut qiymati ID'si (`attribute_values[].id` bilan bir xil) |
| `name_*` | erkin matn | atribut nomi |
| `unit_*` | erkin matn, har tilda alohida | atributning birligi, uchala tilda bir xil |
| `value_*` | erkin matn | atribut qiymati (`boolean` da `"true"` / `"false"`) |
| Yozish | ro'yxat hammasini almashtirardi | **e'tiborga olinmaydi**, `200` qaytadi, hech narsa saqlanmaydi |
| Ro'yxatda (`GET products/`) | yo'q | yo'q |

Maydon faqat eski forma buzilmasligi uchun qoldirilgan. Forma `attribute_values` ga o'tgach olib tashlanadi — yangi kodda ishlatmang.

### `filter_data` — olib tashlandi

Faqat o'qiladigan JSON edi (1C filtr qiymatlari). Endi javobda yo'q; o'rnini bosuvchi maydon yo'q.

---

## 6. Mijoz filtrlari qanday chiqadi

Mijozdagi (mobil / web) kategoriya filtrlari atributlardan avtomatik quriladi. Admin panelda alohida filtr sahifasi kerak emas — quyidagi sozlamalar yetadi:

| Admin panelda | Mijozda |
| --- | --- |
| Atributda `is_filterable: true` va `is_active: true` | atribut biriktirilgan kategoriyalarda filtr bo'lib chiqadi |
| `value_type: number` | diapazon (min–max) filtri, `unit` bilan |
| `list`, `text`, `boolean` | belgilash (checkbox) filtri: mahsulotlarda uchragan qiymatlar va ularning soni |
| Kategoriyadagi atributlar tartibi | filtrlar tartibi |
| Kategoriyada `is_quick_filter` | ro'yxat ustidagi tezkor chiplar; `max_quick_filters` — nechta |
| Atribut nomi va qiymatlarning tarjimasi | filtr nomi va qiymatlari mijoz tilida (tarjima bo'lmasa ruscha) |

- Kategoriya mahsulotlarida qiymati yo'q atribut filtrda ko'rinmaydi.
- O'zgarishlar (atribut, kategoriya atributlari, mahsulot qiymatlari) mijozda **darhol** ko'rinadi.
- `text` atributni filtr qilish mumkin, lekin qiymati deyarli har mahsulotda har xil bo'lsa (model, artikul) foydasiz — bunday atributlarda "Filtr sifatida"ni o'chirib qo'ying.
- Narx filtri har doim bor, sozlanmaydi.

---

## 7. 1C dan kelgan xususiyatlar

1C mahsulot xususiyatlarini erkin matn sifatida yuboradi (nom + qiymat). Server ularni muntazam ravishda atributga aylantiradi:

| 1C dagi | Admin panelda |
| --- | --- |
| Xususiyat nomi | shu nomli (`name_ru`) atribut; yo'q bo'lsa yaratiladi, `name_uz` = ruscha nusxa |
| Mahsulot kategoriyasi | atribut shu kategoriyaga biriktiriladi (ro'yxat oxiriga) |
| Qiymat | mahsulotning atribut qiymati (`value_uz` = ruscha nusxa) |

Yangi atributning turi qiymatlariga qarab aniqlanadi:

| Qiymatlar | Tur |
| --- | --- |
| hammasi `да` / `нет` | `boolean` |
| hammasi "son + bir xil birlik" (`10 А`, `16 А`) | `number`, birlik atributga chiqadi |
| takrorlanadigan, 20 tadan ko'p bo'lmagan turli qiymat | `list`, variantlar avtomatik yaratiladi |
| qolganlari | `text` |

Admin panel uchun oqibatlari:

- Mahsulotda shu atributning qiymati allaqachon bo'lsa, 1C dagi qiymat uni **almashtirmaydi** — admin panelda kiritilgan qiymat ustun.
- Admin panelda o'chirilgan qiymat qayta paydo bo'lmaydi.
- `list` atributga 1C dan yangi qiymat kelsa, variantlar ro'yxatiga qo'shiladi.
- Qiymat atribut turiga to'g'ri kelmasa (masalan `number` atributga matn), u tashlab ketiladi.
- Avtomatik yaratilgan atributlar tarjimasiz (o'zbekcha nom va qiymatlar ruscha).
- "Filtr sifatida" avtomatik yoqiladi; faqat qiymati deyarli har mahsulotda har xil bo'lgan `text` atributlarda o'chiq.
- Import qilingan atributlar darhol kategoriyaga biriktirilgan va qiymatga ega bo'ladi, shuning uchun ularning `value_type` ini o'zgartirib va o'zini o'chirib bo'lmaydi (`400`).
- Backend yangilangandan birinchi import tugaguncha mahsulotlarda `attribute_values` va `characteristics` bo'sh keladi.

---

## 8. Hisoblagichlar

| Maydon | Avval | Hozir |
| --- | --- | --- |
| `filters_count` (`categories/`, `sub-categories/`, `item-categories/`) | 1C filtr sxemalaridagi turli kalitlar soni | ostidagi L3 kategoriyalarga biriktirilgan, "Filtr sifatida" yoqilgan faol atributlar soni (takrorlanmasdan) |
| `catalog.no_characteristics` (`today/`) | faol, xususiyati ham, atribut qiymati ham yo'q mahsulotlar | faol, birorta ham atribut qiymati yo'q mahsulotlar |

Maydon nomlari va turlari o'zgarmagan.

---

## 9. Xatolar

Xatolar oddiy DRF formatida. Xabar matnlari tilga bog'liq, shuning uchun matnga emas, HTTP status va maydon nomiga tayaning.

| Holat | HTTP | Body |
| --- | --- | --- |
| Token yo'q yoki yaroqsiz | 401 | `{"detail": "..."}` |
| Mavjud bo'lmagan `id` | 404 | `{"detail": "..."}` |
| **Atribut** | | |
| `name_uz` / `name_ru` yuborilmadi | 400 | `{"name_uz": ["Обязательное поле."]}` |
| `number` turida `unit` yo'q | 400 | `{"unit": ["This field is required for the number type."]}` |
| `list` turida `options` yo'q yoki bo'sh | 400 | `{"options": ["At least one value is required for the list type."]}` |
| Variantning bir tili bo'sh | 400 | `{"options": [{"value_ru": ["Это поле не может быть пустым."]}]}` |
| Takroriy variant | 400 | `{"options": ["Values must be unique (value_uz)."]}` |
| Begona yoki takroriy variant `id` | 400 | `{"options": ["Option ids must be unique and belong to this attribute."]}` |
| Ishlatilayotgan variantni olib tashlash | 400 | `{"options": ["Options used in products can't be removed: Пульт."]}` |
| Ishlatilayotgan atribut turini o'zgartirish | 400 | `{"value_type": ["Attribute is used in categories or products, its value type can't be changed."]}` |
| Kategoriyaga biriktirilgan atributni o'chirish | 400 | `{"detail": "Attribute is used in categories, detach it from them first."}` |
| Mahsulotlarda qiymati bor atributni o'chirish | 400 | `{"detail": "Attribute has values in products, clear them first."}` |
| **Kategoriya atributlari** | | |
| Takroriy atribut | 400 | `{"attributes": ["Attributes must be unique."]}` |
| Mavjud bo'lmagan atribut | 400 | `{"attributes": ["Attributes [999999] do not exist."]}` |
| Qiymati bor atributni ajratish | 400 | `{"attributes": ["Attributes with values in the category's products can't be detached: Мощность."]}` |
| **Mahsulot** | | |
| Atribut kategoriyaga biriktirilmagan | 400 | `{"attribute_values": ["Attributes [10] are not attached to the product's item category."]}` |
| Atribut takrorlangan | 400 | `{"attribute_values": ["Attributes must be unique."]}` |
| Qiymat yuborilmadi yoki bo'sh | 400 | `{"attribute_values": [{"value_ru": ["Это поле не может быть пустым."]}]}` |
| `number` ga son emas | 400 | `{"attribute_values": [{"value_ru": ["A number is required, e.g. \"2.5\"."]}]}` |
| `number` / `boolean` da `value_uz` ≠ `value_ru` | 400 | `{"attribute_values": [{"value_uz": ["Must be the same as value_ru for the number type."]}]}` |
| `list` ga variantlarda yo'q qiymat | 400 | `{"attribute_values": [{"value_ru": ["Must be one of the attribute's options."]}]}` |
| `boolean` ga boshqa qiymat | 400 | `{"attribute_values": [{"value_ru": ["\"true\" or \"false\" is required."]}]}` |

`attribute_values` va `options` xatolarida massivdagi tartib yuborilgan tartibga mos: xatosiz elementlar o'rnida `{}` keladi.
