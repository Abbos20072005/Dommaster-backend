# Auth: telefon + OTP (SMS / Telegram) — mobile uchun

Base URL: `{{host}}/api/v1/auth/`
Hamma endpointlar ochiq (token kerak emas), `Content-Type: application/json`.

## Umumiy flow

```
1. POST auth/phone/        → otp_key (SMS ketdi)
2. POST otp/verify/        → access_token + refresh_token   ✅

   SMS kelmasa:
   a) POST otp/resend/     → yangi otp_key (yana SMS)
   b) POST otp/telegram/   → yangi otp_key (kod Telegram botga keladi)
   → keyin baribir 2-qadam: otp/verify/ YANGI otp_key bilan
```

> **Asosiy qoida:** har doim **oxirgi olingan `otp_key`**ni saqlang. `resend` va `telegram` har safar **yangi** `otp_key` qaytaradi — eskisi bilan verify / resend / telegram ishlamaydi (`error_code: 11`).

---

## Javob formati

Muvaffaqiyatli:
```json
{ "result": { ... }, "ok": true }
```

Xato (HTTP 400 / 401 / 503):
```json
{
  "detail": "incorrect otp_code",
  "ok": false,
  "result": "",
  "error_code": 12,
  "return_time": 42.37
}
```
- `error_code` — shunga qarab UI logika qiling (`detail` matni o'zgarishi mumkin).
- `error_code: 5` (validation) bo'lsa `detail` — maydonlar bo'yicha obyekt: `{"phone_number": ["..."]}`.
- `return_time` — faqat ba'zi xatolarda keladi (pastda har endpointda yozilgan), 2 xil ko'rinishda:
  - **son (sekund)** — `error_code 16`: shuncha sekunddan keyin qayta so'rash mumkin → timer.
  - **sana-vaqt string** (`"2026-09-28T21:15:03.123456"`, Toshkent vaqti, timezone'siz) — `error_code 10, 31`: shu vaqtgacha limit.

---

## 1. Telefon bilan kirish / ro'yxatdan o'tish

`POST auth/phone/`

```json
{
  "phone_number": "998901234567",
  "role": "user",
  "device_id": "a1b2c3..."
}
```

| Maydon | Majburiy | Izoh |
|---|---|---|
| `phone_number` | ha | O'zbek raqami, 12 raqam `998XXXXXXXXX`. `+`, probel, `-`, qavslar ruxsat: `+998 (90) 123-45-67` ham bo'ladi |
| `role` | yo'q | `user` (default) yoki `prorab`. **Faqat yangi user yaratilganda** qo'llanadi |
| `device_id` | yo'q | Qurilma ID. Login'dan keyin baribir `PATCH fcm/token/` bilan FCM token yuboring |

Javob `200`:
```json
{
  "result": {
    "otp_key": "3f6c1a0e-8b2d-4c1e-9a55-0f5e2b7d9c11",
    "is_new": true,
    "telegram_linked": false
  },
  "ok": true
}
```
- `otp_key` — saqlab qo'ying, verify'da kerak.
- `is_new` — `true` bo'lsa yangi user (masalan, verify'dan keyin ism kiritish ekraniga o'tkazish uchun: `PATCH customer/update/`).
- `telegram_linked` — raqam Telegram botga ulangan bo'lsa `true`. Bunda "Telegram orqali olish" tugmasi bosilganda kod darhol botga keladi (deep link kerak emas).

SMS'ga **5 xonali** kod keladi.

Xatolar:
| `error_code` | Qachon | Nima qilish |
|---|---|---|
| 5 | Raqam formati noto'g'ri | Inputda xato ko'rsatish |
| 10 | 12 soat ichida 3 ta SMS limiti tugagan. `return_time` — datetime | "Keyinroq urinib ko'ring". Bu holatda `otp_key` qaytmaydi, shuning uchun Telegram variantini ham ishlatib bo'lmaydi |

---

## 2. Kodni tasdiqlash (login)

`POST otp/verify/`

```json
{
  "otp_key": "3f6c1a0e-8b2d-4c1e-9a55-0f5e2b7d9c11",
  "otp_code": 12345
}
```

`otp_code` son (`12345`) yoki string (`"12345"`) bo'lishi mumkin.

Javob `200`:
```json
{
  "result": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi..."
  },
  "ok": true
}
```
Keyingi so'rovlarda: `Authorization: Bearer <access_token>`.
Muvaffaqiyatdan keyin userning barcha OTP'lari o'chadi (eski `otp_key`lar endi ishlamaydi).

Kodning amal qilish muddati: ~**2 daqiqa** (SMS yuborilgan / Telegramga yetkazilgan paytdan).

Xatolar:
| `error_code` | Qachon | Nima qilish |
|---|---|---|
| 5 | `otp_key` UUID emas yoki `otp_code` son emas | — |
| 11 | `otp_key` topilmadi (eskirgan, allaqachon ishlatilgan) | Boshidan `auth/phone/` |
| 12 | Kod noto'g'ri | "Kod noto'g'ri" |
| 13 | Kod muddati o'tgan | Resend / Telegram taklif qilish |
| 14 | Bitta kod uchun 3 ta urinish tugagan (4-urinishdan boshlab, kod to'g'ri bo'lsa ham) | Resend / Telegram — yangi kodda urinishlar yana 3 ta |
| 9 | User bloklangan | "Admin bilan bog'laning" |

---

## 3. SMS'ni qayta yuborish

`POST otp/resend/`

```json
{ "otp_key": "<oxirgi otp_key>" }
```

Javob `200`:
```json
{ "result": { "otp_key": "9d2e...-yangi" }, "ok": true }
```
→ **yangi `otp_key`ni saqlang**, verify shu bilan.

Qoidalar:
- Oxirgi OTP'dan keyin **1 daqiqa** o'tgach ruxsat → ekranda 60 sekund timer qiling.
- 12 soatda jami **3 ta SMS** (`auth/phone/` dagi birinchisi ham hisobga kiradi → ya'ni 2 marta resend). Telegram kodlari bu limitga kirmaydi.

Xatolar:
| `error_code` | Qachon | Nima qilish |
|---|---|---|
| 2 | `otp_key` yuborilmagan | — |
| 15 | Bunday `otp_key` yo'q | Boshidan `auth/phone/` |
| 11 | `otp_key` oxirgisi emas | Oxirgi key bilan yuboring |
| 16 | 1 daqiqa hali o'tmagan. `return_time` — **sekund** | Timer'ni `return_time` bilan yangilash |
| 10 | SMS limiti (3/12 soat). `return_time` — datetime | Telegram variantini taklif qilish |

---

## 4. Telegram orqali kod olish ("Kod kelmadi")

`POST otp/telegram/`

```json
{ "otp_key": "<oxirgi otp_key>" }
```

Javob `200` — 2 xil holat:

**a) Raqam Telegramga ulangan** (`linked: true`) — kod allaqachon botga yuborildi:
```json
{
  "result": {
    "otp_key": "c71a...-yangi",
    "linked": true,
    "deep_link": null,
    "link_token": null,
    "expires_in": null
  },
  "ok": true
}
```
→ "Kod Telegramga yuborildi" deb ko'rsating, yangi `otp_key` bilan `otp/verify/`.

**b) Ulanmagan** (`linked: false`) — user botni ochib, raqamini tasdiqlashi kerak:
```json
{
  "result": {
    "otp_key": "c71a...-yangi",
    "linked": false,
    "deep_link": "https://t.me/BuildexGoBot?start=Xy9...",
    "link_token": "Xy9...",
    "expires_in": 600
  },
  "ok": true
}
```
Mobile nima qiladi:
1. Yangi `otp_key`ni saqlaydi.
2. `deep_link`ni **tashqi ilovada** ochadi (Telegram app; Flutter'da `launchUrl(uri, mode: LaunchMode.externalApplication)`).
3. Kod kiritish ekranida qoladi (polling kerak emas).

Telegramda user tomonidan:
1. Bot ochiladi → **Start** bosadi.
2. Bot "📱 Raqamni yuborish" tugmasini chiqaradi → user bosadi (o'z kontaktini ulashadi).
3. Raqam ilovada kiritilgan raqamga mos kelsa → bot **kodni yuboradi**. Mos kelmasa bot xato yozadi.
4. User ilovaga qaytib, kodni kiritadi → `otp/verify/`.

Eslatmalar:
- `deep_link` `expires_in` sekund (default 10 daqiqa) amal qiladi. Muddati o'tsa bot "havola eskirgan" deydi → "Kod kelmadi"ni qayta bosish kerak.
- Kodning 2 daqiqalik muddati kod **botga yetkazilgan paytdan** boshlanadi (user botni ochishga ulgursin).
- Bir marta ulangandan keyin keyingi safar (`telegram_linked: true`) kod darhol botga keladi.
- Telegram tugmasini SMS timer'ini kutmasdan darhol ko'rsatish mumkin.
- Deep link olgandan keyin user SMS resend qilsa ham muammo yo'q: bot doim **oxirgi** OTP kodini yuboradi — ilovadagi oxirgi `otp_key` bilan verify qilinadi.

Limitlar: Telegram kodlari o'rtasida **1 daqiqa**, 12 soatda **10 ta** (SMS limitidan alohida).

Xatolar:
| `error_code` | HTTP | Qachon | Nima qilish |
|---|---|---|---|
| 5 | 400 | `otp_key` UUID emas | — |
| 11 | 400 | `otp_key` topilmadi yoki oxirgisi emas | Oxirgi key bilan / boshidan |
| 16 | 400 | 1 daqiqa o'tmagan. `return_time` — **sekund** | Timer |
| 31 | 400 | Telegram limiti (10/12 soat). `return_time` — datetime | "Keyinroq urinib ko'ring" |
| 32 | 503 | Telegram bot ishlamayapti | SMS resend taklif qilish |

---

## Qo'shimcha endpointlar

### Token yangilash
`POST token/refresh/`
```json
{ "refresh": "<refresh_token>" }
```
Javob (⚠️ `result` ichida emas):
```json
{ "access_token": "...", "refresh_token": "...", "ok": true }
```
Refresh token rotatsiya qilinadi — **yangi `refresh_token`ni ham saqlang**, eskisi ishlamay qoladi. `error_code 22` (HTTP 401) → logout, `auth/phone/` dan boshlash.
Muddatlar (default): access — 1 kun, refresh — 2 kun.

### Telegram ulanishi (profil sozlamalari uchun, token kerak)
- `GET telegram/link/` → `{"result": {"linked": true, "username": "...", "first_name": "...", "linked_at": "..."}, "ok": true}`
- `DELETE telegram/link/` → Telegramni raqamdan uzish. Ulanmagan bo'lsa `error_code 33` (404).

---

## Tavsiya etilgan UI (kod kiritish ekrani)

```
[ _ _ _ _ _ ]              ← 5 xonali kod, raqamli klaviatura

Qayta yuborish: 0:59       ← timer tugagach "SMS qayta yuborish" → otp/resend/
[ Kod kelmadimi? Telegram orqali olish ]   ← otp/telegram/
```
- `error_code 16` kelsa timer'ni `return_time` sekundga qo'ying.
- `error_code 10` (SMS limiti) kelsa SMS tugmasini o'chirib, Telegram tugmasini ko'rsating.
- `error_code 11` / `15` kelsa — telefon kiritish ekraniga qaytaring.
