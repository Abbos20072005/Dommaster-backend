# Xodimlar (Sozlamalar → Xodimlar) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>`. `staff/*` endpointlari **faqat Super admin** uchun — oddiy xodim tokeni bilan `403`.

| Endpoint | Nima uchun |
| --- | --- |
| `GET staff/` | xodimlar ro'yxati (paginatsiyali) |
| `POST staff/` | yangi xodim (JSON) |
| `GET / PATCH / PUT / DELETE staff/{id}/` | bitta xodim ("Kartani ochish") |
| `POST staff/{id}/reset-password/` | "Parolni tiklash" |
| `POST staff/{id}/block/` | "Bloklash" |
| `POST staff/{id}/unblock/` | "Blokdan chiqarish" |
| `POST auth/change-password/` | xodim o'z parolini almashtiradi (har qanday admin tokeni) |

Swagger: `/swagger/admin/` → **staff**, **auth**.

> Xodim — admin panelga login + parol bilan kiradigan akkaunt. Buyurtmaga biriktiriladigan [menejerlar](managers.md) bilan **bog'lanmagan**.

---

## Obyekt

```json
{
  "id": 12,
  "username": "kamola.e",
  "full_name": "Kamola Ergasheva",
  "position": "Kontent menejer",
  "access_level": "staff",
  "must_change_password": true,
  "status": "active",
  "block_reason": null,
  "failed_login_attempts": 0,
  "last_login": null,
  "created_by": { "id": 1, "username": "admin", "full_name": "Admin" },
  "created_at": "2026-10-08T15:36:29.796326"
}
```

| Maydon | Izoh |
| --- | --- |
| `full_name` * | F.I.Sh, 150 belgigacha |
| `position` | Lavozim, ixtiyoriy (bo'sh satr bo'lishi mumkin) |
| `username` * | Login. Faqat lotin harflari, raqamlar va nuqta; kichik harfga o'tkaziladi; unikal. **Faqat yaratishda** — `PATCH`'da yuborilsa e'tiborga olinmaydi |
| `access_level` | Kirish darajasi: `staff` (Xodim, default) / `super_admin` |
| `password` * | Faqat `POST staff/` da, javobda qaytmaydi. Kamida 8 belgi, faqat raqamdan iborat yoki juda oddiy bo'lmasligi kerak |
| `must_change_password` | "Birinchi kirishda parolni almashtirsin". Yaratishda default `true` |
| `status` | `active` (Faol) / `blocked` (Bloklangan) — faqat o'qiladi, `block/` va `unblock/` orqali o'zgaradi |
| `block_reason` | `null` / `manual` (admin blokladi) / `failed_attempts` (5 ta xato urinish) |
| `failed_login_attempts` | ketma-ket xato parol urinishlari soni ("Bloklangan · 5 ta xato urinish") |
| `created_by` | Yaratgan xodim yoki `null` (tizim orqali yaratilganlar) |

Faqat o'qiladi: `id`, `status`, `block_reason`, `failed_login_attempts`, `last_login`, `created_by`, `created_at`.

Yaratish (`POST staff/` → `201` + obyekt):

```json
{
  "full_name": "Kamola Ergasheva",
  "position": "Kontent menejer",
  "username": "kamola.e",
  "access_level": "staff",
  "password": "Temp-pass-77",
  "must_change_password": true
}
```

"Parol yaratish" tugmasi parolni frontda generatsiya qiladi (backend'da generatsiya faqat `reset-password/` da bor).

O'zgartirish (`PATCH staff/{id}/` — faqat kerakli maydon): `full_name`, `position`, `access_level`, `must_change_password`.

O'chirish: `DELETE staff/{id}/` → `204`. Xodimning buyurtma izohlari qoladi (`author: null`). Odatda o'chirish o'rniga bloklash tavsiya etiladi.

---

## Ro'yxat

`GET staff/?page=&page_size=` (default 20, max 100) — javob oddiy admin paginatsiyasi (`count`, `results`, ...). Sarlavhadagi "Xodimlar 7" = `count`.

- Qidiruv: `?search=` (`full_name`, `username`)
- Filtr: `access_level` (`staff` / `super_admin`), `status` (`active` / `blocked`)
- Tartib: `?ordering=` `id`, `username`, `full_name`, `last_login`, `created_at`; default `id`

"(siz)" belgisi: `id` ni `auth/me/` dagi `id` bilan solishtiring.

---

## Amallar

**Parolni tiklash** — `POST staff/{id}/reset-password/`

```json
{ "password": "Given-pass-55", "must_change_password": true }
```

Ikkala maydon ixtiyoriy: `password` yuborilmasa backend 12 belgili parol generatsiya qiladi, `must_change_password` default `true`. Javob (`200`) — o'rnatilgan parol, **faqat shu yerda bir marta ko'rinadi**:

```json
{ "password": "7U9HyJslthMc", "must_change_password": true }
```

Parol tiklash blokni **ochmaydi** — bloklangan xodim uchun alohida `unblock/` kerak.

**Bloklash** — `POST staff/{id}/block/` (body yo'q) → `200` + obyekt (`status: "blocked"`, `block_reason: "manual"`). Xodimning amaldagi tokenlari darhol ishlamay qoladi (`401`).

**Blokdan chiqarish** — `POST staff/{id}/unblock/` (body yo'q) → `200` + obyekt; xato urinishlar hisoblagichi 0 ga tushadi.

---

## Login va parol

`POST auth/login/` javobidagi `admin` va `GET auth/me/` ga qo'shildi: `full_name`, `position`, `access_level`, `must_change_password`.

- Login harf registriga bog'liq emas (`Kamola.E` = `kamola.e`).
- Ketma-ket **5 ta** xato parol → akkaunt bloklanadi. Muvaffaqiyatli kirish hisoblagichni nolga tushiradi.
- Bloklangan akkaunt bilan kirish → `403 {"detail": "Account is blocked"}` (parol to'g'ri bo'lsa ham). Xato login/parol → `401`.
- `must_change_password: true` bo'lsa, front xodimni parol almashtirish sahifasiga yo'naltiradi. Backend boshqa endpointlarni **bloklamaydi** — bu faqat bayroq.

**O'z parolini almashtirish** — `POST auth/change-password/`

```json
{ "old_password": "Temp-pass-77", "new_password": "New-pass-991" }
```

→ `200` + `auth/me/` dagi obyekt (`must_change_password: false`). Tokenlar o'zgarmaydi, qayta login shart emas.

---

## Xatolar

Oddiy DRF formatida. Matnga emas, HTTP status va maydon nomiga tayaning.

| Holat | HTTP | Body |
| --- | --- | --- |
| Token yo'q / yaroqsiz / xodim bloklangan | 401 | `{"detail": "..."}` |
| Super admin emas | 403 | `{"detail": "..."}` |
| Login band | 400 | `{"username": ["Staff with this login already exists"]}` |
| Loginda ruxsat etilmagan belgi | 400 | `{"username": ["..."]}` |
| Zaif parol | 400 | `{"password": ["...", "..."]}` (`change-password/` da `new_password`) |
| Eski parol noto'g'ri | 400 | `{"old_password": ["Incorrect password"]}` |
| O'z kirish darajasini o'zgartirish | 400 | `{"access_level": ["..."]}` |
| O'zini bloklash / o'chirish | 400 | `["You cannot block your own account"]` |

---

## Eslatmalar

- Kirish darajasi hozircha faqat **Xodimlar** bo'limini cheklaydi: `staff` darajasidagi xodim qolgan barcha admin API'lardan foydalana oladi. Bo'limlar bo'yicha alohida ruxsatlar yo'q.
- O'zini bloklab / o'chirib / darajasini tushirib bo'lmagani uchun tizimda doim kamida bitta faol super admin qoladi.
- Parol tiklangandan keyin xodimning eski tokenlari muddati tugaguncha ishlaydi (JWT); darhol uzish kerak bo'lsa — bloklab, qayta oching.
- Avval `createsuperuser` orqali yaratilgan adminlar ro'yxatda `full_name` = login, `position` bo'sh holda chiqadi — kartadan to'ldiriladi.
