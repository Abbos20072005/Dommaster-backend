# Bildirishnomalar — mobile / sayt uchun

Bildirishnomalar **umumiy**: admin yaratadi, barcha mijozlar bir xil ro'yxatni ko'radi. O'qilgan / o'qilmagan holati har bir mijoz uchun alohida saqlanadi.

Base URL: `{{host}}/api/v1/base/`
Token kerak: `Authorization: Bearer <access_token>` (tokensiz → `401`). Til: `Accept-Language: uz | ru | en` (default `ru`; tanlangan tilda matn bo'lmasa — ruscha qaytadi).

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
        "deeplink": "buildex://banner/knauf-kuz",
        "is_read": false,
        "publish_at": "2026-09-25T11:00:00"
      },
      {
        "id": 6,
        "title": "Sement narxlari tushdi",
        "description": "Qizilqum M400 va M500 — PRO narxlarda.",
        "deeplink": "buildex://category/sement",
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
| `deeplink` | bosilganda ochiladigan ekran; bo'sh string bo'lishi mumkin |
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
- Bu bildirishnomalar uchun **push (FCM) yuborilmaydi** — yangi bildirishnoma borligini ilova `unread-count/` orqali biladi. Buyurtma statusi pushlari alohida ishlaydi (`order_status_push.md`) va bu ro'yxatga tushmaydi.
