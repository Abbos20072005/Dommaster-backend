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
  "placement": "home_top",
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
| `placement` | Joylashuv | `home_top` — Bosh sahifa · yuqori slayder (default; sayt va ilova uchun **bitta** ro'yxat, qayerda ko'rinishini kanallar belgilaydi), `home_bottom` — Bosh sahifa · pastda, `catalog` — Katalog (kategoriya sahifasi) ichida. Pastdagi "Banner turlari" ga qarang |
| `show_on_site`, `show_on_ios`, `show_on_android` | Kanallar | default `true`; kamida bittasi `true` bo'lishi shart. Banner faqat saytda yoki faqat ilovada chiqishi kerak bo'lsa — shu yerda belgilanadi |
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
| Bosh sahifa · yuqori slayder | `banners/?placement=home_top&is_visible=true` |
| Bosh sahifa · pastda | `banners/?placement=home_bottom&is_visible=true` |
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
  "home_top": 9,
  "home_bottom": 2,
  "catalog": 3
}
```

`external` — "Tekshirish kerak": arxivda bo'lmagan `link_type=url` bannerlar. `home_top` / `home_bottom` / `catalog` — shu joylashuvdagi arxivda bo'lmagan bannerlar (tab'dagi son). Ro'yxat filtrlari statistikaga ta'sir qilmaydi.

## Tartib

```json
POST banners/reorder/
{ "ids": [412, 415, 398] }
```

Bitta tab'dagi bannerlar yangi tartibda yuboriladi, ro'yxatdagi o'rni = `position` (1 dan). Javob: `200 {"ids": [...]}`.

## Mijoz API (sayt / ilova)

`GET /api/v1/base/banner/` — faqat `active` bannerlar, `position` bo'yicha. Ixtiyoriy: `?placement=home_top|home_bottom|catalog`, `?platform=site|ios|android`. Javobga `placement`, `link_type`, `page` qo'shilgan.

### Banner turlari — qayerda chiqadi

| Tur | `placement` | Mijoz qayerdan oladi |
| --- | --- | --- |
| Bosh sahifa **yuqorisi** (slayder) | `home_top` | `base/banner/` — `placement` **yuborilmasa** aynan shu qaytadi (eski sayt / ilova shunday ishlaydi); yoki `?placement=home_top` (eski `site_home` / `app_home` nomlari ham qabul qilinadi) + `?platform=` |
| Bosh sahifa **pasti** | `home_bottom` | `GET /api/v1/main/` — har bir reklama blokidan (`addsbrands`) keyingi `type: "banners"` elementlari (`data` — bannerlar ro'yxati); yoki `base/banner/?placement=home_bottom` |
| **Kategoriya sahifasi** | `catalog` | `base/banner/?placement=catalog` |

- `main/` da `home_bottom` bannerlar reklama bloklari orasida **teng bo'linadi** va har blokdan keyin ro'yxat bo'lib keladi (tartib — `position`, qoldiq birinchi ro'yxatlarga; masalan 2 ta blok va 5 ta banner → 3 + 2). Banner bloklardan kam bo'lsa, oxirgi bloklar bannersiz qoladi; hech bir banner tushib qolmaydi. `main/` ~17 daqiqa keshlanadi — yangi banner darhol ko'rinmaydi.
- `catalog` bannerlari aniq bir kategoriyaga bog'lanmaydi: hamma kategoriya sahifalari uchun bitta ro'yxat (`target` — bosilganda qayerga olib borishi, qayerda ko'rinishi emas).
- Yangi bosh sahifa (`GET /api/v1/home/`) da slayder bloki `banner_placement` bo'yicha ishlaydi — `home_bottom` uchun shu joylashuvli yana bitta `slider` blok qo'shiladi.

Mijoz tomoni to'liq: `docs/mobile/banners.md`.

## Nima o'zgardi — `home_bottom` joylashuvi

Yangi joylashuv qo'shildi: **`home_bottom` — Bosh sahifa · pastda**. Admin panelda qilish kerak:

| Joy | Nima qilish kerak |
| --- | --- |
| Banner formasi → "Joylashuv" | tanlovga `home_bottom` qo'shish |
| Bannerlar sahifasi → tab'lar | yangi tab: `banners/?placement=home_bottom&is_visible=true` |
| Tab'dagi son | `banners/stats/` javobida yangi `home_bottom` maydoni |
| Tartib (drag & drop) | o'zgarmagan — `banners/reorder/` ga shu tab'dagi bannerlar yuboriladi |
| "Bosh sahifa" → `slider` blok | `banner_placement` tanloviga `home_bottom` qo'shish (`docs/admin/home_page.md`) |

Banner obyekti, maydonlar va validatsiya **o'zgarmagan** — faqat `placement` ning yangi qiymati.

Adminga tushuntirish uchun (qaysi joylashuv qayerda ko'rinadi):

- **Bosh sahifa · yuqori slayder** — bosh sahifaning eng yuqorisidagi slayder (sayt va ilovada; kanallar bo'yicha).
- **Bosh sahifa · pastda** — bosh sahifadagi reklama bloklari ("Asosiy bo'limlar") orasida: bannerlar bloklar soniga teng bo'linib, har blokdan keyin ro'yxat (karusel) bo'lib chiqadi; shu joylashuvdagi hamma faol bannerlar ko'rinadi. Yangi banner saytda ~17 daqiqagacha kechikib ko'rinishi mumkin (kesh).
- **Katalog ichida** — kategoriya sahifasida; hamma kategoriyalar uchun bitta ro'yxat.

## Nima o'zgardi — yuqori slayder bitta joylashuv

`site_home` (Sayt · bosh slayder) va `app_home` (Ilova · bosh ekran) **bitta joylashuvga birlashtirildi: `home_top` — Bosh sahifa · yuqori slayder**. Banner saytda yoki ilovada chiqishini endi faqat kanallar (`show_on_site`, `show_on_ios`, `show_on_android`) belgilaydi.

| Joy | Nima qilish kerak |
| --- | --- |
| Bannerlar sahifasi → tab'lar | ikkita tab o'rniga bitta: `banners/?placement=home_top&is_visible=true` (jami: `home_top`, `home_bottom`, `catalog`, Arxiv) |
| Tab'dagi son | `banners/stats/` da `site_home` va `app_home` o'rniga bitta `home_top` |
| Banner formasi → "Joylashuv" | tanlovda 3 ta qiymat: `home_top`, `home_bottom`, `catalog`. `site_home` / `app_home` yuborilsa — `400` |
| Ro'yxat filtri | `?placement=site_home` / `app_home` endi `400` |
| "Bosh sahifa" → `slider` blok | **o'zgarmagan** — `banner_placement` qiymatlari avvalgidek (`site_home`, `app_home`, `home_bottom`, `catalog`); `site_home` va `app_home` ikkalasi ham `home_top` bannerlarini ko'rsatadi |

Mavjud bannerlar avtomatik `home_top` ga o'tkazilgan; ikkala ro'yxat `position` bo'yicha qo'shilib, 1 dan qayta raqamlangan (tartibni admin drag & drop bilan to'g'rilashi mumkin). Kanallar o'zgarmagan: masalan, faqat ilova uchun kiritilgan banner saytda ham chiqmasligi uchun unda `show_on_site=false` bo'lishi kerak — eski `app_home` bannerlarini bir ko'zdan kechirish kerak.