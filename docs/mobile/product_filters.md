# Mahsulot filtrlari — mobile / web uchun

Base URL: `{{host}}/api/v1/`
Token shart emas.

Filtrlar endi mahsulot **atributlaridan** quriladi (admin panelda boshqariladi). Endpointlar va javob shakli o'zgarmagan, lekin filtr kalitlari va qiymat obyektlari o'zgardi — [nima o'zgardi](#nima-ozgardi) bo'limiga qarang.

| Endpoint | Nima uchun |
| --- | --- |
| `POST product/filter/` | mahsulotlar ro'yxati + shu ro'yxatga mos filtrlar |
| `GET item-category/{id}/filters/` | kategoriyaning filtrlari (mahsulotlarsiz) |

Til `Accept-Language` headeridan olinadi (`uz`, `ru`, `en`; default `ru`).

---

## 1. Filtr obyekti

`available_filters` (yoki `GET item-category/{id}/filters/` dagi `result`) — filtrlar massivi, ko'rsatish tartibida:

```json
[
  { "key": "price", "label": "Narx", "type": "range", "unit": "so'm", "min": 405.0, "max": 1061082.0 },
  {
    "key": "2040",
    "label": "Brend",
    "type": "checkbox",
    "unit": "",
    "values": [
      { "value": "WaterPRO", "label": "WaterPRO", "count": 316 },
      { "value": "VERO", "label": "VERO", "count": 121 }
    ]
  },
  { "key": "2512", "label": "Uzunlik", "type": "range", "unit": "mm", "min": 8.0, "max": 16.0 },
  {
    "key": "2731",
    "label": "Rezba mavjudligi",
    "type": "checkbox",
    "unit": "",
    "values": [
      { "value": "true", "label": "Ha", "count": 112 },
      { "value": "false", "label": "Yo'q", "count": 9 }
    ]
  }
]
```

| Maydon | Izoh |
| --- | --- |
| `key` | filtr kaliti. `"price"` — narx; qolganlari atribut ID'si **string** ko'rinishida. Kodga qotirmang — har doim javobdan oling |
| `label` | filtr nomi, so'ralgan tilda |
| `type` | `range` yoki `checkbox` |
| `unit` | o'lchov birligi; faqat `range` da to'ladi, `checkbox` da `""` |
| `min`, `max` | faqat `range` da; shu ro'yxatdagi eng kichik va eng katta qiymat |
| `values` | faqat `checkbox` da; ko'p ishlatilgani birinchi |
| `values[].value` | so'rovda **qaytarib yuboriladigan** qiymat — o'zgartirmang, tarjima qilmang |
| `values[].label` | foydalanuvchiga **ko'rsatiladigan** matn, so'ralgan tilda |
| `values[].count` | shu qiymatli mahsulotlar soni |

- `price` har doim birinchi keladi (ro'yxatda mahsulot bo'lsa).
- Ro'yxatdagi mahsulotlarda qiymati yo'q filtr kelmaydi.
- Tarjima bo'lmasa `label` ruscha keladi.

---

## 2. Mahsulotlarni filtrlash — `POST product/filter/`

```json
{
  "page": 1,
  "page_size": 20,
  "item_category": 452,
  "sort_by": "price",
  "filters": {
    "price": { "min": 1000, "max": 50000 },
    "2040": ["WaterPRO", "VERO"],
    "2512": { "min": 8, "max": 12 },
    "2731": ["true"]
  }
}
```

`filters` — obyekt: kalit = filtrning `key` i.

| `type` | Qiymat | Izoh |
| --- | --- | --- |
| `range` | `{"min": 8, "max": 12}` | `min` yoki `max` dan bittasini yuborsa ham bo'ladi |
| `checkbox` | `["WaterPRO", "VERO"]` | tanlangan `values[].value` lar |

- Bitta filtr ichidagi qiymatlar — **YOKI** (WaterPRO yoki VERO).
- Turli filtrlar orasida — **VA** (brend va uzunlik).
- Noma'lum kalit e'tiborga olinmaydi (xato qaytmaydi).

Qolgan maydonlar o'zgarmagan: `q`, `sort_by` (`newest`, `price`, `rating`), `price_from`, `price_to`, `brand`, `category`, `sub_category`, `item_category`, `sale_id`, `page`, `page_size`.

### Javob

```json
{
  "ok": true,
  "result": { "totalElements": 316, "content": [ { "id": 10149, "...": "..." } ] },
  "available_filters": [ { "key": "price", "...": "..." } ],
  "quick_filters": [
    { "key": "2040", "label": "WaterPRO", "value": "WaterPRO", "count": 316 }
  ]
}
```

`available_filters` qachon keladi:

| So'rov | `available_filters` |
| --- | --- |
| `item_category` bor | shu kategoriyaning filtrlari |
| `item_category` yo'q, lekin qidiruv yoki boshqa filtr bor (`q`, `brand`, `category`, ...) | topilgan mahsulotlar eng ko'p bo'lgan 5 ta kategoriyaning filtrlari |
| hech narsa yuborilmagan | `[]` |

Filtr tanlangandan keyin `available_filters` dagi `count`, `min`, `max` **filtrlangan** ro'yxat bo'yicha qayta hisoblanadi. Ya'ni tanlangan filtrlarni UI'da saqlab turing — javobda boshqa qiymatlar yo'qolishi mumkin.

---

## 3. Tezkor filtrlar — `quick_filters`

Ro'yxat ustidagi chiplar. Admin kategoriyada belgilagan atributlarning eng ko'p ishlatilgan qiymatlari.

```json
{ "key": "2040", "label": "WaterPRO", "value": "WaterPRO", "count": 316 }
```

Chip bosilganda: `filters[key] = [value]` qilib `product/filter/` ga yuboriladi. `label` — ko'rsatiladigan matn. Belgilanmagan bo'lsa — `[]`.

---

## 4. Kategoriya filtrlari — `GET item-category/{id}/filters/`

```json
{
  "ok": true,
  "result": [ { "key": "price", "...": "..." } ],
  "quick_filters": []
}
```

`result` — 1-bo'limdagi filtr obyektlari, kategoriyaning barcha faol mahsulotlari bo'yicha. Filtr sahifasini mahsulotlarni yuklamasdan chizish uchun.

---

## Nima o'zgardi

| | Avval | Hozir |
| --- | --- | --- |
| `key` | nomdan yasalgan matn (`"тип-лампы"`) | atribut ID'si string ko'rinishida (`"2040"`); `price` o'zgarmagan |
| `label` | faqat ruscha | so'ralgan tilda |
| `type` | `range`, `checkbox`, `radio` | `range`, `checkbox` |
| `values[]` | `{value, count}` | `{value, label, count}` |
| Narx filtri | `label: "Цена"`, `unit: "сум"` | so'ralgan tilda (`Narx` / `so'm`) |

Mobil ilovada qilinadigan ishlar:

1. `values[].label` ni ko'rsating, `values[].value` ni yuboring. Eski ilova `value` ni ko'rsatadi — u ham ishlaydi, lekin tarjimasiz va ha/yo'q filtrlarida `true` / `false` chiqadi.
2. Kalitlarni saqlab qo'ymang va kodga yozmang (deeplink, saqlangan filtrlar). Eski kalit yuborilsa, e'tiborga olinmaydi.
3. `radio` turini qo'llab-quvvatlash shart emas — endi kelmaydi.

---

## Eslatmalar

- Bitta mahsulotda bitta atributga bitta qiymat bor, shuning uchun `checkbox` filtrlari "shu qiymatlardan biri" ma'nosida ishlaydi.
- `range` filtrlari faqat son turidagi atributlardan chiqadi; qiymatlar kasr bo'lishi mumkin (`0.75`).
- Qaysi atribut filtr bo'lishi, tartibi va tezkor filtrlar admin panelda sozlanadi — ilova yangilanmasdan o'zgaradi.
- Kategoriya filtrlari 24 soat keshlanadi; mahsulot, atribut yoki qiymat o'zgarganda kesh darhol tozalanadi.
- Mahsulot kartasidagi xususiyatlar ham shu atributlardan keladi — `docs/mobile/product_attributes.md`.
