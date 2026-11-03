# Top kategoriyalar, brendlar va xaridorlar — admin panel uchun

Dashboard'dagi uchta ro'yxat: eng ko'p sotilgan kategoriyalar, brendlar va eng katta xaridorlar. Hammasi **sotilgan summa (UZS)** bo'yicha kamayish tartibida — dona soni ishlatilmaydi (tovarlar dona / metr / kg da).

Base URL: `{{host}}/api/v1/admin/`. Token: `Authorization: Bearer <admin access token>` (faqat admin; tokensiz → `401`).

| Metod | URL | Nima |
| --- | --- | --- |
| GET | `dashboard/top-sales/` | top 10 kategoriya + top 10 brend, qolganlari «Boshqalar» |
| GET | `dashboard/top-customers/` | top 10 xaridor |

Swagger: `/swagger/admin/` → **dashboard**.

---

## «Sotilgan» qoidasi

Dashboard'dagi **«Umumiy daromad»** kartochkasi bilan bir xil (`dashboard/` → `summary.revenue`):

- faqat **hozir «Yakunlandi» (`5`) statusidagi** buyurtmalar; qolgan hamma statuslar (Tushgan, Tasdiqlangan, Tayyorlash, Yetkazilmoqda, Olib ketishga tayyor) hali sotilgan emas, **Bekor qilingan (`6`) hech qachon** sanalmaydi;
- buyurtma davrga **yaratilgan sanasi** bo'yicha tushadi (Toshkent vaqti, `orders/?from_created=&to_created=` bilan bir xil);
- summa = buyurtmaning `total_price` i (mahsulot chegirmasi va promokoddan keyingi tovarlar + yetkazib berish);
- to'lov statusi qaralmaydi. Pul qaytarish (`payment_status=3`) amalda buyurtmani bekor qilish bilan birga bo'ladi, shuning uchun u ham chiqib ketadi; tovar qaytarish modeli yo'q.

**Kategoriya / brendga taqsimlash:** buyurtmaning `total_price` i uning tovar qatorlariga qator summasi (buyurtma paytidagi narx × miqdor) ulushida bo'linadi (tiyingacha, qoldiq eng katta qoldiqlarga). Yetkazish va promokod ham shu ulushda tushadi — shuning uchun kategoriyalar (yoki brendlar) + «Boshqalar» yig'indisi = shu davrdagi «Umumiy daromad».

## Davr (ikkala endpoint uchun)

```
GET dashboard/top-sales/?period=current_month
GET dashboard/top-customers/?period=all_time
GET dashboard/top-sales/?date_from=2026-10-01&date_to=2026-10-15
```

| Parametr | Qiymatlar | Default | Izoh |
| --- | --- | --- | --- |
| `period` | `current_month` / `last_3_months` / `year` / `all_time` | `current_month` | joriy oy (1-sanadan bugungacha) / oxirgi 3 kalendar oy / oxirgi 12 kalendar oy (joriy oy ham kiradi) / butun tarix |
| `date_from`, `date_to` | `YYYY-MM-DD` | — | ixtiyoriy oraliq, ikkalasi birga; yuborilsa `period` hisobga olinmaydi |

Faqat bittasi yuborilsa, `date_from > date_to` yoki noma'lum `period` → `400`.

Javobning boshi ikkalasida bir xil:

| Maydon | Izoh |
| --- | --- |
| `period` | hisoblangan davr; `custom` = `date_from` + `date_to` yuborilgan |
| `date_from`, `date_to` | hisoblangan oraliq (ikkala chegara ham kiradi). `all_time` da `date_from` = birinchi buyurtma sanasi, buyurtma bo'lmasa `null` |
| `total` | davrda sotilgan summa = «Umumiy daromad» (`dashboard/?date_from=&date_to=` shu sanalar bilan) |
| `orders_count` | sanalgan (yakunlangan) buyurtmalar soni |

## 1. Top kategoriyalar va brendlar

```
GET dashboard/top-sales/?period=current_month
```

```json
{
  "period": "current_month",
  "date_from": "2026-11-01",
  "date_to": "2026-11-20",
  "total": 2050.0,
  "orders_count": 3,
  "categories": {
    "items": [
      {"id": 4, "name": "Sement", "amount": 1560.0, "orders_count": 2, "percent": 76.1},
      {"id": 7, "name": "Bo'yoqlar", "amount": 440.0, "orders_count": 1, "percent": 21.5},
      {"id": null, "name": null, "amount": 50.0, "orders_count": 1, "percent": 2.4}
    ],
    "others": {"count": 0, "amount": 0.0, "orders_count": 0, "percent": 0.0}
  },
  "brands": {
    "items": [
      {"id": 12, "name": "Knauf", "amount": 1560.0, "orders_count": 2, "percent": 76.1}
    ],
    "others": {"count": 0, "amount": 0.0, "orders_count": 0, "percent": 0.0}
  }
}
```

| Maydon | Izoh |
| --- | --- |
| `categories` | mahsulotning **yuqori darajadagi** kategoriyasi bo'yicha (hozirgi kategoriyasi) |
| `brands` | mahsulot brendi bo'yicha |
| `items` | top 10, summa bo'yicha kamayish tartibida |
| `id`, `name` | kategoriya / brend; `id: null` = kategoriyasiz / brendsiz tovarlar (yoki tovarsiz buyurtma) — panel «Kategoriyasiz» / «Brendsiz» deb yozadi |
| `amount` | sotilgan summa, UZS |
| `orders_count` | shu kategoriya / brend tovari bor buyurtmalar soni (bitta buyurtma bir nechta qatorda sanalishi mumkin) |
| `percent` | `total` dan ulush, 1 xona kasr |
| `others` | top 10 dan keyingi hammasi bitta qatorda: `count` = nechta kategoriya / brend birlashdi (`0` = yo'q, qatorni ko'rsatmang), `amount`, `orders_count`, `percent` |

`items` summasi + `others.amount` = `total`.

## 2. Top xaridorlar

```
GET dashboard/top-customers/?period=year
```

```json
{
  "period": "year",
  "date_from": "2025-12-01",
  "date_to": "2026-11-20",
  "total": 4050.0,
  "orders_count": 4,
  "customers": [
    {
      "id": 15,
      "full_name": "Vali",
      "phone_number": "+998 93 *** ** 11",
      "role": "prorab",
      "is_pro": true,
      "is_deleted": false,
      "orders_count": 2,
      "amount": 2900.0,
      "percent": 71.6,
      "last_order_at": "2026-11-10T09:30:00"
    }
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `customers` | top 10, summa bo'yicha kamayish tartibida |
| `id` | mijoz kartasi: `customers/<id>/` |
| `phone_number` | **yashirilgan** (Mijozlar ro'yxatidagi bilan bir xil format); to'liq raqam — kartada `POST customers/<id>/reveal-phone/` |
| `role`, `is_pro` | hozirgi roli: `prorab` = **PRO**, `user` = **B2C** |
| `is_deleted` | mijoz akkauntini o'chirgan (buyurtmalari qoladi) |
| `orders_count`, `amount`, `percent` | davrdagi yakunlangan buyurtmalari, summasi, `total` dan ulushi |
| `last_order_at` | davrdagi oxirgi sanalgan buyurtmasi |

Mehmon xaridlar yo'q — buyurtma faqat tizimga kirgan mijoz nomidan beriladi. Mijozi yo'q buyurtmalar (bo'lsa) `total` ga kiradi, ro'yxatga kirmaydi.
