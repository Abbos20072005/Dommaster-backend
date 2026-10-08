# Tahlil → Savdo — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET analytics/sales/` | "Savdo" sahifasidagi **barcha** vidjetlar bitta javobda |

Swagger: `/swagger/admin/` → **analytics**.

---

## Query parametrlar

| Parametr | Default | Izoh |
| --- | --- | --- |
| `days` | `30` | bugun bilan tugaydigan oyna (1–365). `date_from` + `date_to` yuborilsa e'tiborga olinmaydi |
| `date_from`, `date_to` | — | aniq davr (`YYYY-MM-DD`, ikkalasi ham kiradi). **Birga** yuboriladi, ko'pi bilan 366 kun |

Davr `cohorts` dan boshqa **hamma** vidjetga ta'sir qiladi. "Oldingi davr" — shu davrdan oldingi, xuddi shu uzunlikdagi davr
(masalan `09.09–08.10` uchun `10.08–08.09`).

Xatolar — `400`: `{"date_to": ["date_from and date_to are sent together."]}`, `{"date_to": ["The range is at most 366 days."]}`.

---

## Javob

```json
{
  "summary": { ... },
  "chart": { ... },
  "categories": [ ... ],
  "payment_methods": [ ... ],
  "delivery_types": [ ... ],
  "top_products": [ ... ],
  "refunded_products": [ ... ],
  "cohorts": { ... }
}
```

Umumiy qoidalar:

- Buyurtma davrga **yaratilgan sanasi** (`created_at`) bo'yicha tushadi.
- **Tushum** — faqat **yakunlangan** (`status=3`) buyurtmalar summasi (`total_price`, yetkazib berish bilan) — bosh sahifadagi (`dashboard/`) bilan bir xil qoida. Shuning uchun oxirgi kunlar tushumi buyurtmalar yakunlangani sari o'sadi.
- **Buyurtmalar soni** — holatidan qat'i nazar yaratilgan barcha buyurtmalar.
- Summalar — so'mda, `float`. Foizlar — `0–100`, 1 xona aniqlikda.
- Javob keshlanmaydi.

### `summary` — yuqoridagi kartochkalar

```json
"summary": {
  "days": 30,
  "date_from": "2026-09-09",
  "date_to": "2026-10-08",
  "revenue": { "value": 2270000000.0, "change": 2.2 },
  "orders": { "value": 2504.0, "change": 2.0 },
  "average_check": { "value": 943784.0, "change": 0.1 },
  "cancel_rate": { "value": 4.1, "change": -0.1 },
  "refund_rate": { "value": 1.8, "change": -0.1 },
  "repeat_rate": { "value": 43.0, "change": 2.1 }
}
```

| Maydon | Dizaynda | Izoh |
| --- | --- | --- |
| `revenue` | Tushum | yakunlangan buyurtmalar summasi |
| `orders` | Buyurtmalar | yaratilgan barcha buyurtmalar |
| `average_check` | O'rtacha chek | yakunlangan buyurtmalarning o'rtacha summasi |
| `cancel_rate` | Bekor qilish | bekor qilingan (`status=4`) / barcha buyurtmalar, % |
| `refund_rate` | Qaytarish | puli qaytarilgan (`payment_status=3`) / barcha buyurtmalar, % |
| `repeat_rate` | Takroriy xarid | davrda buyurtma bergan mijozlardan nechasi uchun bu **birinchi buyurtma emas** (bekor qilinganlar hisobga olinmaydi), % |

`change`:

- `revenue`, `orders`, `average_check` — oldingi davrga nisbatan **foizda** (`▲ 2,2%`); oldingi davr `0` bo'lsa `null`.
- `cancel_rate`, `refund_rate`, `repeat_rate` — oldingi davrdan farq **foiz punktida** (`▼ 0,1 p.p.`); oldingi davrda buyurtma / xaridor bo'lmasa `null`.

### `chart` — tushum va buyurtmalar

```json
"chart": {
  "step": "day",
  "points": [
    {
      "date": "2026-09-09",
      "revenue": 71400000.0,
      "orders": 84,
      "previous_date": "2026-08-10",
      "previous_revenue": 66250000.0
    }
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `step` | har doim `day` — bitta nuqta = bitta kun |
| `points[]` | davrning har bir kuni, eskidan yangiga; bo'sh kunlar `0` bilan |
| `revenue` | "Tushum" chizig'i (chap o'q) |
| `orders` | "Buyurtmalar" chizig'i (o'ng o'q) |
| `previous_revenue` | "Tushum · oldingi davr" chizig'i: oldingi davrning shu tartibdagi kuni (`previous_date`) |

### `categories` — kategoriyalar bo'yicha tushum

```json
"categories": [
  { "category": { "id": 2, "name": "Elektr jihozlari" }, "revenue": 612000000.0, "percent": 27.0 }
]
```

Eng ko'p tushum bergan **8 tagacha** yuqori darajali kategoriya, kattadan kichikka. `percent` — davrdagi barcha mahsulotlar
tushumidagi ulush (ro'yxatga kirmaganlar ham hisobda, shuning uchun yig'indi `100` dan kam bo'lishi mumkin).

> Buyurtma qatorida narx saqlanmaydi: mahsulot tushumi = `soni × mahsulotning hozirgi narxi` (chegirmali narx bo'lsa — o'sha).
> Narx keyin o'zgargan bo'lsa yoki promokod / yetkazib berish bo'lsa, `categories` va `top_products` yig'indisi
> `summary.revenue` ga teng chiqmaydi. `percent` uchun bu muhim emas.

### `payment_methods` — to'lov usullari

```json
"payment_methods": [
  { "key": "click", "orders": 1104, "revenue": 1023000000.0, "orders_percent": 45.9, "revenue_percent": 45.1 },
  { "key": "cash", "orders": 690, "revenue": 633000000.0, "orders_percent": 28.7, "revenue_percent": 27.9 }
]
```

Yakunlangan buyurtmalar. **Har doim 6 ta qator** (bo'shlari `0` bilan), tushum bo'yicha kattadan kichikka:

| `key` | Nima |
| --- | --- |
| `click`, `payme`, `uzum` | onlayn to'lov (`payment_type` 1 / 2 / 3) |
| `cash`, `card` | olganda to'lash (`payment_type=4`), naqd / karta |
| `other` | to'lov turi ko'rsatilmagan buyurtmalar |

### `delivery_types` — olish usuli

```json
"delivery_types": [
  { "key": "delivery", "orders": 1502, "revenue": 1480000000.0, "orders_percent": 62.5, "revenue_percent": 65.2 },
  { "key": "pickup", "orders": 902, "revenue": 790000000.0, "orders_percent": 37.5, "revenue_percent": 34.8 }
]
```

Yakunlangan buyurtmalar, har doim 2 ta qator: `delivery` (Yetkazib berish), `pickup` (Olib ketish). Maydonlar `payment_methods` dagidek.

### `top_products` — eng ko'p sotilgan mahsulotlar

```json
"top_products": [
  {
    "product": { "id": 672, "name": "Avtomat Chint NXB-63 1P C25", "product_code": "00-00012345", "articul_code": "NXB-63-C25" },
    "quantity": 412,
    "revenue": 18540000.0,
    "change": 4.2
  }
]
```

Yakunlangan buyurtmalardagi **10 tagacha** mahsulot, **tushum** bo'yicha kattadan kichikka.

| Maydon | Izoh |
| --- | --- |
| `product.product_code` / `articul_code` | 1C kodi / artikul — "SKU" ustuni; ikkalasi ham `null` bo'lishi mumkin |
| `quantity` | sotilgan soni |
| `revenue` | `soni × hozirgi narx` (yuqoridagi izohga qarang) |
| `change` | tushum oldingi davrga nisbatan, %; oldingi davrda sotilmagan bo'lsa `null` |

### `refunded_products` — eng ko'p qaytarilgan mahsulotlar

```json
"refunded_products": [
  { "product": { "id": 672, "name": "Avtomat Chint NXB-63 1P C25", "product_code": null, "articul_code": null }, "quantity": 6, "orders": 4 }
]
```

Puli qaytarilgan (`payment_status=3`) buyurtmalardagi **10 tagacha** mahsulot, soni bo'yicha kattadan kichikka.
`quantity` — shu buyurtmalardagi soni, `orders` — nechta buyurtmada.

### `cohorts` — takroriy xarid kogortalari

```json
"cohorts": {
  "offsets": 3,
  "rows": [
    { "month": "2026-07-01", "customers": 1842, "percents": [24.0, 31.0, 36.0] },
    { "month": "2026-08-01", "customers": 2316, "percents": [27.0, 33.0, null] },
    { "month": "2026-09-01", "customers": 2905, "percents": [29.0, null, null] },
    { "month": "2026-10-01", "customers": 2488, "percents": [null, null, null] }
  ]
}
```

Davr filtriga **bog'liq emas**: har doim oxirgi 4 oy (joriy oy ham), eskidan yangiga.

| Maydon | Izoh |
| --- | --- |
| `month` | oyning birinchi kuni |
| `customers` | **birinchi** buyurtmasini shu oyda bergan mijozlar (bekor qilingan buyurtmalar hisobga olinmaydi) |
| `percents[i]` | ulardan nechasi `(i + 1)`-oy oxirigacha yana buyurtma bergan, % — "1-oy", "2-oy", "3-oy" ustunlari. Qiymat yig'ilib boradi (`1-oy ≤ 2-oy ≤ 3-oy`) |
| `null` | o'sha oy hali boshlanmagan — katakda "–" |

Misol: iyul kogortasining "2-oy" katagi — birinchi buyurtmasi iyulda bo'lgan mijozlardan sentabr oxirigacha ikkinchi buyurtma
berganlari. Joriy oyga to'g'ri kelgan katak (avgust kogortasining "2-oy"i oktabrda) oy tugaguncha o'sib boradi.

---

## Dizaynda bor, API'da yo'q

| Dizayndagi element | Sabab |
| --- | --- |
| "Kanallar" (Sayt / iOS / Android) | buyurtmada kanal saqlanmaydi |
| "Qaytarish" — tovarni qaytarish, qaytarish sababi | tovar qaytarish modeli yo'q. O'rniga **pul qaytarilgan** buyurtmalar (`payment_status=3`): `refund_rate`, `refunded_products`; sabab saqlanmaydi |
| To'lov usullari: "Onlayn · Atmos", "Omborda", "Pul ko'chirish" | bunday to'lov turlari yo'q — haqiqiylari: `click`, `payme`, `uzum`, `cash`, `card` |
| Yuqoridagi boshqa filtrlar (kanal, kategoriya va h.k.) | faqat davr filtri bor |
