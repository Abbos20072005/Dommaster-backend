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
| `days` | `30` | `1`–`365` | `summary` (KPI kartochkalar) — bugunda tugaydigan oyna |
| `date_from`, `date_to` | — | `YYYY-MM-DD`, `date_from <= date_to` | `summary` — ixtiyoriy sana oralig'i (ikkala chegara ham kiradi). Berilsa `days` **e'tiborga olinmaydi** |
| `period` | `week` | `week` (7 kun) / `month` (30 kun) / `quarter` (13 hafta) / `half_year` (26 hafta) / `year` (12 oy) | `delivered_orders`, `received_orders`, `registrations` va `active_users` grafiklari |
| `months` | `6` | `1`–`24` | `revenue` grafigi |
| `low_stock` | `10` | `>= 0` | `catalog` — "kam qoldi" chegarasi |

Qolgan vidjetlar (`recent_orders`, `attention`, `customers`) parametrga bog'liq emas.

Hafta / oy / 3 oy / 6 oy / yil tugmalari:

| Tugma | Grafiklar | KPI kartochkalar (`summary`) |
| --- | --- | --- |
| Hafta | `period=week` — bugun va oldingi 6 kun, nuqta = kun | `days=7` |
| Oy | `period=month` — bugun va oldingi 29 kun, nuqta = kun | `days=30` |
| 3 oy | `period=quarter` — joriy hafta va oldingi 12 ta hafta, nuqta = hafta (13 ta nuqta) | `days=90` |
| 6 oy | `period=half_year` — joriy hafta va oldingi 25 ta hafta, nuqta = hafta (26 ta nuqta) | `days=180` |
| Yil | `period=year` — joriy oy va oldingi 11 ta **kalendar oy**, nuqta = oy (12 ta nuqta) | `days=365` |

`summary` `period` ga **bog'liq emas** — unga `days` yoki `date_from` + `date_to` yuboriladi. `period=year` kalendar oylar bo'yicha (1-sanadan), `days=365` esa aynan 365 kun — shuning uchun yillik grafik jami bilan `summary` biroz farq qilishi mumkin. `quarter` / `half_year` ham shunday: ular **dushanbadan** boshlanadigan to'liq haftalar (oxirgisi — joriy hafta, bugungacha), `days=90` / `days=180` esa aynan kunlar soni.

`date_from` va `date_to` faqat **birga** yuboriladi: bittasi bo'lsa → `400 {"date_to": ["..."]}` (yoki `date_from`), `date_from > date_to` → `400 {"date_to": ["..."]}`, format noto'g'ri → `400 {"date_from": ["..."]}`. Bo'sh qiymat (`?date_from=&date_to=`) — yuborilmagan hisoblanadi. Oraliq uzunligi cheklanmagan, kelajakdagi sana ham qabul qilinadi (o'sha kunlar `0`).

Misollar:

- `GET dashboard/?days=7&period=month&months=12&low_stock=5`
- `GET dashboard/?date_from=2026-09-01&date_to=2026-09-30` — sentabr uchun KPI, `change` — 2-avgust … 31-avgust (oldingi 30 kun) bilan solishtiriladi

---

## Javob

```json
{
  "summary": { ... },
  "delivered_orders": { ... },
  "received_orders": { ... },
  "registrations": { ... },
  "active_users": { ... },
  "recent_orders": [ ... ],
  "attention": { ... },
  "customers": { ... },
  "catalog": { ... },
  "revenue": { ... }
}
```

Umumiy qoidalar:

- Davrlar **kalendar kun** bo'yicha, bugun ham kiradi: `days=30` — bugun va undan oldingi 29 kun. Vaqt — Toshkent vaqti.
- `change` — shu uzunlikdagi **oldingi davrga** nisbatan o'zgarish, foizda (`12.5` = +12.5%, `-8.0` = −8%). Oldingi davr `0` bo'lsa — `null` (foizni hisoblab bo'lmaydi, "—" ko'rsating). Oldingi davr joriy davrdan bevosita oldin turadi: `date_from=2026-09-10&date_to=2026-09-16` (7 kun) → `2026-09-03 … 2026-09-09`.
- Tushum (`revenue`, `average_check`) faqat **yakunlangan** buyurtmalardan (`status=3`) hisoblanadi — `received_orders` bundan mustasno (u barcha tushgan buyurtmalar summasi).
- Grafik nuqtalari (`points`, `months`) bo'sh kunlar/oylar bilan to'liq keladi (`0` bilan), eskidan yangiga tartibda.
- Summalar — so'mda, `float`.

### `summary` — KPI kartochkalar

```json
"summary": {
  "days": 30,
  "date_from": "2026-09-09",
  "date_to": "2026-10-08",
  "orders":        { "value": 184.0,       "change": 12.5 },
  "revenue":       { "value": 96450000.0,  "change": -8.0 },
  "average_check": { "value": 612000.0,    "change": 3.1 },
  "new_customers": { "value": 57.0,        "change": null }
}
```

| Maydon | Izoh |
| --- | --- |
| `days` | davr uzunligi, kunlarda: `?days=` yoki `date_from … date_to` oralig'idagi kunlar soni |
| `date_from`, `date_to` | hisoblangan davr chegaralari (ikkalasi ham kiradi). `?days=` bilan so'ralganda ham keladi: `date_to` = bugun |
| `orders` | shu davrda yaratilgan **barcha** buyurtmalar soni (holatidan qat'i nazar) |
| `revenue` | shu davrda yaratilgan yakunlangan buyurtmalar summasi |
| `average_check` | yakunlangan buyurtmalarning o'rtacha summasi |
| `new_customers` | shu davrda ro'yxatdan o'tgan mijozlar soni |

`value` har doim `float` keladi (sonlar ham: `184.0`).

### `delivered_orders` — yetkazilgan buyurtmalar grafigi

```json
"delivered_orders": {
  "period": "week",
  "step": "day",
  "count": 41,
  "revenue": 23800000.0,
  "change": 5.4,
  "count_change": -2.4,
  "points": [
    { "date": "2026-09-26", "count": 6, "revenue": 3400000.0, "average_check": 566666.67 },
    { "date": "2026-09-27", "count": 0, "revenue": 0.0, "average_check": 0.0 }
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `period` | `week` — 7 ta nuqta, `month` — 30 ta nuqta, `quarter` — 13 ta, `half_year` — 26 ta, `year` — 12 ta nuqta |
| `step` | bitta nuqta nima: `day` (`week`, `month`), `week` (`quarter`, `half_year`) yoki `month` (`year`) |
| `count`, `revenue` | davr bo'yicha jami |
| `change` | **tushum**ning oldingi davrga nisbatan o'zgarishi, % (`quarter` — oldingi 13 hafta, `half_year` — oldingi 26 hafta, `year` — oldingi 12 oy) |
| `count_change` | buyurtmalar **soni**ning oldingi davrga nisbatan o'zgarishi, % (oldingi davr `0` → `null`) |
| `points[]` | har bir kun (`step=week` bo'lsa — hafta, `date` = haftaning dushanbasi; `step=month` bo'lsa — oy, `date` = oyning birinchi kuni): `date`, `count`, `revenue`, `average_check` |

Kun buyurtmaning **yaratilgan sanasi** (`created_at`) bo'yicha olinadi, yetkazilgan sanasi bo'yicha emas.

### `received_orders` — tushgan buyurtmalar grafigi

`delivered_orders` bilan **bir xil shakl** (`period`, `step`, `count`, `revenue`, `change`, `count_change`, `points[]`) — o'sha grafik komponentini ishlating. Farqi — qaysi buyurtmalar sanaladi:

| | `delivered_orders` | `received_orders` |
| --- | --- | --- |
| Buyurtmalar | faqat yakunlangan (`status=3`) | **barchasi** — hozirgi holatidan qat'i nazar (kutilmoqda, yig'ilmoqda, yetkazilmoqda, yakunlangan, bekor qilingan, do'konda kutmoqda) |
| `revenue` | yakunlangan buyurtmalar summasi | barcha tushgan buyurtmalar summasi (bekor qilinganlari ham kiradi) |
| `average_check` | yakunlanganlarning o'rtachasi | tushganlarning o'rtachasi |

Kun — buyurtma **tushgan** (yaratilgan) sana. Jami `count` `summary.orders` bilan bir xil qoidada (davrlari mos kelsa — bir xil son: `period=week` ↔ `days=7`, `period=month` ↔ `days=30`).

### `registrations` — ro'yxatdan o'tishlar grafigi

```json
"registrations": {
  "period": "week",
  "step": "day",
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
| `period`, `step` | `delivered_orders` dagi bilan bir xil |
| `days` | davrdagi kunlar soni: `week` → 7, `month` → 30, `quarter` / `half_year` → birinchi haftaning dushanbasidan bugungacha, `year` → 12 oyning birinchi kunidan bugungacha (`?days=` ga bog'liq **emas**) |
| `total` | davrdagi yangi mijozlar |
| `mobile` | FCM tokeni bor mijozlar (ilovada qurilma ro'yxatdan o'tkazgan) |
| `web` | `total - mobile` |
| `mobile_percent`, `web_percent` | ulushlar, % (`total=0` bo'lsa `0.0`) |
| `points[]` | har bir kun (`step=week` — hafta, `step=month` — oy): `date`, `count` |

### `active_users` — faol mijozlar grafigi

Davr ichida **biror amal qilgan** mijozlar (har biri bir marta sanaladi), ikki guruhga bo'lingan: buyurtma berganlar va boshqa amal qilganlar.

```json
"active_users": {
  "period": "month",
  "step": "day",
  "total": 412,
  "buyers": 96,
  "others": 316,
  "total_change": 8.4,
  "buyers_change": -3.0,
  "others_change": 12.1,
  "actions": {
    "orders": 96, "favourites": 58, "cart": 141, "questions": 12,
    "reviews": 9, "chat": 17, "views": 230, "visits": 388
  },
  "guests": 1240,
  "points": [
    { "date": "2026-09-28", "total": 21, "buyers": 4, "others": 17 },
    { "date": "2026-09-29", "total": 0, "buyers": 0, "others": 0 }
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `period`, `step` | `delivered_orders` dagi bilan bir xil (`?period=`) |
| `total` | **jami faol mijozlar** — davrda quyidagi amallardan kamida bittasini qilganlar. `total = buyers + others` |
| `buyers` | davrda **buyurtma bergan** mijozlar (buyurtma holatidan qat'i nazar, bekor qilingani ham) |
| `others` | davrda faol bo'lgan, lekin **buyurtma bermagan** mijozlar (faqat like / savat / savol / sharh / chat / ko'rish / ilovaga kirish) |
| `total_change`, `buyers_change`, `others_change` | oldingi shu uzunlikdagi davrga nisbatan %, oldingi davr `0` → `null` |
| `actions` | har bir amal bo'yicha mijozlar soni (davr bo'yicha). Bir mijoz bir nechta amalda sanaladi — **yig'indisi `total` ga teng emas** |
| `guests` | login qilmagan, mahsulot ochgan / qidirgan qurilmalar soni (`X-Device-Id`). `total` ga **kirmaydi** |
| `points[]` | har bir nuqta: `date`, `total`, `buyers`, `others` (`total = buyers + others`). Nuqta ichida `buyers` — shu kun/hafta/oyda buyurtma berganlar, `others` — shu nuqtada faol bo'lib, shu nuqtada buyurtma bermaganlar |

Nuqtalarning yig'indisi davr `total` iga teng **emas**: bir mijoz bir necha kunda faol bo'lsa, har kunida sanaladi, davr jamisida esa bir marta.

`actions` kalitlari — qaysi amal nimadan olinadi:

| Kalit | Amal | Sana |
| --- | --- | --- |
| `orders` | buyurtma berdi | buyurtma yaratilgan sana |
| `favourites` | sevimlilarga qo'shdi (like) | qo'shilgan sana (keyin o'chirgan bo'lsa — sanalmaydi) |
| `cart` | savatga qo'shdi / sonini o'zgartirdi | savat elementining oxirgi o'zgarishi (o'chirilgani sanalmaydi) |
| `questions` | mahsulotga savol berdi | savol sanasi |
| `reviews` | mahsulotga sharh yozdi | sharh sanasi |
| `chat` | qo'llab-quvvatlash chatiga yozdi | xabar sanasi (operator javoblari sanalmaydi) |
| `views` | mahsulotni ochdi yoki qidirdi | ko'rish / qidiruv sanasi |
| `visits` | ilova / saytga **login bilan kirdi** (token bilan istalgan so'rov — ochib, ko'rib chiqib ketgan bo'lsa ham) yoki login qildi | kun |

Faqat **ro'yxatdan o'tgan** mijozlar sanaladi (login qilmagan mehmonlar — alohida `guests`). Bloklangan mijozlar ham, o'sha davrda faol bo'lgan bo'lsa, sanaladi.

Cheklovlar (tarix uchun):

- `visits` — kunlik tashriflar **shu o'zgarish deploy qilingan kundan** yoziladi. Undan oldingi davr uchun faqat mijozning **oxirgi** login sanasi bor, shuning uchun eski davrlarda `visits` (va `others`) kamroq chiqadi.
- `views` dagi ko'rish / qidiruv tarixi 90 kun saqlanadi (bundan eskisi faqat "yaqinda ko'rilganlar" ro'yxatidagi birinchi ko'rish bo'yicha), shuning uchun `half_year` / `year` ning eski oylarida `views` kamroq.
- `guests` — faqat ilova `X-Device-Id` sarlavhasini yuborgan so'rovlardan (mahsulot ochish / qidirish), ilovani ochib hech narsa qilmagan mehmon sanalmaydi.

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
