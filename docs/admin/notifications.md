# Bildirishnomalar — admin panel uchun

Bildirishnoma **umumiy**: bitta yozuv barcha mijozlarga ko'rinadi (auditoriya tanlash yo'q). Kim ochgani alohida saqlanadi — `reads_count`.

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET notifications/` | ro'yxat (paginatsiyali) |
| `POST notifications/` | yaratish |
| `GET / PUT / PATCH / DELETE notifications/{id}/` | bitta bildirishnoma |
| `GET notifications/stats/` | kartochkalar va tab sonlari |

Swagger: `/swagger/admin/` → **notifications**.

---

## Obyekt

```json
{
  "id": 6,
  "title": "Цены на цемент снизились",
  "title_uz": "Sement narxlari tushdi",
  "title_ru": "Цены на цемент снизились",
  "title_en": null,
  "description": "Кизилкум М400 и М500 — по PRO ценам.",
  "description_uz": "Qizilqum M400 va M500 — PRO narxlarda.",
  "description_ru": "Кизилкум М400 и М500 — по PRO ценам.",
  "description_en": null,
  "deeplink": "buildex://category/sement",
  "publish_at": "2026-09-30T10:00:00",
  "is_active": true,
  "status": "scheduled",
  "reads_count": 0,
  "push_sent_at": null,
  "push_devices": 0,
  "created_at": "2026-09-28T15:14:26",
  "updated_at": "2026-09-28T15:14:26"
}
```

| Maydon | Izoh |
| --- | --- |
| `title_ru` * | majburiy (asosiy til), 150 belgigacha |
| `title_uz`, `title_en` | ixtiyoriy; bo'sh bo'lsa mijozga ruscha ko'rsatiladi |
| `description_ru` * | majburiy, oddiy matn |
| `description_uz`, `description_en` | ixtiyoriy |
| `deeplink` | ixtiyoriy, 255 belgigacha (`buildex://category/sement`); format tekshirilmaydi |
| `publish_at` | mijozlarga qachondan ko'rinadi; yuborilmasa — hozir. Kelajakdagi vaqt = rejalashtirilgan |
| `is_active` | default `true`; `false` = qoralama (mijozga chiqmaydi) |

Faqat o'qiladi: `id`, `title`, `description` (joriy tildagi qiymat), `status`, `reads_count`, `push_sent_at`, `push_devices`, `created_at`, `updated_at`.

### `status` (saqlanmaydi, hisoblanadi)

| `status` | Shart | UI |
| --- | --- | --- |
| `published` | `is_active=true`, `publish_at` o'tgan | Yuborildi |
| `scheduled` | `is_active=true`, `publish_at` kelajakda | Rejalashtirilgan |
| `draft` | `is_active=false` | Qoralama |

Qoralamani chiqarish: `PATCH {"is_active": true}` — `publish_at` yuborilmasa va eskisi o'tib ketgan bo'lsa, u avtomatik **hozirgi vaqtga** suriladi. Rejalashtirish uchun `publish_at` ni birga yuboring.

`reads_count` — bildirishnomani ochgan mijozlar soni ("Ochildi" ustuni).

### Push (FCM)

Bildirishnoma **chiqarilgan** (`published`) bo'lgan paytda barcha mijozlarning qurilmalariga push yuboriladi — alohida endpoint yo'q, `POST` / `PATCH` ning o'zi yetarli.

| Holat | Push |
| --- | --- |
| `POST` — `is_active=true`, `publish_at` yuborilmagan yoki o'tgan | darhol |
| `POST` — qoralama (`is_active=false`) | yuborilmaydi |
| `PATCH {"is_active": true}` — qoralamani chiqarish | darhol |
| rejalashtirilgan (`publish_at` kelajakda) | vaqti kelganda (fon vazifasi har daqiqada tekshiradi, 1 daqiqagacha kechikishi mumkin) |
| push ketgan bildirishnomani tahrirlash / qayta chiqarish | qayta yuborilmaydi |

- Har bir bildirishnoma uchun push **bir marta** ketadi. Matndagi xatoni tuzatsangiz — ro'yxatda yangilanadi, lekin ketgan push o'zgarmaydi.
- Push matni: `title_ru` + `description_ru` (mijoz tili backendda saqlanmaydi). Bosilganda ilova `deeplink` bo'yicha ochadi.
- `push_sent_at` — push yuborila boshlagan vaqt (`null` = hali yuborilmagan). `push_devices` — pushni qabul qilgan qurilmalar soni ("Yetkazildi" ustuni); yuborish fonda ketadi, shuning uchun `POST` javobida `0` bo'ladi — bir ozdan keyin `GET` da haqiqiy son chiqadi.
- Push funksiyasi qo'shilishidan oldin chiqarilgan bildirishnomalarda `push_sent_at = publish_at`, `push_devices = 0` (ularga push ketmagan).

---

## Ro'yxat — `GET notifications/`

- Paginatsiya: `?page=&page_size=` (default 20, max 100)
- Filtrlar: `?status=published|scheduled|draft`, `?is_active=true|false`, `?from_publish=2026-10-01&to_publish=2026-10-31` (`publish_at` bo'yicha, ikkala chegara ham kiradi)
- Qidiruv: `?search=` (sarlavha va matn uz/ru/en, `deeplink`)
- Tartib: `?ordering=` `id`, `title`, `publish_at`, `is_active`, `reads_count`, `created_at`, `updated_at`; default — `-publish_at`

Tablar: "Kampaniyalar" = `?is_active=true` (yoki `status` bo'yicha), "Qoralamalar" = `?status=draft`.

## Statistika — `GET notifications/stats/`

Ro'yxat filtrlari ta'sir qilmaydi.

```json
{
  "published": 18,
  "scheduled": 1,
  "draft": 2,
  "published_30d": 4,
  "reads_30d": 13270
}
```

| Maydon | Izoh |
| --- | --- |
| `published`, `scheduled`, `draft` | status bo'yicha sonlar (tab counterlari) |
| `published_30d` | oxirgi 30 kunda chiqarilganlar |
| `reads_30d` | oxirgi 30 kundagi ochilishlar soni (mijoz × bildirishnoma) |

---

## Xatolar

Oddiy DRF formati — maydon nomi bo'yicha:

```json
{
  "title_ru": ["Обязательное поле."],
  "description_ru": ["Обязательное поле."]
}
```

## Eslatmalar

- Push qayta yuborilmaydi (xato bo'lsa ham) va ochilgan pushlar hisobi yo'q — faqat `push_devices` (FCM qabul qilgan qurilmalar).
- Auditoriya (PRO mijozlar, oxirgi 30 kunda xarid qilganlar) va ikkinchi xodim tasdig'i ("Tasdiq kutmoqda") yo'q — bildirishnoma hammaga ko'rinadi.
- "Avtomatik (buyurtma holati)" tabi uchun ma'lumot yo'q: buyurtma statusi pushlari kodda qat'iy yozilgan (`docs/mobile/order_status_push.md`), bazada saqlanmaydi.
- Mijoz faqat ro'yxatdan o'tganidan keyin chiqarilgan bildirishnomalarni ko'radi.
- Chiqarilgan bildirishnomani tahrirlash / o'chirish mumkin; o'chirilsa o'qilganlik yozuvlari ham o'chadi.
- Mijoz tomoni: `docs/mobile/notifications.md`.
