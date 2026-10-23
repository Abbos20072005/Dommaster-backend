# Kategoriya matni (tovarlar ostidagi blok) — mobile / sayt uchun

BLD-251: kategoriya sahifasida, tovarlar ro'yxatidan pastda chiqadigan foydali matn (ru + uz). Matnni kontent jamoasi admin panelda kiritadi.

## Endpointlar

Yangi endpoint yo'q — mavjud kategoriya detail javoblariga bitta kalit qo'shildi: `description`.

| Endpoint | Sahifa | `description` kimda |
| --- | --- | --- |
| `GET /api/v1/categories/<id>/` | L1 kategoriya (ichida sub kategoriyalar) | faqat L1 ning o'zida |
| `GET /api/v1/sub/categories/<id>/` | L2 sub kategoriya (ichida L3 lar) | faqat L2 ning o'zida |
| `GET /api/v1/item/categories/<id>/` | L3 (predmet) kategoriya — tovarlar ro'yxati sahifasi | L3 ning o'zida |

Ichma-ich keladigan bolalar (`sub_categories[]`, `product_item_categories[]`) va ro'yxatlarda (`item/categories/` hammasi, `categories/` menyu) `description` kaliti **yo'q** — javob og'irlashmasin. Bolaning matni kerak bo'lsa, o'sha bolaning detail endpointini chaqiring.

Auth kerak emas.

## Javob

`GET /api/v1/item/categories/12/` (`Accept-Language: ru`):

```json
{
  "result": {
    "id": 12,
    "name": "Перфораторы",
    "slug": "perforatory",
    "meta_title": "",
    "meta_description": "",
    "image": "https://api.buildex.uz/media/item_category/perf.png",
    "image_alt": "",
    "description": "<h2>Как выбрать перфоратор</h2><p>Смотрите на мощность и <strong>силу удара</strong>.</p><ul><li>SDS-plus — для дома</li><li>SDS-max — для демонтажа</li></ul><p>Смотрите также <a href=\"/catalog/instrumenty/dreli\">дрели</a>.</p>",
    "product_amount": 84,
    "breadcrumbs": [ ... ],
    "updated_at": "2026-10-23T14:40:00"
  },
  "ok": true
}
```

| Maydon | Turi | Izoh |
| --- | --- | --- |
| `description` | string | Admin panelda kiritilgan matn. `""` = matn yo'q → **blok umuman chiqmasin** |

### Format

Backend matnni admin panelda kiritilganidek saqlaydi va qaytaradi (tozalamaydi, o'zgartirmaydi). Format (markdown yoki cheklangan HTML: sarlavha, ro'yxat, havola) admin panel bilan kelishiladi — render qilishdan oldin uni front xavfsiz holga keltiradi (ruxsat etilgan teglardan boshqasini olib tashlash, `script` / `on*` atributlar yo'q). Tashqi havolalarga `rel` / `target` qo'yish ham frontda. Matndagi havolalarni slug'li URL'larga almashtirish — BLD-47 dan keyin, kontent tomonidan.

## Til

`Accept-Language: uz` → uz matn, `ru` (yoki boshqa / header yo'q) → ru matn.

**Fallback yo'q**: uz matn kiritilmagan bo'lsa, `uz` so'rovda `description = ""` keladi (ru matn uz sahifada ko'rsatilmaydi). Shunda uz sahifada blok chiqmaydi.

## Xatolar

O'zgarmadi: kategoriya topilmasa yoki faol bo'lmasa → `{"detail": ..., "ok": false, "result": "", "error_code": ...}` (`NOT_FOUND`).

## Frontda qilinadigan ishlar

1. **Sayt (SSR)**: kategoriya sahifasini serverda render qilganda `description` ni tovarlar ro'yxatidan **pastda** chiqarish — matn sahifa kodida (view-source) ko'rinishi kerak.
2. `description === ""` → blokni umuman render qilmaslik (bo'sh sarlavha / bo'sh konteyner ham yo'q).
3. Uzun matn: birinchi 2–3 qator ko'rinadi, qolgani «Ko'proq / Подробнее» tugmasi bilan ochiladi. Matn HTML'da to'liq turadi, faqat CSS bilan yashiriladi (`max-height` + `overflow: hidden`), JS bilan keyin yuklanmaydi.
4. Blok tovarlar ro'yxatidan keyin turadi — tovarlarni pastga surmaydi (mobil va desktop).
5. Til almashtirilganda sahifani yangi `Accept-Language` bilan qayta so'rash.
6. Mobil ilova: hozircha majburiy emas; kerak bo'lsa xuddi shu kalit.
