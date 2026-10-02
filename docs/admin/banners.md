# Bannerlar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET banners/` | ro'yxat (paginatsiyali, default tartib — `position`) |
| `POST banners/` | yaratish (`multipart/form-data` — rasmlar bor) |
| `GET / PATCH / DELETE banners/{id}/` | bitta banner |
| `GET banners/stats/` | tepadagi kartochkalar va tab'lardagi sonlar |
| `POST banners/reorder/` | tartibni o'zgartirish (`{"ids": [...]}`) |

Swagger: `/swagger/admin/` → **banners**.

---

## Obyekt

```json
{
  "id": 412,
  "code": "BNR-0412",
  "title": "Knauf kuzgi aksiya",
  "title_uz": null,
  "title_ru": "Knauf kuzgi aksiya",
  "title_en": null,
  "desktop_image": "https://.../media/banner/desktop/knauf.png",
  "mobile_image": "https://.../media/banner/mobile/knauf.png",
  "placement": "site_home",
  "show_on_site": true,
  "show_on_ios": true,
  "show_on_android": true,
  "link_type": "category",
  "target": { "model": "productitemcategory", "id": 31, "name": "Gipsokarton" },
  "page": "",
  "link": "",
  "starts_at": "2026-09-15T00:00:00",
  "ends_at": "2026-10-01T23:59:00",
  "position": 1,
  "is_visible": true,
  "status": "active",
  "created_at": "2026-09-14T10:12:00",
  "updated_at": "2026-09-14T10:12:00"
}
```

| Maydon | Dizaynda | Izoh |
| --- | --- | --- |
| `code` | `BNR-0412` | faqat o'qiladi, `id` dan yasaladi |
| `title_ru` * | Ichki nom | majburiy; `title_uz`, `title_en` ixtiyoriy |
| `desktop_image` * | Rasm 16:5 | fayl |
| `mobile_image` | Rasm 1:1 | fayl, ixtiyoriy; bo'sh `mobile_image=` — o'chiradi |
| `placement` | Joylashuv | `site_home` — Sayt · bosh slayder (default), `app_home` — Ilova · bosh ekran, `catalog` — Katalog ichida |
| `show_on_site`, `show_on_ios`, `show_on_android` | Kanallar | default `true`; kamida bittasi `true` bo'lishi shart |
| `link_type` * | Havola turi | `category`, `product`, `badge` (Teg), `brand`, `page` (Sahifa), `url` (Tashqi URL) |
| `target` | Manzil | `category` / `product` / `badge` / `brand` uchun — pastga qarang |
| `page` | Manzil | `link_type=page` uchun: ichki yo'l, `/` bilan boshlanadi (`/pro`) |
| `link` | Manzil | `link_type=url` uchun: to'liq URL |
| `starts_at` * | Boshlanish | `YYYY-MM-DDTHH:MM:SS`, Toshkent vaqti |
| `ends_at` | Tugash | ixtiyoriy (`null` — muddatsiz); `starts_at` dan keyin bo'lishi shart |
| `position` | Tartib | yuborilmasa yangi banner o'z joylashuvining oxiriga qo'shiladi |
| `is_visible` | Arxiv | `false` — arxivda (default `true`) |
| `status` | Holat | faqat o'qiladi — pastga qarang |

Faqat o'qiladi: `id`, `code`, `title`, `status`, `created_at`, `updated_at`.

## Havola (`link_type` + manzil)

| `link_type` | Kerakli maydon | `target.model` |
| --- | --- | --- |
| `category` | `target` | `productcategory`, `productsubcategory`, `productitemcategory` |
| `product` | `target` | `product` |
| `badge` | `target` | `productbadge` |
| `brand` | `target` | `brand` |
| `page` | `page` | — |
| `url` | `link` | — |

- JSON: `"target": {"model": "product", "id": 97}`. Multipart: `target.model=product` + `target.id=97`.
- Tanlangan turga tegishli bo'lmagan maydonlar serverda tozalanadi (masalan `link_type=page` bo'lsa `target` → `null`, `link` → `""`), ularni alohida bo'shatish shart emas.
- `PATCH` da `link_type` o'zgarsa, yangi turning manzili ham shu so'rovda yuborilishi kerak, aks holda `400`.
- "Sahifa" ro'yxati backend'da saqlanmaydi — `page` ga yo'l matn sifatida yoziladi.

## Holat (`status`)

Saqlanmaydi, har so'rovda hisoblanadi:

| `status` | Qachon |
| --- | --- |
| `archived` | `is_visible=false` |
| `scheduled` — Rejalashtirilgan | `starts_at` hali kelmagan |
| `expired` — Muddati tugagan | `ends_at` o'tib ketgan |
| `active` — Faol | qolgan hollarda |

Arxivga o'tkazish: `PATCH banners/{id}/` `{"is_visible": false}`, qaytarish: `{"is_visible": true}`.

## Ro'yxat

Filtrlar: `?placement=`, `?status=active|scheduled|expired|archived`, `?link_type=`, `?is_visible=`,
`?show_on_site=`, `?show_on_ios=`, `?show_on_android=`, `?target_model=`, `?has_target=`, `?search=` (nom, `link`, `page`),
`?ordering=position|starts_at|ends_at|title|created_at`.

Tab'lar:

| Tab | So'rov |
| --- | --- |
| Sayt · bosh slayder | `banners/?placement=site_home&is_visible=true` |
| Ilova · bosh ekran | `banners/?placement=app_home&is_visible=true` |
| Katalog ichida | `banners/?placement=catalog&is_visible=true` |
| Arxiv | `banners/?is_visible=false` |

## Statistika

```json
GET banners/stats/
{
  "active": 10,
  "scheduled": 4,
  "expired": 2,
  "archived": 2,
  "external": 1,
  "site_home": 6,
  "app_home": 3,
  "catalog": 3
}
```

`external` — "Tekshirish kerak": arxivda bo'lmagan `link_type=url` bannerlar. `site_home` / `app_home` / `catalog` — shu joylashuvdagi arxivda bo'lmagan bannerlar (tab'dagi son). Ro'yxat filtrlari statistikaga ta'sir qilmaydi.

## Tartib

```json
POST banners/reorder/
{ "ids": [412, 415, 398] }
```

Bitta tab'dagi bannerlar yangi tartibda yuboriladi, ro'yxatdagi o'rni = `position` (1 dan). Javob: `200 {"ids": [...]}`.

## Mijoz API (sayt / ilova)

`GET /api/v1/base/banner/` — faqat `active` bannerlar, `position` bo'yicha. Ixtiyoriy: `?placement=site_home|app_home|catalog`, `?platform=site|ios|android`. Parametrsiz barcha faol bannerlar qaytadi (eski ilova shunday ishlaydi). Javobga `placement`, `link_type`, `page` qo'shilgan.
