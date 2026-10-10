# Bosh sahifa (bloklar) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET home-blocks/` | bloklar ro'yxati — **paginatsiyasiz** (massiv), sahifadagi tartibda |
| `POST home-blocks/` | "+ Blok qo'shish" |
| `GET / PATCH / DELETE home-blocks/{id}/` | bitta blok |
| `POST home-blocks/reorder/` | drag & drop (`{"ids": [...]}`) |
| `GET / PATCH home-page/` | "Ko'rsatish qoidalari" + nashr holati |
| `POST home-page/publish/` | "Nashr qilish" |

Swagger: `/swagger/admin/` → **home-blocks**, **home-page**.

Bloklar ro'yxati — bu **qoralama**: har bir o'zgarish darhol saqlanadi, lekin "Nashr qilish" bosilmaguncha nashr qilingan versiyaga o'tmaydi.

---

## Blok

```json
{
  "id": 9,
  "type": "badge_products",
  "title": "Подборка Хит",
  "title_uz": "Podborka \"Hit\"",
  "title_ru": "Подборка Хит",
  "title_en": null,
  "position": 3,
  "is_visible": true,
  "show_on_site": true,
  "show_in_app": true,
  "banner_placement": "",
  "banner": null,
  "badge": { "id": 7, "name": "Хит", "kind": "manual", "color": "#2563EB" },
  "sale": null,
  "days": null,
  "pages": [],
  "items_count": 90,
  "items_total": 118,
  "status": "visible",
  "created_at": "2026-10-09T12:04:21",
  "updated_at": "2026-10-09T12:04:21"
}
```

| Maydon | Izoh |
| --- | --- |
| `type` * | blok turi (pastdagi jadval). Faqat yaratishda beriladi, `PATCH` da e'tiborga olinmaydi |
| `title_ru` * | sarlavha, majburiy (asosiy til); `title_uz`, `title_en` ixtiyoriy |
| `position` | tartib; yuborilmasa yangi blok oxiriga qo'shiladi. O'zgartirish uchun `reorder/` |
| `is_visible` | `false` — blok qo'lda yashirilgan |
| `show_on_site`, `show_in_app` | "Sayt" / "Ilova" belgilari. Kamida bittasi `true` bo'lishi kerak |
| `banner_placement`, `banner`, `badge`, `sale`, `days`, `pages` | blokning manbasi — turiga qarab bittasi ishlatiladi, qolganlari bo'shatiladi |

Faqat o'qiladi: `id`, `title` (joriy tildagi sarlavha), `items_count`, `items_total`, `status`, `created_at`, `updated_at`.

### Turlar

| `type` | Blok | Manba maydoni | `items_count` |
| --- | --- | --- | --- |
| `slider` | Bannerlar slayderi | `banner_placement` *: `site_home` / `app_home` / `catalog` | shu joylashuvdagi faol bannerlar |
| `banner` | Bitta banner | `banner` *: `{"id": 4}` yoki `4` | `1` — banner faol, aks holda `0` |
| `categories` | 1-daraja kategoriyalar | — | faol kategoriyalar |
| `brands` | Brendlar | — | "Bosh sahifada" belgilangan brendlar (`brands/` dagi `show_on_home`) |
| `badge_products` | Teg bo'yicha podborka | `badge` *: `{"id": 7}` yoki `7` | mahsulotlar |
| `sale_products` | Aksiya mahsulotlari | `sale`: `{"id": 1}`; `null` — asosiy aksiya (`is_main`) | mahsulotlar |
| `new_products` | Yangi mahsulotlar | `days` *: oxirgi necha kunda qo'shilgan (`>= 1`) | mahsulotlar |
| `bestsellers` | Eng ko'p sotilganlar | — | mahsulotlar (bekor qilinmagan buyurtmalarda sotilganlar) |
| `all_products` | Barcha mahsulotlar | — | mahsulotlar |
| `pages` | Sahifalar ("Xizmatlar va shartlar") | `pages` *: `[{"title_ru", "title_uz", "title_en", "path"}]` | sahifalar soni |
| `content` | Maqola / Videolar | — | maqolalar + videolar |
| `adds_brands` | Asosiy bo'limlar (reklama bloklari) | — | ko'rinadigan `adds-brands` |

`*` — shu tur uchun majburiy; berilmasa `400 {"<maydon>": ["Required for type=..."]}`.

`pages` elementi: `title_ru` majburiy, `path` — ichki yo'l, `/` bilan boshlanadi (`/delivery`).

### `items_count` / `items_total` — "90 ta mos (118 dan)"

Mahsulotli bloklar (`badge_products`, `sale_products`, `new_products`, `bestsellers`, `all_products`):

- `items_total` — manbadagi faol mahsulotlar (118);
- `items_count` — ulardan ko'rsatish qoidalariga mos keladiganlari (90).

Boshqa bloklarda `items_count` — blokdagi elementlar soni, `items_total` = `null`.

### `status`

| `status` | UI | Qachon |
| --- | --- | --- |
| `visible` | Ko'rsatiladi | qolgan hollarda |
| `hidden` | Yashirilgan | `is_visible=false` |
| `rule_hidden` | Qoida bo'yicha yashirin | mahsulotli blok, `items_count` < `min_products` |

`status` saqlanmaydi — har so'rovda hisoblanadi.

---

## Ro'yxat

`GET home-blocks/` → massiv (paginatsiya yo'q), tartib — `position`.

- Tablar: `?channel=site` ("Sayt") / `?channel=app` ("Mobil ilova") — shu kanalda yoqilgan bloklar
- Filtrlar: `type`, `is_visible`, `show_on_site`, `show_in_app`; qidiruv: `?search=` (sarlavha)

## Tartib

```json
POST home-blocks/reorder/
{ "ids": [12, 10, 9] }
```

`ids` — yangi tartibdagi bloklar. Hamma blokni ham, faqat bitta tabdagilarini ham yuborish mumkin: yuborilgan bloklar o'zlari egallab turgan joylar ichida qayta joylashadi, yuborilmaganlari (boshqa kanaldagi bloklar) joyida qoladi. Javob: `200 {"ids": [...]}`.

---

## Ko'rsatish qoidalari va nashr

```json
GET home-page/
{
  "hide_out_of_stock": true,
  "hide_stale_price": true,
  "min_products": 4,
  "personal_feed_enabled": true,
  "personal_feed_holdout_percent": 10,
  "published_at": "2026-09-28T18:20:00",
  "published_by": { "id": 3, "username": "shakhzod", "full_name": "Shakhzod A." },
  "has_changes": false
}
```

| Maydon | Izoh |
| --- | --- |
| `hide_out_of_stock` | "Qoldig'i yo'q mahsulotlarni bloklarda yashirish" — qoldig'i 0 mahsulotlar `items_count` ga kirmaydi |
| `hide_stale_price` | "Narxi eskirgan mahsulotlarni yashirish" — **faqat saqlanadi**, hozircha hech narsaga ta'sir qilmaydi (pastga qarang) |
| `min_products` | "Blokdagi minimal mahsulotlar soni" — mos mahsuloti bundan kam mahsulotli blok `rule_hidden` bo'ladi |
| `personal_feed_enabled` | shaxsiy lenta (`products/recommended/`) o'chirgichi. `false` — endpoint oddiy tasodifiy lentani qaytaradi. **Nashrga bog'liq emas**: saqlangan zahoti kuchga kiradi, `has_changes` ga ta'sir qilmaydi |
| `personal_feed_holdout_percent` | nazorat guruhi, 0–100 (%): shuncha foydalanuvchi shaxsiy lenta o'rniga tasodifiy lentani oladi (lenta foyda berayotganini solishtirish uchun). Test akkaunt shu guruhga tushib qolsa shaxsiy lentani ko'rmaydi — tekshiruv paytida `0` qiling. Bu ham darhol kuchga kiradi |
| `published_at`, `published_by` | "Oxirgi nashr"; hali nashr qilinmagan bo'lsa `null` |
| `has_changes` | qoralama (bloklar + qoidalar) nashr qilingan versiyadan farq qiladi → "Nashr qilish" tugmasi faol |

`PATCH home-page/` — uchta qoida va shaxsiy lentaning ikki sozlamasi yoziladi: `{"min_products": 6}`.

`POST home-page/publish/` — body kerak emas. Joriy bloklar va qoidalarni nashr qilingan versiya sifatida saqlaydi, javobda o'sha `home-page/` obyekti (`has_changes=false`).

Blok yoki qoida o'zgargandan keyin `has_changes` ni yangilash uchun `GET home-page/` ni qayta chaqiring. O'zgarishni qaytarib qo'ysangiz (masalan sarlavhani eski holiga) `has_changes` yana `false` bo'ladi.

---

## Mijozga (sayt / ilova) nima chiqadi

Nashr qilingan versiya mijozga `GET /api/v1/home/?platform=site|ios|android` orqali beriladi ([docs/mobile/home_page.md](../mobile/home_page.md)).

- Qoralamadagi o'zgarishlar "Nashr qilish" gacha mijozga ko'rinmaydi; nashrdan keyin darhol ko'rinadi.
- Mijozga faqat ko'rsatadigan narsasi bor bloklar chiqadi. `status = visible` bo'lsa ham blok **chiqmaydi**, agar: shu platformada o'chirilgan; `items_count = 0` (faol banner yo'q, "Bosh sahifada" belgilangan brend yo'q, ...); manbasi o'chirilgan (banner / teg / aksiya) yoki aksiya yashirilgan.
- `rule_hidden` blok chiqmaydi; mahsulotlar soni `min_products` ga yetishi bilan o'zi qaytadi (qayta nashr shart emas — sanoq jonli).
- Bannerlar, kategoriyalar, brendlar, mahsulotlar tarkibi jonli olinadi (5 daqiqagacha kesh), nashr faqat bloklar ro'yxati, tartibi, sozlamalari va qoidalarni muzlatadi.
- Ilovaning hozirgi versiyasi eski endpointlardan (`main/` va boshqalar) foydalanadi — ular o'zgarmagan. Yangi endpointga o'tgandan keyingina bu sahifadagi sozlamalar ilovaga ta'sir qiladi.

## Hozircha yo'q

- `hide_stale_price` — mahsulotda "1C narxi qachon yangilangan" degan vaqt saqlanmaydi, shuning uchun filtrlash imkoni yo'q.
- "Oldindan ko'rish" / "Jonli ko'rinish" uchun alohida endpoint yo'q — bloklar tarkibi mavjud endpointlardan olinadi (`banners/?placement=`, `products/?badge=`, ...).
- Boshlang'ich holat: migratsiya hozirgi bosh sahifani (8 ta blok) yaratadi va uni nashr qilingan versiya qilib qo'yadi — birinchi "Nashr qilish" gacha `published_at = null`, `has_changes = false`.
