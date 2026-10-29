# Brend tavsifi — mobile / sayt uchun

BLD-248: brend sahifasidagi (`/brand/knauf`) qisqa tavsif (ru + uz). Matnni kontent jamoasi admin panelda kiritadi.

## Endpoint

Yangi endpoint yo'q — `GET /api/v1/brands/<id>/` javobiga bitta kalit qo'shildi: `description`. Brendlar ro'yxatida (`brands/`) va tovar ichidagi `brand` obyektida bu kalit **yo'q**.

Auth kerak emas.

`GET /api/v1/brands/7/` (`Accept-Language: ru`):

```json
{
  "result": {
    "id": 7,
    "name": "Knauf",
    "slug": "knauf",
    "description": "<p>Knauf — немецкий производитель строительных смесей и гипсокартона.</p>",
    "meta_title": "",
    "meta_description": "",
    "image": "https://api.buildex.uz/media/brand/image/knauf.png",
    "image_alt": "",
    "products_count": 64,
    "updated_at": "2026-10-29T10:00:00"
  },
  "ok": true
}
```

| Maydon | Turi | Izoh |
| --- | --- | --- |
| `description` | string | Admin panelda kiritilgan matn. `""` = matn yo'q → **blok umuman chiqmasin** |

## Format

Backend matnni kiritilganidek saqlaydi va qaytaradi (tozalamaydi). Oddiy matn yoki cheklangan HTML (paragraf, ro'yxat, havola) bo'lishi mumkin — kategoriya matnidagi qoida bilan bir xil ([category_description.md](category_description.md)): render qilishdan oldin front ruxsat etilgan teglardan boshqasini olib tashlaydi; HTML tegi bo'lmagan matnda qator ko'chishlarini o'zi saqlaydi.

## Til

`Accept-Language: uz` → uz matn, `ru` (yoki boshqa / header yo'q) → ru matn.

**Fallback yo'q**: uz matn kiritilmagan bo'lsa, `uz` so'rovda `description = ""` keladi — uz sahifada blok chiqmaydi (ru matn ko'rsatilmaydi). Kategoriya matni bilan bir xil.

## Xatolar

O'zgarmadi: brend topilmasa → `NOT_FOUND`.
