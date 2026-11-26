# Filtr sahifalari (SEO) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>`.

| Endpoint | Nima uchun |
| --- | --- |
| `GET filter-pages/` | sahifalar ro'yxati (paginatsiyali) |
| `POST filter-pages/` | sahifa yaratish |
| `GET / PATCH / DELETE filter-pages/{id}/` | bitta sahifa |

Swagger: `/swagger/admin/` → **filter-pages**.

Filtr sahifasi — kelishilgan kalit so'zlar ro'yxatidagi bitta filtr kombinatsiyasining alohida sahifasi
("Bosch" + "perforator", "kabel VVG 3×2.5", "sement M400 50 kg", "Knauf quruq aralashmalar"): **bitta katalog
darajasi + ixtiyoriy brend + atribut filtrlari**. Saytda o'qiladigan manzil (`slug`), H1, meta va 300–500 belgilik matn bilan ochiladi va
sitemap'ga tushadi. Ro'yxatda yo'q kombinatsiyalar qidiruvga yopiq qoladi.

**Ochiq sahifa** (`is_open: true` — saytda va sitemap'da bor) = `is_active` **va** kamida **3 ta faol tovar**
(`products_count`) **va** sahifaning kategoriyasi faol **va** brend ko'rinadigan (`is_visible`). Tovarlar soni
har soatda qayta hisoblanadi (Celery) va sahifa saqlanganda darhol.

**Daraja** (`level`, faqat o'qish uchun) — sahifa aynan bitta kategoriyaga bog'lanadi:

| `level` | Nima | Filtrlar |
| --- | --- | --- |
| `item_category` | predmet kategoriya ichida brend va / yoki atribut filtrlari ("Makita perforatorlari", "kabel VVG 3×2.5") | bor |
| `sub_category` | butun subkategoriyadagi brend ("Knauf quruq aralashmalar") | yo'q, brend majburiy |
| `category` | butun asosiy kategoriyadagi brend | yo'q, brend majburiy |

Tovarlar soni darajaning hamma predmet kategoriyalaridan sanaladi.

---

## Obyekt

```json
{
  "id": 1,
  "slug": "perforator-makita",
  "level": "item_category",
  "category": null,
  "sub_category": null,
  "item_category": { "id": 452, "name": "Перфораторы", "product_sub_category": { "id": 155, "name": "...", "product_category": { "id": 5, "name": "..." } } },
  "brand": { "id": 24, "name": "Makita" },
  "filters": { "3334": ["SDS-plus"], "3340": { "min": 800, "max": 1200 } },
  "keyword_uz": "makita perforator",
  "keyword_ru": "перфоратор макита",
  "search_volume": 320,
  "title_uz": "Makita perforatorlari",
  "title_ru": "Перфораторы Makita",
  "meta_title_uz": null, "meta_title_ru": null,
  "meta_description_uz": null, "meta_description_ru": null,
  "text_uz": "...", "text_ru": "...",
  "is_active": true,
  "is_open": true,
  "products_count": 18,
  "counted_at": "2026-10-16T13:40:00",
  "created_at": "...", "updated_at": "..."
}
```

| Maydon | |
| --- | --- |
| `slug` | ixtiyoriy; bo'sh → `keyword_ru` (yoki `title_ru`) dan lotincha yasaladi. Unikal, faqat lotin harf / raqam / `-` |
| `category` / `sub_category` / `item_category` | **aynan bittasi** to'ldiriladi, `{"id"}` yoki id. Birortasi yuborilsa, sahifa shu darajaga o'tadi (yuborilmaganlari `null` bo'ladi), ya'ni darajani almashtirish uchun faqat yangisini yuborish kifoya |
| `brand` | ixtiyoriy, `{"id"}` / id / `null` |
| `filters` | faqat `item_category` sahifasida; `product/filter/` dagi `filters` bilan bir xil: kalit = atribut id (`"price"` ham bo'ladi), qiymat = qiymatlar ro'yxati (ru matn, `list` atribut uchun — variantlardan biri, `boolean` — `"true"` / `"false"`) yoki `number` atribut / narx uchun `{"min", "max"}` (kamida bittasi) |
| `keyword_*`, `search_volume` | kalit so'z va oylik qidiruvlar soni (ro'yxatdan; shart — oyiga ≥ 10) |
| `title_*` | H1, `title_ru` **majburiy** |
| `meta_title_*`, `meta_description_*` | bo'sh → saytga H1 / matn boshi beriladi |
| `text_*` | 300–500 belgilik oddiy matn (backend uzunlikni tekshirmaydi) |
| `is_open`, `products_count`, `counted_at` | faqat o'qish uchun |

Tekshiruvlar (`400`):
- daraja yo'q yoki bittadan ko'p → `item_category` kalitida;
- filtr shu predmet kategoriyaga biriktirilgan, `is_filterable` va faol atribut bo'lishi kerak; `list` qiymati
  atribut variantlarida bo'lishi kerak (`filters`);
- predmet kategoriya sahifasida brend ham, filtr ham yo'q → rad etiladi, bu oddiy kategoriya sahifasi (`filters`);
- `sub_category` / `category` sahifasida filtr bor (`filters`) yoki brend yo'q (`brand`) → rad etiladi;
- bir kombinatsiyaga (daraja + brend + filtrlar, tartibi ahamiyatsiz) faqat bitta sahifa (`filters`).

Daraja yoki kategoriya o'zgarsa, eski `filters` yangisi bo'yicha qayta tekshiriladi (yuqori darajaga o'tganda
`filters: {}` ham yuboring). Kategoriya yoki brend
o'chirilsa, sahifa ham o'chadi.

## Ro'yxat filtrlari

`is_active`, `is_open` (`true` / `false`), `level` (`category` / `sub_category` / `item_category`), `category`,
`sub_category`, `item_category`, `brand`, `has_brand`; qidiruv `?search=` — kalit so'z,
H1, slug; tartib `?ordering=` — `search_volume`, `products_count`, `created_at`, `updated_at`, `slug`
(default: eng ko'p qidiriladigan birinchi).

## Ro'yxatni fayldan yuklash

```bash
env/Scripts/python.exe manage.py import_filter_pages pages.xlsx --dry-run
```

Birinchi qator — ustun nomlari: `keyword_ru` (majburiy), `keyword_uz`, `search_volume`, `item_category` /
`sub_category` / `category` (id yoki slug; to'ldirilganlarning eng pastki darajasi sahifa darajasi bo'ladi),
`brand` (id yoki nom), `filters` (faqat predmet kategoriya qatorida) (`Атрибут ru = qiymat | qiymat; Сечение = 2.5..4`, son: `4` — aniq,
`2..` / `..4` — chegara), `slug`, `title_ru`, `title_uz`, `meta_title_*`, `meta_description_*`, `text_ru`,
`text_uz`. Shu kombinatsiyaning sahifasi bor → yangilanadi (faqat to'ldirilgan kataklar); yangi sahifa
`title_ru` siz → H1 = kalit so'z, `text_ru` siz → nofaol yaratiladi. Oyiga 10 tadan kam qidiriladigan qatorlar
o'tkazib yuboriladi (`--min-volume`). Oxirida o'tkazilgan qatorlar va 3 tadan kam tovarli sahifalar ro'yxati.

Sayt tomoni (Rasul): [`docs/mobile/filter_pages.md`](../mobile/filter_pages.md).
