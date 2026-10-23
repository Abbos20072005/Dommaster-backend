# Yangiliklar, maqolalar, videolar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET news/` | yangiliklar ro'yxati (paginatsiyali) |
| `POST news/` | yangilik yaratish (multipart — `image` fayl) |
| `GET / PUT / PATCH / DELETE news/{id}/` | bitta yangilik |
| `GET articles/` | maqolalar ro'yxati (paginatsiyali) |
| `POST articles/` | maqola yaratish |
| `GET / PUT / PATCH / DELETE articles/{id}/` | bitta maqola |
| `GET videos/` | videolar ro'yxati (paginatsiyali) |
| `POST videos/` | video yaratish |
| `GET / PUT / PATCH / DELETE videos/{id}/` | bitta video |

Swagger: `/swagger/admin/` → **news**, **articles**, **videos**.

Uchala ro'yxatda umumiy:

- Paginatsiya: `?page=&page_size=` (default 20, max 100)
- Sana filtri: `?from_created=2026-10-01&to_created=2026-10-31` (`created_at` bo'yicha, ikkala chegara ham kiradi)
- Default tartib: yangilari birinchi (`-id`); teskari tartib uchun `-` qo'yiladi (`?ordering=-created_at`)

---

## Yangiliklar — `news/`

### Obyekt (`GET news/{id}/`, `POST`, `PATCH` javobi)

```json
{
  "id": 5,
  "title": "Открытие нового филиала",
  "title_uz": "Yangi filial ochildi",
  "title_ru": "Открытие нового филиала",
  "description": "<p>Подробности внутри.</p>",
  "description_uz": "<p>Tafsilotlar ichida.</p>",
  "description_ru": "<p>Подробности внутри.</p>",
  "image": "https://.../media/news/filial.png",
  "created_at": "2026-10-02T15:14:26",
  "updated_at": "2026-10-02T15:14:26"
}
```

| Maydon | Izoh |
| --- | --- |
| `title_ru` * | majburiy (asosiy til), 450 belgigacha |
| `title_uz` | ixtiyoriy |
| `description_ru` * | majburiy, HTML (rich text) |
| `description_uz` | ixtiyoriy, HTML |
| `image` * | rasm, yaratishda majburiy (multipart); keyin o'chirib bo'lmaydi, faqat almashtiriladi |

Faqat o'qiladi: `id`, `title`, `description` (joriy tildagi qiymat), `created_at`, `updated_at`.

Rasm almashtirilsa yoki yangilik o'chirilsa — eski fayl diskdan ham o'chiriladi.

Rasm o'zgarmasa `PATCH` ni JSON bilan yuborish mumkin:

```json
{ "title_uz": "Yangi filial ochildi" }
```

### Ro'yxat

`GET news/` — ro'yxatda `description*` maydonlari **kelmaydi** (og'ir HTML), to'liq matn uchun `GET news/{id}/`:

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "next_page": null,
  "previous_page": null,
  "results": [
    {
      "id": 5,
      "title": "Открытие нового филиала",
      "title_uz": "Yangi filial ochildi",
      "title_ru": "Открытие нового филиала",
      "image": "https://.../media/news/filial.png",
      "created_at": "2026-10-02T15:14:26",
      "updated_at": "2026-10-02T15:14:26"
    }
  ]
}
```

- Qidiruv: `?search=` (sarlavha uz/ru)
- Tartib: `?ordering=` `id`, `title`, `created_at`, `updated_at`

---

## Maqolalar — `articles/`

Maqolada tarjima maydonlari **yo'q** — har bir maydon bitta (tilga bog'lanmagan) qiymat.

### Obyekt

```json
{
  "id": 3,
  "title": "Как выбрать смеситель",
  "short_description": "Краткое описание статьи.",
  "description": "<p>Полный текст статьи.</p>",
  "created_at": "2026-10-02T15:14:26",
  "updated_at": "2026-10-02T15:14:26"
}
```

| Maydon | Izoh |
| --- | --- |
| `title` * | majburiy, 450 belgigacha |
| `short_description` * | majburiy, qisqa matn (oddiy text) |
| `description` * | majburiy, HTML (rich text) |
| `send_push` | faqat yaratishda, default `true` — quyida **Mijozlarga xabar**. Javobda qaytmaydi |

Faqat o'qiladi: `id`, `created_at`, `updated_at`. Rasm yo'q — JSON yuboriladi.

### Ro'yxat

`GET articles/` — ro'yxatda `description` **kelmaydi**: `id`, `title`, `short_description`, `created_at`, `updated_at`.

- Qidiruv: `?search=` (`title`, `short_description`)
- Tartib: `?ordering=` `id`, `title`, `created_at`, `updated_at`

---

## Videolar — `videos/`

### Obyekt (ro'yxatda ham shu ko'rinishda)

```json
{
  "id": 2,
  "name": "Как пользоваться Dommaster",
  "name_uz": "Dommaster'dan qanday foydalanish",
  "name_ru": "Как пользоваться Dommaster",
  "url": "https://youtube.com/watch?v=demo",
  "created_at": "2026-10-02T15:14:27",
  "updated_at": "2026-10-02T15:14:27"
}
```

| Maydon | Izoh |
| --- | --- |
| `name_ru` * | majburiy (asosiy til), 150 belgigacha |
| `name_uz` | ixtiyoriy |
| `url` * | majburiy, to'liq havola (`https://...`); noto'g'ri bo'lsa `400` |
| `send_push` | faqat yaratishda, default `true` — quyida **Mijozlarga xabar**. Javobda qaytmaydi |

Faqat o'qiladi: `id`, `name` (joriy tildagi nom), `created_at`, `updated_at`. Fayl yuklanmaydi — faqat havola, JSON yuboriladi.

- Qidiruv: `?search=` (nomi uz/ru, `url`)
- Tartib: `?ordering=` `id`, `name`, `created_at`, `updated_at`

---

## Mijozlarga xabar (maqola / video yaratilganda)

`POST articles/` yoki `POST videos/` da `send_push` yuborilmasa yoki `true` bo'lsa, backend o'zi:

1. **hammaga** bildirishnoma yaratadi (`notifications/` ro'yxatida ko'rinadi, `push_to_topic: true`):

   | | Maqola | Video |
   | --- | --- | --- |
   | sarlavha | maqola `title` (150 belgigacha qisqartiriladi), uz = ru | `Yangi video` / `Новое видео` |
   | matn | `short_description` (200 belgigacha), uz = ru | `name_uz` / `name_ru` |
   | havola | `link_type=article`, `buildex://article/<id>` | `link_type=video`, `buildex://video/<id>` |

2. push yuboradi — ilovaning barcha qurilmalariga bitta FCM topic orqali (ruscha matn).

- **Jim soatlar** yoqilgan: 22:00–09:00 oralig'ida yaratilsa, bildirishnoma ertalab 09:00 ga rejalashtiriladi (`scheduled`) va push shu payt ketadi.
- `"send_push": false` — bildirishnoma ham, push ham bo'lmaydi (masalan, eski maqolani qayta kiritganda). Formada "Mijozlarga xabar yuborish" checkbox'i, default yoqilgan.
- `PUT` / `PATCH` da `send_push` e'tiborga olinmaydi — tahrirlash qayta push yubormaydi. Bildirishnoma matnini `notifications/{id}/` da tuzatish mumkin (ketgan push o'zgarmaydi).
- Maqola / video **o'chirilsa**, unga olib boradigan bildirishnomalar ham o'chadi (rejalashtirilgani bo'lsa — push ketmaydi).
- Django admin orqali qo'shilgan maqola / videoga xabar ketmaydi — faqat shu admin API.

---

## Xatolar

Oddiy DRF formati — maydon nomi bo'yicha:

```json
{
  "title_ru": ["Обязательное поле."],
  "image": ["Ни одного файла не было отправлено."]
}
```

## Eslatmalar

- Mijoz API'si (sayt / ilova) o'zgarmagan: `GET /api/v1/base/news/`, `articles/`, `video/` avvalgidek ishlaydi, yaratilgan yozuv darhol ko'rinadi (kesh yo'q). Yashirish / qoralama holati yo'q — yozuv bor bo'lsa, mijozga chiqadi.
- `description` ichiga rasm qo'yish: admin API'da rich text uchun alohida rasm yuklash endpointi **yo'q** (django-admin'dagi ckeditor uploader faqat sessiya bilan ishlaydi). Hozircha matn ichidagi rasm tashqi havola (`<img src="https://...">`) bo'lishi kerak.
