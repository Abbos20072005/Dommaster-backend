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
  "title_en": null,
  "description": "<p>Подробности внутри.</p>",
  "description_uz": "<p>Tafsilotlar ichida.</p>",
  "description_ru": "<p>Подробности внутри.</p>",
  "description_en": null,
  "image": "https://.../media/news/filial.png",
  "created_at": "2026-10-02T15:14:26",
  "updated_at": "2026-10-02T15:14:26"
}
```

| Maydon | Izoh |
| --- | --- |
| `title_ru` * | majburiy (asosiy til), 450 belgigacha |
| `title_uz`, `title_en` | ixtiyoriy |
| `description_ru` * | majburiy, HTML (rich text) |
| `description_uz`, `description_en` | ixtiyoriy, HTML |
| `image` * | rasm, yaratishda majburiy (multipart); keyin o'chirib bo'lmaydi, faqat almashtiriladi |

Faqat o'qiladi: `id`, `title`, `description` (joriy tildagi qiymat), `created_at`, `updated_at`.

Rasm almashtirilsa yoki yangilik o'chirilsa — eski fayl diskdan ham o'chiriladi.

Rasm o'zgarmasa `PATCH` ni JSON bilan yuborish mumkin:

```json
{ "title_en": "New branch opened" }
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
      "title_en": null,
      "image": "https://.../media/news/filial.png",
      "created_at": "2026-10-02T15:14:26",
      "updated_at": "2026-10-02T15:14:26"
    }
  ]
}
```

- Qidiruv: `?search=` (sarlavha uz/ru/en)
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
  "name_en": null,
  "url": "https://youtube.com/watch?v=demo",
  "created_at": "2026-10-02T15:14:27",
  "updated_at": "2026-10-02T15:14:27"
}
```

| Maydon | Izoh |
| --- | --- |
| `name_ru` * | majburiy (asosiy til), 150 belgigacha |
| `name_uz`, `name_en` | ixtiyoriy |
| `url` * | majburiy, to'liq havola (`https://...`); noto'g'ri bo'lsa `400` |

Faqat o'qiladi: `id`, `name` (joriy tildagi nom), `created_at`, `updated_at`. Fayl yuklanmaydi — faqat havola, JSON yuboriladi.

- Qidiruv: `?search=` (nomi uz/ru/en, `url`)
- Tartib: `?ordering=` `id`, `name`, `created_at`, `updated_at`

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

- Mijoz (sayt / ilova) tomonida hech narsa o'zgarmagan: `GET /api/v1/base/news/`, `articles/`, `video/` avvalgidek ishlaydi, yaratilgan yozuv darhol ko'rinadi (kesh yo'q). Yashirish / qoralama holati yo'q — yozuv bor bo'lsa, mijozga chiqadi.
- `description` ichiga rasm qo'yish: admin API'da rich text uchun alohida rasm yuklash endpointi **yo'q** (django-admin'dagi ckeditor uploader faqat sessiya bilan ishlaydi). Hozircha matn ichidagi rasm tashqi havola (`<img src="https://...">`) bo'lishi kerak.
