# Bildirishnomalar — mobile / sayt uchun

Bildirishnomalarni admin yaratadi. Ko'pchiligi hammaga ko'rinadi; auditoriyasi tanlangan (masalan faqat PRO mijozlar yoki faqat iOS) bildirishnomani faqat o'sha mijozlar ko'radi — ro'yxat, `unread-count/` va `{id}/` buni o'zi hisobga oladi. O'qilgan / o'qilmagan holati har bir mijoz uchun alohida saqlanadi.

Base URL: `{{host}}/api/v1/base/`
Token kerak: `Authorization: Bearer <access_token>` (tokensiz → `401`). Til: `Accept-Language: uz | ru` (default `ru`, `en` yoki boshqa til → `ru`; tanlangan tilda matn bo'lmasa — ruscha qaytadi).

| Endpoint | Nima uchun |
| --- | --- |
| `GET notifications/` | ro'yxat (paginatsiyali), har birida `is_read` |
| `GET notifications/unread-count/` | o'qilmaganlar soni (qo'ng'iroqcha ustidagi badge) |
| `GET notifications/{id}/` | bitta bildirishnoma; **ochilganda o'qilgan bo'ladi** |
| `POST notifications/read-all/` | hammasini o'qilgan qilish (body yo'q) |

Swagger: `/swagger/` → **Notification**.

---

## Ro'yxat — `GET notifications/`

Query: `?page=1&page_size=10` (default 1 / 10), `?is_read=false` — faqat o'qilmaganlar (`true` — faqat o'qilganlar).

```json
{
  "result": {
    "totalElements": 2,
    "totalPages": 1,
    "size": 10,
    "number": 1,
    "numberOfElements": 2,
    "first": true,
    "last": true,
    "empty": false,
    "content": [
      {
        "id": 7,
        "title": "Knauf kuzgi aksiya",
        "description": "Gipsokarton va qorishmalarga 20% gacha chegirma",
        "image": "https://api.example.uz/media/notification/knauf.jpg",
        "deeplink": "buildex://banner/7",
        "link_type": "banner",
        "page": "",
        "content_type_info": {"model": "banner", "id": 7},
        "is_read": false,
        "publish_at": "2026-09-25T11:00:00"
      },
      {
        "id": 6,
        "title": "Sement narxlari tushdi",
        "description": "Qizilqum M400 va M500 — PRO narxlarda.",
        "image": null,
        "deeplink": "buildex://sub-category/sement",
        "link_type": "category",
        "page": "",
        "content_type_info": {"model": "productsubcategory", "id": 12},
        "is_read": true,
        "publish_at": "2026-09-22T18:30:00"
      }
    ]
  },
  "ok": true
}
```

| Maydon | Izoh |
| --- | --- |
| `title`, `description` | so'ralgan tildagi matn (oddiy text, HTML emas) |
| `image` | rasm (to'liq URL) yoki `null` |
| `link_type` | bosilganda qayerga o'tiladi: `category`, `product`, `badge`, `page`, `banner`; bo'sh string = havola yo'q |
| `content_type_info` | `link_type` = `category` / `product` / `badge` / `banner` uchun obyekt — bannerlardagi bilan bir xil shakl: `model` (`productcategory`, `productsubcategory`, `productitemcategory`, `product`, `productbadge`, `banner`) + `id`; aks holda `null` (obyekt o'chirilgan bo'lsa ham) |
| `page` | `link_type=page` uchun ichki yo'l (`/pro`), aks holda bo'sh |
| `deeplink` | xuddi shu havola bitta satrda (`buildex://sub-category/sement`, `buildex://product/15`, `buildex://page/pro`); `link_type` bo'sh bo'lsa admin yozgan erkin matn yoki bo'sh string |
| `is_read` | joriy mijoz ochganmi |
| `publish_at` | chiqarilgan vaqti — ro'yxatda sana sifatida shu ko'rsatiladi |

Tartib: yangilari birinchi (`publish_at` bo'yicha).

## O'qilmaganlar soni — `GET notifications/unread-count/`

```json
{ "result": { "unread_count": 1 }, "ok": true }
```

## Bitta bildirishnoma — `GET notifications/{id}/`

Ro'yxatdagi bilan bir xil obyekt qaytadi, `is_read` har doim `true` — so'rovning o'zi bildirishnomani o'qilgan qiladi (alohida "mark as read" endpointi yo'q). Topilmasa → `404` (`error_code: 4`).

## Hammasini o'qilgan qilish — `POST notifications/read-all/`

Body yuborilmaydi.

```json
{ "result": { "unread_count": 0 }, "ok": true }
```

---

## Eslatmalar

- Mijoz faqat **ro'yxatdan o'tganidan keyin** chiqarilgan bildirishnomalarni ko'radi — yangi mijozda eski aksiyalar o'qilmagan bo'lib yig'ilib qolmaydi.
- Qoralama va vaqti hali kelmagan (rejalashtirilgan) bildirishnomalar ro'yxatda ham, `{id}/` da ham chiqmaydi (`404`).
- Buyurtma statusi pushlari alohida ishlaydi (`order_status_push.md`) va bu ro'yxatga tushmaydi.

---

## Push (FCM)

Bildirishnoma chiqarilganda backend uning auditoriyasidagi qurilmalarga push yuboradi (token: `PATCH auth/fcm/token/`, `order_status_push.md` dagi kabi). Har bir bildirishnoma uchun bir marta.

**Token bilan birga `platform` yuboring** (`"ios"` yoki `"android"`): `PATCH auth/fcm/token/ {"device_id": "...", "fcm_token": "...", "platform": "ios"}`. Maydon ixtiyoriy, lekin usiz qurilma "faqat iOS" / "faqat Android" bildirishnomalarini olmaydi (push ham, ro'yxatda ham).

`notification` — tizim ko'rsatadigan matn: `title` / `body` = bildirishnomaning **ruscha** sarlavhasi va matni (mijoz tili backendda saqlanmaydi); rasmi bo'lsa — `image` (to'liq https URL). iOS'da rasm chiqishi uchun Notification Service Extension kerak.

`data` (barcha qiymatlar **string**):

```json
{
  "type": "notification",
  "notification_id": "7",
  "deeplink": "buildex://banner/7",
  "link_type": "banner",
  "target_model": "banner",
  "target_id": "7",
  "page": ""
}
```

- `type` — push turi; bu bildirishnomalar uchun har doim `notification` (buyurtma statusi — `order_status`).
- `notification_id` — push bosilganda `GET notifications/{id}/` ni chaqiring: bildirishnoma o'qilgan bo'ladi va matn kerakli tilda qaytadi.
- `link_type`, `target_model`, `target_id`, `page` — ro'yxatdagi `link_type`, `content_type_info.model`, `content_type_info.id`, `page` ning o'zi (bo'lmasa bo'sh string); `deeplink` — xuddi shu havola bitta satrda. Hammasi bo'sh bo'lsa — bildirishnomaning o'zini oching.
- Push kelganda `unread-count/` ni yangilang. Push yetib borishi kafolatlanmaydi — ro'yxat va badge har doim API'dan olinadi.
