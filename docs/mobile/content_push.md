# Yangi maqola / video push'i — mobile uchun

Admin panelda yangi **maqola** yoki **video** qo'shilganda backend:

1. hammaga ko'rinadigan bildirishnoma yaratadi (ilovadagi bildirishnomalar ro'yxatiga tushadi — `GET /api/v1/base/notifications/`);
2. bitta **FCM topic**'ga push yuboradi — **`buildex_content`**.

Topic nomi statik, o'zgarmaydi. Push faqat shu topic'ga obuna bo'lgan qurilmalarga boradi, shuning uchun **obunani ilova o'zi qiladi** (backendga hech narsa yuborilmaydi, yangi endpoint yo'q).

---

## Ilovada qilinadigan ishlar

1. **Topic'ga obuna** — har ishga tushganda (login bo'lmagan mehmon ham), push ruxsati so'ralgandan keyin:

   ```dart
   await FirebaseMessaging.instance.subscribeToTopic("buildex_content");
   ```

   ```swift
   Messaging.messaging().subscribe(toTopic: "buildex_content")
   ```

   ```kotlin
   Firebase.messaging.subscribeToTopic("buildex_content")
   ```

   Qayta chaqirish xavfsiz (obuna takrorlanmaydi). Logout'da obunani **bekor qilmang** — mehmon ham bu push'larni oladi. Agar sozlamalarda "Yangi maqolalar / videolar" o'chirgichi qilinsa — o'chirilganda `unsubscribeFromTopic("buildex_content")`, yoqilganda yana `subscribeToTopic`.

2. **Ikki yangi deeplink**ni ochish:

   | Deeplink | Ekran | Ma'lumot olish |
   | --- | --- | --- |
   | `buildex://article/<id>` | maqola | `GET /api/v1/base/articles/<id>/` |
   | `buildex://video/<id>` | video | `GET /api/v1/base/video/<id>/` |

   Maqola / video o'chirilgan bo'lishi mumkin (push allaqachon ketgan bo'lsa) — unda detail `404` (`"error_code": 4`) qaytaradi, "Topilmadi" ko'rsating.

3. **Bildirishnomalar ro'yxatida** yangi `link_type` qiymatlari: `article`, `video` (quyida).

4. Push bosilganda: login bo'lgan bo'lsa `GET /api/v1/base/notifications/{notification_id}/` ni chaqiring (o'qilgan bo'ladi, `unread-count` kamayadi), keyin deeplink'ni oching. Mehmon bo'lsa — faqat deeplink'ni oching (bildirishnomalar API token talab qiladi).

---

## Push tarkibi

`notification` (tizim ko'rsatadigan qism) — **ruscha** (mijoz tili backendda saqlanmaydi, topic bitta):

| | Maqola | Video |
| --- | --- | --- |
| `title` | maqola sarlavhasi (150 belgigacha qisqartiriladi) | `Новое видео` |
| `body` | maqolaning qisqa tavsifi (`short_description`, 200 belgigacha) | video nomi (ruscha, bo'lmasa o'zbekcha) |

`data` (barcha qiymatlar **string**) — oddiy bildirishnomalardagi bilan bir xil kalitlar:

```json
{
  "type": "notification",
  "notification_id": "41",
  "deeplink": "buildex://article/12",
  "link_type": "article",
  "target_model": "articles",
  "target_id": "12",
  "page": ""
}
```

Video uchun: `"deeplink": "buildex://video/5"`, `"link_type": "video"`, `"target_model": "video"`, `"target_id": "5"`.

| Kalit | Izoh |
| --- | --- |
| `type` | har doim `notification` (buyurtma statusi push'i — `order_status`) |
| `notification_id` | bildirishnoma id'si → `GET notifications/{id}/` |
| `deeplink` | ochiladigan ekran |
| `link_type` | `article` yoki `video` |
| `target_model` | `articles` yoki `video` |
| `target_id` | maqola / video id'si |
| `page` | har doim bo'sh |

---

## Bildirishnomalar ro'yxatida

`GET /api/v1/base/notifications/` elementida (token kerak):

```json
{
  "id": 41,
  "title": "Buildex Go: стройматериалы и инструменты теперь в вашем телефоне",
  "description": "Скачайте приложение и заказывайте в два клика.",
  "image": null,
  "deeplink": "buildex://article/12",
  "link_type": "article",
  "page": "",
  "content_type_info": {"model": "articles", "id": 12},
  "is_read": false,
  "publish_at": "2026-10-23T12:00:00"
}
```

- Video: `"link_type": "video"`, `"content_type_info": {"model": "video", "id": 5}`, `title` — `Accept-Language` bo'yicha `Yangi video` / `Новое видео`, `description` — video nomi.
- Maqola tarjima qilinmaydi — ikkala tilda ham bir xil matn.
- Maqola / video o'chirilsa, uning bildirishnomasi ham ro'yxatdan o'chadi.

---

## Qachon keladi

- Maqola / video yaratilganda darhol. **22:00–09:00** (Toshkent vaqti) oralig'ida yaratilsa — ertalab **09:00** da (ro'yxatda ham shu paytdan chiqadi).
- Har bir maqola / video uchun **bir marta**; tahrirlash qayta push yubormaydi.
- Admin yaratishda push'ni o'chirib qo'yishi mumkin — unda bildirishnoma ham bo'lmaydi.
- Ilovaning obunani qo'shmagan eski versiyalariga push **kelmaydi**, lekin bildirishnoma ro'yxatda ko'rinadi.
- Push yetib borishi kafolatlanmaydi — ro'yxat va `unread-count` har doim API'dan olinadi.
