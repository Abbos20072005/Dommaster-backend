# Bildirishnomalar — admin panel uchun

Bildirishnoma ilova / sayt ichidagi ro'yxatda chiqadi va chiqarilgan paytda push (FCM) bo'lib ketadi. Auditoriya tanlanmasa (`segment=all`, `platform=all`) uni barcha mijozlar ko'radi; tanlansa — faqat o'sha auditoriya. Kim ochgani alohida saqlanadi — `reads_count`.

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET notifications/` | ro'yxat (paginatsiyali) |
| `POST notifications/` | yaratish |
| `GET / PUT / PATCH / DELETE notifications/{id}/` | bitta bildirishnoma |
| `GET notifications/stats/` | kartochkalar va tab sonlari |
| `GET notifications/audience/` | forma uchun auditoriya segmentlari va ularning hajmi |

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
  "image": "https://api.example.uz/media/notification/sement.jpg",
  "link_type": "category",
  "target": {"model": "productsubcategory", "id": 12, "name": "Цемент"},
  "page": "",
  "deeplink": "buildex://sub-category/sement",
  "segment": "pro",
  "platform": "ios",
  "publish_at": "2026-09-30T10:00:00",
  "quiet_hours": true,
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
| `image` | ixtiyoriy rasm (pushda va ro'yxatda chiqadi). Fayl yuborilsa so'rov `multipart/form-data` bo'ladi; bo'sh `image=` — rasmni o'chiradi |
| `link_type` | bosilganda qayerga olib boradi: `category`, `product`, `badge`, `page`, `banner`; bo'sh = havolasiz. Quyida — **Deeplink** |
| `target` | `link_type` = `category` / `product` / `badge` / `banner` uchun obyekt: `{"model", "id"}` |
| `page` | `link_type=page` uchun ichki yo'l, `/` bilan boshlanadi (`/pro`) |
| `deeplink` | `link_type` berilsa — backend o'zi yasaydi (yuborilgani e'tiborga olinmaydi); `link_type` bo'sh bo'lsa — erkin matn, 255 belgigacha |
| `segment` | auditoriya: `all` (default), `pro`, `tashkent`, `buyers_30d`, `abandoned_cart`. Quyida — **Auditoriya** |
| `platform` | `all` (default, iOS va Android), `ios`, `android` |
| `publish_at` | mijozlarga qachondan ko'rinadi va push qachon ketadi; yuborilmasa — hozir. Kelajakdagi vaqt = rejalashtirilgan. Toshkent vaqti (UTC+5) |
| `quiet_hours` | default `false`; `true` — 22:00–09:00 oralig'iga tushgan `publish_at` eng yaqin 09:00 ga ko'chiriladi |
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

### Deeplink

| `link_type` | Nima yuboriladi | `target.model` | `deeplink` (backend yasaydi) |
| --- | --- | --- | --- |
| `category` | `target` | `productcategory` / `productsubcategory` / `productitemcategory` | `buildex://category/<slug>`, `buildex://sub-category/<slug>`, `buildex://item-category/<slug>` |
| `product` | `target` | `product` | `buildex://product/<id>` |
| `badge` (Teg) | `target` | `productbadge` | `buildex://badge/<id>` |
| `banner` | `target` | `banner` | `buildex://banner/<id>` |
| `page` (Sahifa) | `page` | — | `buildex://page/pro` (`page="/pro"`) |
| bo'sh | ixtiyoriy `deeplink` | — | yuborilgan matn |

- JSON: `"target": {"model": "product", "id": 15}`; multipart: `target.model=product`, `target.id=15`.
- `link_type` ga mos kelmagan `target` → `400`. `link_type` almashtirilsa, keraksiz maydonlar (`target` / `page`) o'zi tozalanadi.
- "Manzil" ro'yxati uchun mavjud endpointlar: `categories/`, `sub-categories/`, `item-categories/`, `products/`, `product-badges/`, `banners/` (hammasida `?search=`).
- Javobdagi `deeplink` — forma ostidagi ko'rinish (`buildex://category/sement`) uchun; ilova asosan `link_type` + `target` bilan ishlaydi.

### Auditoriya — `GET notifications/audience/`

```json
[
  {"segment": "all", "customers": 41280, "devices": 38110, "devices_ios": 14950, "devices_android": 21800},
  {"segment": "pro", "customers": 3940, "devices": 3602, "devices_ios": 1497, "devices_android": 2010},
  {"segment": "tashkent", "customers": 28610, "devices": 26400, "devices_ios": 11020, "devices_android": 14700},
  {"segment": "buyers_30d", "customers": 9870, "devices": 9105, "devices_ios": 3800, "devices_android": 5100},
  {"segment": "abandoned_cart", "customers": 2315, "devices": 2100, "devices_ios": 890, "devices_android": 1150}
]
```

`customers` — segmentdagi mijozlar soni (ro'yxatdagi "PRO mijozlar · 3 940"); segment ostidagi "1 497 qurilma" — tanlangan platformaga qarab `devices` / `devices_ios` / `devices_android`. Sonlar so'rov paytidagi holat.

| `segment` | UI | Kim kiradi |
| --- | --- | --- |
| `all` | Barcha foydalanuvchilar | bloklanmagan barcha mijozlar |
| `pro` | PRO mijozlar | roli `prorab` |
| `tashkent` | Toshkent shahri | saqlangan manzillaridan biri Toshkent shahri hududida (koordinata bo'yicha; manzili yo'q mijoz kirmaydi) |
| `buyers_30d` | Oxirgi 30 kunda xarid qilganlar | oxirgi 30 kunda bekor qilinmagan buyurtmasi bor |
| `abandoned_cart` | Savatini tashlab ketganlar | savatida mahsulot bor, savat 1 kundan beri o'zgarmagan (30 kundan eski savatlar hisobga olinmaydi) |

- Auditoriya **push ketayotgan paytda** hisoblanadi va o'sha paytdagi mijozlar ro'yxati saqlanadi: bildirishnomani ilova ichidagi ro'yxatda ham faqat ular ko'radi. Rejalashtirilgan bildirishnomada formadagi son va haqiqiy yuborilgan son farq qilishi mumkin.
- `platform` = `ios` / `android`: faqat shu platformadagi qurilmalarga ketadi va ro'yxatda ham faqat shunday qurilmasi bor mijozlar ko'radi. Platformani ilova token bilan birga yuboradi — eski ilova versiyasidagi qurilmalarning platformasi noma'lum, ular faqat `platform=all` da oladi (`devices` > `devices_ios` + `devices_android` bo'lishi shundan).
- Push ketgandan keyin `segment` va `platform` ni o'zgartirib bo'lmaydi (`400`).

### Jim soatlar

`quiet_hours=true` bo'lsa, 22:00–09:00 (Toshkent vaqti) oralig'iga tushgan `publish_at` eng yaqin 09:00 ga ko'chiriladi: 23:30 → ertasi 09:00, 03:00 → shu kuni 09:00. "Hozir yuborish" ham shu qoidaga tushadi — kechasi yaratilgan bildirishnoma `scheduled` bo'lib qaytadi. Javobdagi `publish_at` — ko'chirilgan vaqt.

### Push (FCM)

Bildirishnoma **chiqarilgan** (`published`) bo'lgan paytda auditoriyasidagi qurilmalarga push yuboriladi — alohida endpoint yo'q, `POST` / `PATCH` ning o'zi yetarli.

| Holat | Push |
| --- | --- |
| `POST` — `is_active=true`, `publish_at` yuborilmagan yoki o'tgan | darhol |
| `POST` — qoralama (`is_active=false`) | yuborilmaydi |
| `PATCH {"is_active": true}` — qoralamani chiqarish | darhol |
| rejalashtirilgan (`publish_at` kelajakda) | vaqti kelganda (fon vazifasi har daqiqada tekshiradi, 1 daqiqagacha kechikishi mumkin) |
| push ketgan bildirishnomani tahrirlash / qayta chiqarish | qayta yuborilmaydi |

- Har bir bildirishnoma uchun push **bir marta** ketadi. Matndagi xatoni tuzatsangiz — ro'yxatda yangilanadi, lekin ketgan push o'zgarmaydi.
- Push matni: `title_ru` + `description_ru` (mijoz tili backendda saqlanmaydi). `image` bo'lsa — pushda rasm bilan chiqadi. Bosilganda ilova `link_type` / `target` (yoki `deeplink`) bo'yicha ochadi.
- `push_sent_at` — push yuborila boshlagan vaqt (`null` = hali yuborilmagan). `push_devices` — pushni qabul qilgan qurilmalar soni ("Yetkazildi" ustuni); yuborish fonda ketadi, shuning uchun `POST` javobida `0` bo'ladi — bir ozdan keyin `GET` da haqiqiy son chiqadi.
- Push funksiyasi qo'shilishidan oldin chiqarilgan bildirishnomalarda `push_sent_at = publish_at`, `push_devices = 0` (ularga push ketmagan).

---

## Ro'yxat — `GET notifications/`

- Paginatsiya: `?page=&page_size=` (default 20, max 100)
- Filtrlar: `?status=published|scheduled|draft`, `?is_active=true|false`, `?segment=`, `?platform=`, `?link_type=`, `?from_publish=2026-10-01&to_publish=2026-10-31` (`publish_at` bo'yicha, ikkala chegara ham kiradi)
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
- Ikkinchi xodim tasdig'i ("Tasdiq kutmoqda") yo'q — bildirishnoma saqlanishi bilan chiqadi / rejalashtiriladi.
- "Avtomatik (buyurtma holati)" tabi uchun ma'lumot yo'q: buyurtma statusi pushlari kodda qat'iy yozilgan (`docs/mobile/order_status_push.md`), bazada saqlanmaydi.
- Mijoz faqat ro'yxatdan o'tganidan keyin chiqarilgan bildirishnomalarni ko'radi.
- Pushdagi rasm ishlashi uchun serverda `.env` da `BACKEND_URL` (backendning tashqi manzili) bo'lishi kerak — bo'lmasa push rasmsiz ketadi.
- Chiqarilgan bildirishnomani tahrirlash / o'chirish mumkin; o'chirilsa o'qilganlik yozuvlari ham o'chadi.
- Mijoz tomoni: `docs/mobile/notifications.md`.
