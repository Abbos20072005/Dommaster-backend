# Dashboard (bosh sahifa) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET dashboard/` | bosh sahifadagi **barcha** vidjetlar bitta javobda |

Swagger: `/swagger/admin/` → **dashboard**.

---

## Query parametrlar

Hammasi ixtiyoriy. Noto'g'ri qiymat → `400 {"<param>": ["..."]}`.

| Parametr | Default | Chegara | Qaysi vidjetga ta'sir qiladi |
| --- | --- | --- | --- |
| `days` | `30` | `1`–`365` | `summary` (KPI kartochkalar) |
| `period` | `week` | `week` (7 kun) / `month` (30 kun) | `delivered_orders` va `registrations` grafiklari |
| `months` | `6` | `1`–`24` | `revenue` grafigi |
| `low_stock` | `10` | `>= 0` | `catalog` — "kam qoldi" chegarasi |

Qolgan vidjetlar (`recent_orders`, `attention`, `customers`) parametrga bog'liq emas.

Misol: `GET dashboard/?days=7&period=month&months=12&low_stock=5`

---

## Javob

```json
{
  "summary": { ... },
  "delivered_orders": { ... },
  "registrations": { ... },
  "recent_orders": [ ... ],
  "attention": { ... },
  "customers": { ... },
  "catalog": { ... },
  "revenue": { ... }
}
```

Umumiy qoidalar:

- Davrlar **kalendar kun** bo'yicha, bugun ham kiradi: `days=30` — bugun va undan oldingi 29 kun. Vaqt — Toshkent vaqti.
- `change` — shu uzunlikdagi **oldingi davrga** nisbatan o'zgarish, foizda (`12.5` = +12.5%, `-8.0` = −8%). Oldingi davr `0` bo'lsa — `null` (foizni hisoblab bo'lmaydi, "—" ko'rsating).
- Tushum (`revenue`, `average_check`) faqat **yakunlangan** buyurtmalardan (`status=3`) hisoblanadi.
- Grafik nuqtalari (`points`, `months`) bo'sh kunlar/oylar bilan to'liq keladi (`0` bilan), eskidan yangiga tartibda.
- Summalar — so'mda, `float`.

### `summary` — KPI kartochkalar

```json
"summary": {
  "days": 30,
  "orders":        { "value": 184.0,       "change": 12.5 },
  "revenue":       { "value": 96450000.0,  "change": -8.0 },
  "average_check": { "value": 612000.0,    "change": 3.1 },
  "new_customers": { "value": 57.0,        "change": null }
}
```

| Maydon | Izoh |
| --- | --- |
| `days` | so'ralgan oyna (`?days=`) |
| `orders` | shu davrda yaratilgan **barcha** buyurtmalar soni (holatidan qat'i nazar) |
| `revenue` | shu davrda yaratilgan yakunlangan buyurtmalar summasi |
| `average_check` | yakunlangan buyurtmalarning o'rtacha summasi |
| `new_customers` | shu davrda ro'yxatdan o'tgan mijozlar soni |

`value` har doim `float` keladi (sonlar ham: `184.0`).

### `delivered_orders` — yetkazilgan buyurtmalar grafigi

```json
"delivered_orders": {
  "period": "week",
  "count": 41,
  "revenue": 23800000.0,
  "change": 5.4,
  "points": [
    { "date": "2026-09-26", "count": 6, "revenue": 3400000.0, "average_check": 566666.67 },
    { "date": "2026-09-27", "count": 0, "revenue": 0.0, "average_check": 0.0 }
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `period` | `week` — 7 ta nuqta, `month` — 30 ta nuqta |
| `count`, `revenue` | davr bo'yicha jami |
| `change` | **tushum**ning oldingi davrga nisbatan o'zgarishi, % |
| `points[]` | har bir kun: `date`, `count`, `revenue`, `average_check` |

Kun buyurtmaning **yaratilgan sanasi** (`created_at`) bo'yicha olinadi, yetkazilgan sanasi bo'yicha emas.

### `registrations` — ro'yxatdan o'tishlar grafigi

```json
"registrations": {
  "days": 7,
  "total": 23,
  "mobile": 15,
  "web": 8,
  "mobile_percent": 65.2,
  "web_percent": 34.8,
  "points": [
    { "date": "2026-09-26", "count": 4 },
    { "date": "2026-09-27", "count": 0 }
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `days` | `period` dan keladi: `week` → 7, `month` → 30 (`?days=` ga bog'liq **emas**) |
| `total` | davrdagi yangi mijozlar |
| `mobile` | FCM tokeni bor mijozlar (ilovada qurilma ro'yxatdan o'tkazgan) |
| `web` | `total - mobile` |
| `mobile_percent`, `web_percent` | ulushlar, % (`total=0` bo'lsa `0.0`) |
| `points[]` | har bir kun: `date`, `count` |

### `recent_orders` — oxirgi buyurtmalar

Oxirgi **5 ta** buyurtma (yangi birinchi). Obyekt `orders/` ro'yxatidagi bilan bir xil:

```json
"recent_orders": [
  {
    "id": 14,
    "customer": { "id": 8, "full_name": "Prorab Usta Sherzod", "phone_number": "+998901234569" },
    "manager": null,
    "status": 0,
    "payment_status": 2,
    "payment_type": 1,
    "payment_method": null,
    "delivery_type": 0,
    "total_price": 365000.0,
    "products_total_price": 335000.0,
    "saved_price": 10000.0,
    "delivery_price": "40000.0000",
    "receiver_name": "Prorab Sherzod",
    "receiver_phone": "+998901234569",
    "items_count": 2,
    "created_at": "2026-09-24T12:29:41.405932",
    "updated_at": "2026-09-24T12:29:41.405932"
  }
]
```

| Maydon | Qiymatlar |
| --- | --- |
| `status` | `0` Kutilmoqda, `1` Yig'ilmoqda, `2` Yetkazilmoqda, `3` Yakunlangan, `4` Bekor qilingan |
| `payment_status` | `0` Kutilmoqda, `1` Hold, `2` To'langan, `3` Bekor qilingan |
| `payment_type` | `1` Click, `2` Payme, `3` Uzum, `4` yetkazilganda (`payment_method`: `cash` / `card`) |
| `delivery_type` | `0` Yetkazib berish, `1` Olib ketish |
| `customer`, `manager` | `null` bo'lishi mumkin |
| `delivery_price` | **string** (decimal), qolgan summalar `float` |

### `attention` — e'tibor talab qiladi

```json
"attention": {
  "total": 12,
  "out_of_stock": 1,
  "out_of_stock_categories": ["Стройматериалы"],
  "stale_pending_orders": 3,
  "pending_hours": 2,
  "unanswered_questions": 7,
  "unanswered_chats": 1,
  "moderation_queue": 0,
  "last_stock_sync": "2026-09-23T11:38:03.134652"
}
```

| Maydon | Izoh |
| --- | --- |
| `total` | pastdagi 5 ta hisoblagich yig'indisi (nishondagi son) |
| `out_of_stock` | faol, lekin qoldig'i `<= 0` mahsulotlar |
| `out_of_stock_categories` | shunday mahsuloti eng ko'p bo'lgan 2 tagacha kategoriya nomi (bo'sh bo'lishi mumkin) |
| `stale_pending_orders` | `pending_hours` soatdan ko'p "Kutilmoqda" holatida turgan buyurtmalar |
| `pending_hours` | chegara, hozir `2` |
| `unanswered_questions` | ko'rinadigan, admin javob bermagan savollar |
| `unanswered_chats` | oxirgi xabari mijozdan bo'lgan chatlar |
| `moderation_queue` | savollarga mijozlar yozgan, hali tasdiqlanmagan (yashirin) javoblar |
| `last_stock_sync` | 1C dan qoldiqlar oxirgi marta kelgan vaqt (`null` — hali kelmagan) |

### `customers` — mijozlar tarkibi

```json
"customers": {
  "total": 1240,
  "individual": 980,
  "b2b": 190,
  "unverified": 70,
  "active": 412,
  "repeat_purchase_percent": 37.5,
  "blocked": 6
}
```

| Maydon | Izoh |
| --- | --- |
| `total` | barcha mijozlar; `individual + b2b + unverified = total` |
| `individual` | tasdiqlangan, oddiy mijoz |
| `b2b` | tasdiqlangan, prorab |
| `unverified` | telefoni tasdiqlanmagan |
| `active` | oxirgi 30 kunda tizimga kirgan |
| `repeat_purchase_percent` | xaridorlar ichida 2+ (bekor qilinmagan) buyurtmasi borlar ulushi, % |
| `blocked` | bloklangan |

`active` va `blocked` boshqa guruhlar bilan kesishadi — yig'indiga qo'shilmaydi.

### `catalog` — katalog holati

```json
"catalog": {
  "total": 48,
  "in_stock": 44,
  "low_stock": 3,
  "out_of_stock": 1,
  "incomplete": 0,
  "inactive": 0,
  "low_stock_threshold": 10
}
```

| Maydon | Izoh |
| --- | --- |
| `total` | **faol** mahsulotlar; `in_stock + low_stock + out_of_stock = total` |
| `in_stock` | qoldiq `> low_stock_threshold` |
| `low_stock` | `0 <` qoldiq `<= low_stock_threshold` |
| `out_of_stock` | qoldiq `<= 0` |
| `incomplete` | rasmi yoki narxi yo'q faol mahsulotlar (yuqoridagilar bilan kesishadi) |
| `inactive` | nofaol mahsulotlar (`total` ga kirmaydi) |
| `low_stock_threshold` | ishlatilgan chegara (`?low_stock=`) |

### `revenue` — tushum, B2B va jismoniy shaxslar

```json
"revenue": {
  "b2b": 41200000.0,
  "individual": 87600000.0,
  "months": [
    { "month": "2026-09-01", "b2b": 7300000.0, "individual": 15100000.0 },
    { "month": "2026-10-01", "b2b": 0.0, "individual": 0.0 }
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `b2b` | prorab mijozlarning yakunlangan buyurtmalari summasi (butun davr) |
| `individual` | qolgan barcha yakunlangan buyurtmalar (mijozsiz buyurtmalar ham shu yerda) |
| `months[]` | oxirgi `months` ta oy (joriy oy ham kiradi): `month` — oyning birinchi kuni |

---

> Javob keshlanmaydi — har so'rovda bazadan hisoblanadi.
