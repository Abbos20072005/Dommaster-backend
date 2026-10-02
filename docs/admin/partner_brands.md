# Hamkor brendlar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET partner-brands/` | hamkor brendlar ro'yxati (paginatsiyali) |
| `POST partner-brands/` | hamkor brend yaratish (JSON) |
| `GET / PATCH / PUT / DELETE partner-brands/{id}/` | bitta hamkor brend |

Swagger: `/swagger/admin/` → **partner-brands**.

> Bu oddiy brendlardan (`brands/`, [brands.md](brands.md)) alohida, mustaqil ro'yxat: mahsulotlarga ham, `brands/` ga ham bog'lanmagan.

---

## Obyekt

```json
{
  "id": 3,
  "name": "Knauf",
  "is_active": true,
  "created_at": "2026-10-02T12:28:41",
  "updated_at": "2026-10-02T12:28:41"
}
```

| Maydon | Izoh |
| --- | --- |
| `name` * | nomi, majburiy, 255 belgigacha; tarjimasiz (bitta maydon); unikal emas — bir xil nom ikki marta kiritilishi mumkin |
| `is_active` | default `true` |

Faqat o'qiladi: `id`, `created_at`, `updated_at`.

Yaratish:

```json
{ "name": "Knauf" }
```

O'zgartirish (`PATCH` — faqat kerakli maydon):

```json
{ "is_active": false }
```

Xato (`400`):

```json
{ "name": ["This field is required."] }
```

O'chirish: `DELETE partner-brands/{id}/` → `204`, cheklovsiz (hech narsaga bog'lanmagan).

> Hamkor brendlar hozircha faqat admin API'da — mijoz (sayt / ilova) API'lariga chiqarilmagan, logotip (rasm) maydoni yo'q.

---

## Ro'yxat

`GET partner-brands/?page=&page_size=` (default 20, max 100)

```json
{
  "count": 14,
  "next": "https://.../api/v1/admin/partner-brands/?page=2",
  "previous": null,
  "next_page": 2,
  "previous_page": null,
  "results": [ { "id": 3, "name": "Knauf", "is_active": true, "created_at": "...", "updated_at": "..." } ]
}
```

- Qidiruv: `?search=` (nomi)
- Filtr: `is_active` (`true` / `false`)
- Tartib: `?ordering=` `id`, `name`, `created_at`, `updated_at` (teskari: `-name`); default — yangilari birinchi (`-created_at`)
