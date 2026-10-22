# Do'konlar va olib ketish (pickup) — admin panel uchun

Do'kon = **filial** (`MarketBranch`, `/api/v1/admin/branches/`): alohida do'konlar jadvali yo'q. Olib ketish nuqtasi bo'la oladiganlar — `branch_type` `0` Showroom va `1` Market; `2` Warehouse (ombor) sayt / ilovadagi do'konlar ro'yxatiga chiqmaydi va checkout'da tanlanmaydi.
Token: admin JWT (`Authorization: Bearer <admin access>`), boshqa token / tokensiz → `401` / `403`.
Swagger: `/swagger/admin/` → **branches**, **orders**.

> **Migratsiyadan keyin bir marta:** `manage.py backfill_branch_address` — migratsiya 0031 `address_uz` / `address_ru` ustunlarini bo'sh qo'shadi, eski yagona `address` esa faqat shu buyruq bilan `address_ru`ga ko'chiriladi. Ishlatilmasa filiallar manzilsiz ko'rinadi. `address_uz` ataylab bo'sh qoladi — bo'sh uz matni ru'ga tushadi, kontent jamoasi qaysi filial tarjima kutayotganini ko'radi. Qayta ishlatish xavfsiz (`--dry-run` bor).

> Filiallarni **1C ham yaratadi va yangilaydi** (`code` = 1C ombor kodi). 1C ombor kartasini qayta yuborganda nomni (`name_uz` va `name_ru` ikkalasini ham ombor nomi bilan), turini va o'zi yuborgan maydonlarni (manzil, koordinata, telefon, `working_hours`, tavsif, `is_active`, `position`) qayta yozadi. `schedule`, `landmark_*`, `address_uz` va rasmni 1C yubormaydi — ular saqlanadi. 1C yuborgan manzil `address_ru`ga tushadi (`address` ustuni ham yoziladi).

---

## Filiallar (do'konlar) CRUD

```
GET    /api/v1/admin/branches/              ro'yxat (pagination: ?page=&page_size=)
POST   /api/v1/admin/branches/              yaratish
GET    /api/v1/admin/branches/<id>/
PATCH  /api/v1/admin/branches/<id>/
DELETE /api/v1/admin/branches/<id>/
POST   /api/v1/admin/branches/reorder/      {"ids": [3, 1, 2]} → position = ro'yxatdagi o'rni (yuborilmaganlar keyin)
```

JSON yoki multipart (`image` fayli bilan; multipart'da `schedule` — JSON string).

| Maydon | Majburiy | Izoh |
| --- | --- | --- |
| `name_uz`, `name_ru` | `name_ru` ha | (`name` — o'qish uchun, ru) |
| `address_uz`, `address_ru` | yo'q | manzil matni, ikki tilda (`address` — o'qish uchun, 1C yozgan qiymat; panel uni yangilamaydi) |
| `landmark_uz`, `landmark_ru` | yo'q | mo'ljal (ориентир), `""` = yo'q |
| `branch_type` | — | `0` Showroom, `1` Market (default), `2` Warehouse |
| `phone_number` | yo'q | telefon (format tekshirilmaydi) |
| `image` | yo'q | bitta rasm; almashtirilsa / tozalansa / filial o'chirilsa eski fayl o'chadi |
| `latitude`, `longitude` | yo'q | yuborilsa — O'zbekiston hududida: kenglik 37.1…45.6, uzunlik 55.9…73.2 |
| `schedule` | yo'q (default: har kuni 09:00–18:00) | 7 kun, pastga qarang |
| `working_hours` | yo'q | eski oddiy matn (eski ilova va 1C uchun); yangi ilova `schedule`ni o'qiydi |
| `is_active` | — | default `true`; `false` = sayt / ilovada ko'rinmaydi, checkout'da tanlab bo'lmaydi |
| `position` | — | default `0`, kichigi oldin |
| `code` | yo'q | 1C ombor kodi (unikal) |
| `is_open_now` | o'qish | jadval bo'yicha hozir (Toshkent vaqti) ochiqmi |
| `orders_count` | o'qish | shu filialdan olib ketish buyurtmalari soni |

### Jadval (`schedule`)

Har doim **7 qator**, `day` `0` dushanba … `6` yakshanba (har kun bir marta, tartibi ixtiyoriy — server saralaydi):

```json
[
  {"day": 0, "is_open": true, "open_time": "09:00", "close_time": "20:00"},
  ...
  {"day": 6, "is_open": false, "open_time": null, "close_time": null}
]
```

- Ochiq kunda `open_time` va `close_time` majburiy, `"HH:MM"` (`"HH:MM:SS"` ham qabul qilinadi, soniya tashlanadi).
- Yopilish ochilishdan **keyin** bo'lishi shart — `20:00 → 09:00` (yarim tundan o'tadigan) jadval saqlanmaydi.
- Yopiq kunda vaqtlar `null` bo'lib saqlanadi.
- Bayram jadvali yo'q (v2).

### Xatolar (`400`)

```json
{"latitude": ["The point is outside Uzbekistan: latitude must be 37.1..45.6."]}
{"schedule": ["Day 0: the closing time must be after the opening time."]}
{"schedule": ["The schedule must have 7 days (day 0 = Monday .. 6 = Sunday)."]}
```

### O'chirish

Buyurtmasi yoki 1C qoldig'i bor filial **o'chirilmaydi** → `400 {"detail": "Branch has orders, deactivate it instead (is_active=false)."}` (qoldiq bo'lsa — `"Branch has product stock, ..."`) — `PATCH {"is_active": false}` qiling. Qolganlari → `204`.

### Filtrlar

`?branch_type=0|1|2`, `?is_active=true|false`, `?has_orders=true|false`, `?search=` (nom, manzil, telefon, kod), `?ordering=position|-created_at|name|...` (default `position, id`).

---

## Buyurtmalar (`/api/v1/admin/orders/`)

Yangi maydonlar:

| Maydon | Ro'yxat | Karta | Izoh |
| --- | --- | --- | --- |
| `pickup_branch` | — | ✅ (yoziladi) | olib ketish filiali hozirgi holatida `{id, name, address, phone_number}`. Yozish: `{"id": 3}` yoki `3` |
| `pickup_store` | ✅ | ✅ | buyurtma paytidagi filial (snapshot): `{id, name_uz, name_ru, address_uz, address_ru, landmark_uz, landmark_ru, phone, latitude, longitude}`; yetkazib berishda `null` |
| `ready_for_pickup_at` | — | ✅ | "Olib ketishga tayyor" bo'lgan vaqt |
| `pickup_deadline` | ✅ | ✅ | tayyor + 2 kun |
| `pickup_expired` | ✅ | ✅ | `true` = hali tayyor holatda va muddat o'tgan (belgi) |
| `pickup_expired_at` | — | ✅ | muddat o'tgani qayd etilgan vaqt (fon vazifasi, pastga qarang) |

- `pickup_store` buyurtma paytidagi **snapshot** — filial keyin tahrirlansa (admin panelda yoki 1C'da) / nofaol qilinsa ham buyurtmada o'zgarmaydi. Kartada boshqa filial tanlansa (`pickup_branch`), snapshot yangi filialdan olinadi; nofaol filialni tanlab bo'lmaydi.
- `delivery_type = 1` da `pickup_branch` majburiy; `delivery_type = 0` ga o'tkazilsa `pickup_branch` tozalanadi.

Filtrlar: `?pickup_branch=<id>`, `?pickup_expired=true|false`, `?status=5`.
`orders/stats/` ga qo'shildi: `ready_for_pickup`, `pickup_expired`.

### "Olib ketishga tayyor" (status `5`)

- Faqat pickup buyurtma va faqat `1` Collecting'dan o'tkaziladi (`PATCH {"status": 5}`), aks holda `400 {"status": [...]}`. Qoldiq `1` da kamaygan bo'ladi.
- `5` ga o'tganda: `ready_for_pickup_at` = hozir, `pickup_deadline` = +2 kun (Toshkent vaqti), mijozga push (buyurtma raqami, do'kon nomi, muddat — shaxsiy ma'lumotsiz).
- Keyin faqat: `3` Completed (olib ketildi) yoki `4` Canceled (qoldiq qaytadi); boshqa status → `400` — yig'ilib do'konda turgan buyurtma faqat berilishi yoki bekor qilinishi mumkin. 1C `PATCH orders/<id>/status/` bu qoidani bilmaydi va `5` ni o'rnata olmaydi, lekin `5` da turgan buyurtmaga "collecting" yuborishi mumkin — bu holda status `1` ga tushadi, **qoldiq esa ikkinchi marta kamaymaydi** (signal buyurtma qaysi statusdan kelganiga qaraydi, `STOCK_TAKEN_STATUSES`).
- `5` holatidagi buyurtmani o'chirib bo'lmaydi (avval bekor qiling).
- Muddat o'tsa avtomatik bekor qilinmaydi: `pickup_expired: true`, "Bugungi ishlar" sahifasida `expired_pickup_orders` qatori, Telegram guruhiga "⏰ Заказ № … не забрали вовремя" xabari (bir marta).

### Telegram

Yangi buyurtma xabarida (caption + Excel) olib ketishda do'kon nomi, manzili (mo'ljal, telefon) va xaritada joylashuvi ko'rinadi — buyurtma paytidagi snapshot'dan.

### Event'lar (Order Flow v2 §8)

`OrderOutboxEvent` jadvaliga yoziladi (`event_type`):

| Event | Qachon | Telegram |
| --- | --- | --- |
| `order.pickup_selected` | buyurtma do'kon bilan yaratilganda / kartada do'kon o'zgarganda | yo'q (`status = recorded`) |
| `order.pickup_ready` | status → `5` (`payload`: `store_id`, `pickup_deadline`) | yo'q (`recorded`) |
| `order.pickup_done` | pickup buyurtma → `3` Completed | yo'q (`recorded`) |
| `order.pickup_expired` | `pickup_deadline` o'tgan, hali `5` (fon vazifasi, har 10 daqiqada) | ha |

Hozircha event'larni o'qiydigan hisobot yo'q — faqat qayd.

Fon vazifasi: `tasks.expire_pickup_orders` (Celery beat, har 10 daqiqa) → `apps/service/pickup.py`. Har buyurtma uchun bir marta ishlaydi (`pickup_expired_at`; status `5` ga o'tganda tozalanadi).
