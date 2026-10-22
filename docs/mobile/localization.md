# Katalog javoblarining tili (uz / ru)

Base URL: `{{host}}/api/v1/`

Mijoz API'sidagi hamma matn `Accept-Language` sarlavhasiga qarab qaytadi. Oldin mahsulotning o'zi (nomi, tavsiflari, atributlari) tilga moslangan edi, lekin brend nomi, qidiruv taklifari va kategoriya menyusi har doim **ru** chiqardi — endi ular ham tilga moslangan.

## Til qanday aniqlanadi

- `Accept-Language` dagi birinchi ma'lum til olinadi: `uz`, `ru`; `uz-UZ` → `uz`, to'liq brauzer sarlavhasi (`uz-UZ,uz;q=0.9,ru;q=0.8`) ham ishlaydi.
- Sarlavha yo'q yoki boshqa til (`en` va h.k.) → **ru**.
- Tanlangan tildagi qiymat bo'sh bo'lsa → **ru** ga tushadi (hech qachon bo'sh string qaytmaydi). Shuning uchun `name_uz` to'ldirilmagan mahsulot/kategoriya uz tilida ham o'qiladigan nom bilan keladi.

## Nima o'zgardi

| Joy | Oldin | Hozir |
| --- | --- | --- |
| Mahsulot kartasidagi `brand.name` (`products/`, `products/<id>/`, `product/filter/`, savat, sevimlilar, buyurtma) | doim ru | so'rov tili |
| `GET brands/`, `GET brands/?item_category_id=`, `GET brands/<id>/` → `name` | doim ru (detalda bo'sh uz bo'sh qaytardi) | so'rov tili |
| `GET products/most-sold/` → `name` | doim ru | so'rov tili |
| `GET products/most-search/` → ro'yxat | doim ru | so'rov tili |
| `GET search/?q=` → `products` | doim ru | so'rov tili |
| `GET categories/` (menyu / daraxt / brend bo'yicha) → har uch darajadagi `name` | doim ru | so'rov tili |
| `GET main/` → `addsbrands.name` va ichidagi mahsulot nomlari | doim ru | so'rov tili |
| Mahsulot detalidagi `variant_groups[].name` / `items[].display_value` | tilga moslangan, lekin bo'sh uz → bo'sh string | bo'sh uz → ru |
| Kategoriya detali (`categories/<id>/`, `sub-categories/<id>/`, `item-categories/<id>/`) → `name` | bo'sh uz → bo'sh string | bo'sh uz → ru |

Qidirishning o'zi avvalgidek ikkala tilda ishlaydi (`name_uz` va `name_ru` bo'yicha), faqat javobdagi nom endi so'rov tilida.

## Avvaldan tilga moslangan (o'zgarmagan)

- Mahsulot: `name`, `short_description`, `description`, `slug`, `meta_title`, `meta_description`, `images[].alt`, `attributes` / `characteristics` (nomi, qiymati, `Ha` / `Да`), `breadcrumbs`.
- Kategoriyalar va brend: `slug`, `meta_title`, `meta_description`, `image_alt`.
- Filtrlar (`product/filter/` → `available_filters`, `quick_filters`), SEO filter sahifalari, `home/` bloklari sarlavhalari, bannerlar.

## Hali ham tilga bog'liq emas

- Mahsulotning `unit` (o'lchov birligi) — 1C beradigan erkin matn, tarjimasi yo'q.
- Buyurtma holati pushlari — faqat ru (mijozning tili saqlanmaydi).
- `services/` nomi va tavsifi — bo'sh uz bo'sh qaytaradi (eski xatti-harakat saqlangan).

## Eski ilova versiyalari buziladimi

Yo'q — maydonlar, ularning nomlari va javob shakli o'zgarmagan, faqat qiymat so'rov tilida keladi. `Accept-Language` yubormaydigan mijozlar avvalgidek ru oladi.

## Deploydan keyin

Keshlangan javoblarning kalitiga til qo'shildi (`home:main:data`, `products:most_sold`, `products:most_search`, `search:v2:<q>`, `categories:list:brand=…`, `categories:lists`, `categories:list:item:category=…`). Eski kalitlar o'qilmaydi, shuning uchun birinchi so'rovlar keshni qaytadan to'ldiradi — alohida amal talab qilinmaydi.
