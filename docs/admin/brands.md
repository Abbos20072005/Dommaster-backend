# Brendlar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET brands/` | brendlar ro'yxati (paginatsiyali) |
| `POST brands/` | brend yaratish (multipart — `image` fayl) |
| `GET / PATCH / DELETE brands/{id}/` | bitta brend |

Swagger: `/swagger/admin/` → **brands**.

---

## Obyekt

```json
{
  "id": 12,
  "name": "Bosch",
  "name_uz": "Bosch",
  "name_ru": "Bosch",
  "name_en": null,
  "description_uz": "Nemis elektr asboblari brendi",
  "description_ru": "Немецкий бренд электроинструмента",
  "description_en": null,
  "country": "Germaniya",
  "image": "https://.../media/brand/image/bosch.png",
  "is_visible": true,
  "show_on_home": false,
  "code": "000000045",
  "products_count": 318,
  "created_at": "2026-10-02T12:28:41",
  "updated_at": "2026-10-02T12:28:41"
}
```

| Maydon | Izoh |
| --- | --- |
| `name_ru` * | majburiy (asosiy til) |
| `name_uz`, `name_en` | ixtiyoriy |
| `description_uz`, `description_ru`, `description_en` | tavsif, ixtiyoriy; bo'sh bo'lsa `null` yoki `""` keladi |
| `country` | mamlakat — oddiy matn (bitta maydon, tarjimasiz), ixtiyoriy, 100 belgigacha; bo'sh = `""` |
| `image` * | logotip, yaratishda majburiy (multipart) |
| `is_visible` | default `true` |
| `show_on_home` | "Bosh sahifada" belgisi, default `false`. Bosh sahifaning `brands` bloki shu belgili (va `is_visible`) brendlarni sanaydi — [home_page.md](home_page.md) |
| `code` | 1C kodi, unikal, ixtiyoriy (bo'sh → `null`) |

Faqat o'qiladi: `id`, `name` (joriy tildagi nom), `products_count`, `created_at`, `updated_at`.

Rasm o'zgarmasa `PATCH` ni JSON bilan yuborish mumkin:

```json
{ "country": "Turkiya", "description_uz": "..." }
```

O'chirish: mahsuloti bor brend o'chirilmaydi → `400 {"detail": "Brand has products, hide it instead (is_visible=false)."}`.

> `description`, `country` va `show_on_home` hozircha faqat admin API'da — mijoz (sayt / ilova) API'lariga chiqarilmagan.

---

## Ro'yxat

`GET brands/?page=&page_size=`

- Qidiruv: `?search=` (nomi uz/ru/en, `code`, `country`)
- Filtrlar: `is_visible`, `show_on_home`, `country` (aniq mos kelishi kerak), `has_products`
- Tartib: `?ordering=` `id`, `name`, `country`, `products_count`, `created_at`, `updated_at` (teskari: `-name`)
