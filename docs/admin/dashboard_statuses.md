# Buyurtma va mahsulot holatlari — admin panel uchun

Dashboard'dagi ikkita pie chart uchun: buyurtmalar status bo'yicha (davr bilan) va mahsulotlar admin holati bo'yicha (hozirgi surat). Javobda faqat kodlar, son va % keladi — status / holat nomlarini panel o'zi qo'yadi (buyurtmalar ro'yxatidagi xarita bilan bir xil).

Base URL: `{{host}}/api/v1/admin/`. Token: `Authorization: Bearer <admin access token>` (faqat admin; tokensiz → `401`).

| Metod | URL | Nima |
| --- | --- | --- |
| GET | `dashboard/order-statuses/` | davrda yaratilgan buyurtmalar har status bo'yicha: son + % |
| GET | `dashboard/product-statuses/` | hamma mahsulotlar `publish_status` va `is_active` bo'yicha: son + % |

Swagger: `/swagger/admin/` → **dashboard**.

---

## 1. Buyurtmalar status bo'yicha

```
GET dashboard/order-statuses/?period=current_month
GET dashboard/order-statuses/?date_from=2026-10-01&date_to=2026-10-15
```

| Parametr | Qiymatlar | Default | Izoh |
| --- | --- | --- | --- |
| `period` | `current_month` / `last_month` / `last_3_months` / `year` | `current_month` | joriy oy (1-sanadan bugungacha) / o'tgan kalendar oy / oxirgi 3 kalendar oy / oxirgi 12 kalendar oy (joriy oy ham kiradi) |
| `date_from`, `date_to` | `YYYY-MM-DD` | — | ixtiyoriy oraliq, ikkalasi birga yuboriladi, `date_to` ham kiradi; yuborilsa `period` hisobga olinmaydi |

Faqat bittasi yuborilsa yoki `date_from > date_to` → `400`.

Buyurtma davrga **yaratilgan sanasi** (`created_at`, Toshkent vaqti) bo'yicha tushadi, status — **hozirgi** statusi. Bekor qilinganlar (`6`) ham alohida bo'lak.

```json
{
  "period": "current_month",
  "date_from": "2026-11-01",
  "date_to": "2026-11-20",
  "total": 4,
  "statuses": [
    {"status": 0, "count": 2, "percent": 50.0},
    {"status": 1, "count": 1, "percent": 25.0},
    {"status": 2, "count": 0, "percent": 0.0},
    {"status": 3, "count": 0, "percent": 0.0},
    {"status": 4, "count": 0, "percent": 0.0},
    {"status": 5, "count": 0, "percent": 0.0},
    {"status": 6, "count": 1, "percent": 25.0}
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `period` | qaysi davr hisoblandi; `custom` = `date_from` + `date_to` yuborilgan |
| `date_from`, `date_to` | hisoblangan oraliq (ikkala chegara ham kiradi) |
| `total` | oraliqda yaratilgan hamma buyurtmalar |
| `statuses` | **har doim 7 ta**, kod tartibida, 0 lilari ham |
| `status` | `0` Tushgan, `1` Tasdiqlangan, `2` Tayyorlash, `3` Yetkazilmoqda, `4` Olib ketishga tayyor, `5` Yakunlandi, `6` Bekor qilingan (`order_status_changes.md`) |
| `percent` | `total` dan ulush, 1 xona kasr; `total = 0` → `0` (yaxlitlash sababli yig'indi 100 dan biroz farq qilishi mumkin) |

**Ro'yxat bilan mosligi:** `total` = `orders/?from_created=<date_from>&to_created=<date_to>` ning `count`, bo'lak = shu filtr + `&status=<status>`. Bo'lakni bosganda shu havolani oching.

## 2. Mahsulotlar admin holati bo'yicha

```
GET dashboard/product-statuses/
```

Parametr yo'q — hozirgi holat (davr filtri yo'q).

```json
{
  "total": 8235,
  "publish_statuses": [
    {"publish_status": "draft", "count": 8234, "percent": 100.0},
    {"publish_status": "review", "count": 0, "percent": 0.0},
    {"publish_status": "published", "count": 1, "percent": 0.0}
  ],
  "activity": [
    {"is_active": true, "count": 7508, "percent": 91.2},
    {"is_active": false, "count": 727, "percent": 8.8}
  ]
}
```

Mahsulotda bir-biriga bog'liq bo'lmagan ikkita holat bor, shuning uchun ikkita ro'yxat (har birining yig'indisi = `total`):

| Ro'yxat | Qiymatlar | Ma'nosi | Ro'yxatdagi filtr |
| --- | --- | --- | --- |
| `publish_statuses` | `draft` Qoralama, `review` Moderatsiyada, `published` Nashr etilgan | mahsulot kartasining moderatsiya holati (`moderation.md`) | `products/?publish_status=<qiymat>` |
| `activity` | `true` Faol, `false` Nofaol | mijozlarga ko'rinadimi (`is_active`; 1C ham o'zgartiradi) | `products/?is_active=<qiymat>` |

`total` = `products/` ning `count` (filtrsiz). Har doim 3 + 2 qator, 0 lilari ham.

> `publish_status` hozircha faqat admin moderatsiyasi uchun — mijozga ko'rinish faqat `is_active` ga bog'liq. Shuning uchun "qoralama" bo'lsa ham mahsulot saytda chiqib turishi mumkin. Qaysi pie chartni ko'rsatish (yoki ikkalasini) — dizayn qarori.

Qoldiq holati (bor / kam / yo'q) bu endpointda yo'q (02.11 qarori).
