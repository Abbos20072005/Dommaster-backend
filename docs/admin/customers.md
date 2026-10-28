# Mijozlar — admin panel

Hammasi `/api/v1/admin/customers/` ostida, admin token bilan. Sana / vaqt — ISO 8601 (Toshkent vaqti).
PRO berish / olish: [pro_customers.md](pro_customers.md) (`POST customers/<id>/role/`, o'zgarmagan).

## 1. Ro'yxat va mijoz: maydonlar

`GET customers/`, `GET customers/<id>/` (detail'da `addresses` ham), `PATCH customers/<id>/`.

| Maydon | Tur | Izoh |
|---|---|---|
| `phone_number` | string | **Maskalangan**: `+998 90 *** ** 67`. To'liq raqam — `POST reveal-phone/` (5-bo'lim). `PATCH` da to'liq raqam yuboriladi |
| `registration_channel` | `site` / `ios` / `android` / `null` | Ro'yxatdan o'tish kanali. `null` = noma'lum (eski mijozlar, `platform` yubormaydigan ilova versiyasi). Faqat o'qish |
| `last_login` | datetime / null | Oxirgi kirish |
| `last_login_platform` | `site` / `ios` / `android` / `null` | Oxirgi kirish platformasi (OTP tasdiqlanganda yoziladi). Faqat o'qish |
| `active_devices` | int | Push token'i bor qurilmalar soni |
| `orders_count` | int | **Yakunlangan** (status 3) buyurtmalar |
| `total_purchase` | number | Yakunlangan buyurtmalar summasi |
| `last_order_at` | datetime / null | Oxirgi buyurtma (har qanday status) |
| `returns_count` | int | **Bekor qilingan** (status 4) buyurtmalar — hozircha qaytarish modeli yo'q, "Qaytarishlar" shuni ko'rsatadi |
| `segment` | `regular` / `big` / `vip` / `null` | Qo'lda belgilanadi (`PATCH`), hech narsa hisoblamaydi |
| `tags` | string[] | Qo'lda (`PATCH`): ≤ 20 ta, har biri ≤ 50 belgi; probellar kesiladi, takrorlar (katta-kichik harf farqsiz) tashlanadi |
| `language` | `uz` / `ru` | Ilova / sayt so'rovlaridagi til (kuniga bir marta yangilanadi). `PATCH` qabul qiladi, lekin mijoz ilovadan boshqa tilda kirsa, keyingi kun o'sha til yoziladi. `en` yo'q |
| `email` | string / null | `PATCH` qabul qiladi (email formati tekshiriladi) |
| `is_deleted`, `deleted_at` | bool, datetime / null | O'chirilgan mijoz (6-bo'lim). Faqat o'qish |
| `role`, `verified`, `is_blocked`, `avatar`, `created_at`, `updated_at` | | Avvalgidek |

`PATCH customers/<id>/` qabul qiladi: `full_name`, `phone_number`, `email`, `verified`, `is_blocked`, `segment`,
`tags`, `language`. `role` — faqat `POST role/`. `segment: null` — segmentni olib tashlaydi.

Manzil (`addresses[]`): `recipient_name`, `recipient_phone` qo'shildi (`""` = mijozning o'zi — u holda mijoz ismi /
telefonini ko'rsating). Ularni mijoz ilovada to'ldiradi.

## 2. Filtrlar, qidiruv, tartib (`GET customers/`)

| Parametr | Izoh |
|---|---|
| `registration_channel` | `site`, `ios`, `android`. Bir nechtasi: `?registration_channel=ios&registration_channel=android` yoki `?registration_channel=ios,android` ("Ilova"). Noma'lum qiymat → 400 |
| `segment` | `regular` / `big` / `vip` |
| `tag` | shu tegi bor mijozlar (aniq moslik) |
| `orders_min`, `orders_max` | `orders_count` oralig'i |
| `purchase_min`, `purchase_max` | `total_purchase` oralig'i |
| `last_order_from`, `last_order_to` | `YYYY-MM-DD`, oxirgi buyurtma sanasi |
| `has_returns` | `true` / `false` — bekor qilingan buyurtmasi bor / yo'q |
| `is_deleted` | `true` = "O'chirilgan" tab. **Yuborilmasa o'chirilganlar ro'yxatda chiqmaydi** |
| `role`, `verified`, `is_blocked`, `is_active`, `has_orders`, `from_created`, `to_created` | Avvalgidek |

`search`: ism, telefon, email. Faqat raqamlar (probel, `+`, `-`, qavslar e'tiborsiz) → telefonning bir qismi
**yoki** buyurtma raqami. `#28598` / `№28598` → faqat buyurtma raqami (shu buyurtmaning egasi).

`ordering`: `id`, `full_name`, `created_at`, `last_login`, `orders_count`, `total_purchase`, `last_order_at`
(`-` = kamayish). Bo'sh qiymatlar (buyurtmasi yo'q, hech kirmagan) ikkala yo'nalishda ham oxirida.

## 3. `GET customers/stats/`

```json
{ "total": 8120, "active": 1450, "b2b": 37, "blocked": 4, "ordered_30d": 612, "deleted": 15 }
```

- `ordered_30d` — oxirgi 30 kunda buyurtma bergan mijozlar (har qanday status).
- `deleted` — o'chirilganlar. Qolgan hamma raqamlar (`total` ham) o'chirilganlarni **hisoblamaydi**.
- Ro'yxat filtrlarini hisobga olmaydi. "Yangi (7 kun)" — `GET customers/?from_created=...` ning `count` i.

## 4. Ichki izohlar (mijozga ko'rinmaydi)

- `GET customers/<id>/notes/` — yangilari birinchi, sahifalangan:
  `{ "id": 3, "author": { "id": 2, "username": "aziz", "full_name": "Aziz Karimov" }, "text": "...", "created_at": "..." }`
  (`author` — `null`, agar xodim o'chirilgan bo'lsa).
- `POST customers/<id>/notes/` — `{ "text": "..." }` → `201` + izoh. Bo'sh matn → 400.
- `DELETE customers/<id>/notes/<note_id>/` → `204`. Faqat muallif yoki super admin (boshqasi → 403).

## 5. Telefon, qurilmalar, jurnal

- `POST customers/<id>/reveal-phone/` (body yo'q) → `{ "phone_number": "+998901234567" }`. Har bir chaqiruv
  jurnalga yoziladi (kim, qachon).
- `POST customers/<id>/logout-all/` (body yo'q) → `204`. Shu paytgacha berilgan hamma access / refresh tokenlar
  ishlamay qoladi, push tokenlar o'chadi (`active_devices` = 0). Mijoz qayta SMS kod bilan kiradi.
- `GET customers/<id>/activity/` — jurnal, yangilari birinchi, sahifalangan:

  ```json
  {
    "id": 41, "kind": "blocked", "text": "Bloklandi", "channel": "admin",
    "actor": { "id": 2, "username": "aziz", "full_name": "Aziz Karimov" },
    "data": {}, "created_at": "2026-10-28T10:15:00"
  }
  ```

  `channel`: `ios` / `android` / `site` (mijozning o'zi), `admin` (xodim; `actor` to'ldirilgan), `null` (mijoz,
  platforma noma'lum). `text` — tayyor o'zbekcha qator; o'z matningiz kerak bo'lsa `kind` bo'yicha quring:

  | `kind` | `text` | `data` |
  |---|---|---|
  | `registered` | Hisob yaratildi, telefon SMS / Telegram kod bilan tasdiqlandi | `otp_channel` |
  | `logged_in` | Hisobga kirildi | |
  | `updated` | Profil o'zgartirildi: segment, teglar | `fields` (o'zgargan maydonlar) |
  | `blocked` / `unblocked` | Bloklandi / Blokdan chiqarildi | |
  | `role_changed` | PRO berildi / PRO bekor qilindi (sabab) | `old_value`, `new_value`, `reason` |
  | `phone_revealed` | Telefon ko'rsatildi | |
  | `logged_out_all` | Barcha qurilmalardan chiqarildi | |
  | `deleted` | Hisob o'chirildi | |

  Jurnal deploy paytidan boshlanadi: undan oldingi voqealar yo'q (oldingi rol o'zgarishlari — `role-history/` da).

## 6. O'chirish (soft delete)

`DELETE customers/<id>/` → `204` — endi **bazadan o'chirilmaydi**: `is_deleted = true`, `deleted_at`, tokenlar va
push tokenlar o'chadi, jurnalga yoziladi. Ilovadagi "Akkauntni o'chirish" ham xuddi shunday. Mijoz yozuvi va
buyurtmalari qoladi, `GET customers/<id>/` ishlayveradi, ro'yxatda faqat `?is_deleted=true` bilan chiqadi.
Shu raqam bilan qayta kirilsa — yangi mijoz yaratiladi (eskisi o'chirilgan holda qoladi). Tiklash endpoint'i yo'q.
Allaqachon o'chirilganni qayta `DELETE` → `204`, hech narsa o'zgarmaydi.

## 7. Hozircha yo'q

- **Qaytarishlar** (`/returns/`): qaytarish modeli yo'q. "Qaytarishlar" tabi uchun bekor qilingan buyurtmalarni
  oling: `GET orders/?customer=<id>&status=4` (`returns_count` shu son).
- **Murojaatlar / tiketlar** (`/tickets/`): tiket tizimi yo'q, tab avvalgidek `GET chats/?customer=<id>`.
- **Rozilik** (push / sms / email): saqlanmaydi, maydon qaytmaydi.
- Telefon faqat `customers/` javoblarida maskalanadi: `orders/`, `chats/` va boshqalarda mijoz telefoni to'liq.
