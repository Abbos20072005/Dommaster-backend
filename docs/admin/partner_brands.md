# Hamkor brendlar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET partner-brands/` | hamkor brendlar ro'yxati (paginatsiyali) |
| `POST partner-brands/` | hamkor brend yaratish (JSON) |
| `GET / PATCH / PUT / DELETE partner-brands/{id}/` | bitta hamkor brend |

Swagger: `/swagger/admin/` → **partner-brands**.

> Hamkor brend — oddiy brendlardan (`brands/`, [brands.md](brands.md)) alohida, mustaqil ro'yxat: mahsulotlarga ham, `brands/` ga ham **bog'lanmagan**. Faqat nom va holatdan iborat — logotip (rasm), tavsif, tarjima maydonlari yo'q.

---

## Obyekt

```json
{
  "id": 3,
  "name": "Knauf",
  "is_active": true,
  "created_at": "2026-10-02T12:28:41.512934",
  "updated_at": "2026-10-02T12:28:41.512934"
}
```

| Maydon | Izoh |
| --- | --- |
| `name` * | nomi, majburiy, 255 belgigacha; tarjimasiz (bitta maydon); unikal emas — bir xil nom ikki marta kiritilishi mumkin |
| `is_active` | default `true`; `false` = nofaol |

Faqat o'qiladi: `id`, `created_at`, `updated_at`.

Yaratish (`POST partner-brands/` → `201` + obyekt):

```json
{ "name": "Knauf" }
```

O'zgartirish (`PATCH partner-brands/{id}/` — faqat kerakli maydon → `200` + obyekt):

```json
{ "is_active": false }
```

O'chirish: `DELETE partner-brands/{id}/` → `204`, body yo'q. Cheklovsiz — hech narsaga bog'lanmagan.

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
  "results": [
    { "id": 3, "name": "Knauf", "is_active": true, "created_at": "...", "updated_at": "..." }
  ]
}
```

- Qidiruv: `?search=` (`name`)
- Filtr: `is_active` (`true` / `false`)
- Tartib: `?ordering=` `id`, `name`, `created_at`, `updated_at` (teskari: `-name`); default — yangilari birinchi (`-created_at`)

---

## Xatolar

Oddiy DRF formatida (klient API'dagi `{"ok", "error_code"}` o'rami yo'q). Xabar matnlari tilga bog'liq (default — ruscha), shuning uchun matnga emas, HTTP status va maydon nomiga tayaning.

| Holat | HTTP | Body |
| --- | --- | --- |
| Token yo'q yoki yaroqsiz | 401 | `{"detail": "..."}` |
| `name` yuborilmadi | 400 | `{"name": ["Обязательное поле."]}` |
| `name` bo'sh yoki 255 belgidan uzun | 400 | `{"name": ["..."]}` |
| Mavjud bo'lmagan `id` | 404 | `{"detail": "..."}` |

---

## Eslatmalar

- Hamkor brendlar faqat admin API'da — mijoz (sayt / ilova) API'lariga hozircha **chiqarilmagan**, ya'ni `is_active` hozir faqat admin paneldagi holat (hech qayerda filtr sifatida ishlatilmaydi).
- Tartiblash maydoni (`position`) yo'q — ro'yxat `?ordering=` bilan tartiblanadi, qo'lda joyini almashtirish (`reorder/`) yo'q.
- Mahsulotlar soni (`products_count`) yo'q — hamkor brend mahsulotlarga bog'lanmagan. Mahsulot brendlari uchun `brands/` ishlatiladi.
