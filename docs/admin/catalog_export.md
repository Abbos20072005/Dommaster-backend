# Faol katalog — PM Expert CRM uchun .xlsx havola

Menejer orqali (saytdan tashqari) qilingan sotuvni PM Expert CRM'ga kiritishda tovar shu ro'yxatdan
tanlanadi. Qo'lda oylik Excel o'rniga — doimiy havola, kuniga 1 marta o'zi yangilanadi.

## Havola

```
https://api.buildex.uz/api/v1/feeds/catalog.xlsx?token=<CATALOG_EXPORT_TOKEN>
```

- `token` = serverdagi `.env`'dagi `CATALOG_EXPORT_TOKEN` (taxmin qilib bo'lmaydigan tasodifiy qator).
  Noto'g'ri / yo'q token yoki `.env`'da bo'sh qiymat → **404** (havola o'chiq).
- Token so'rov parametri (`?token=`), yo'lda emas — backend'ning request log'iga tushmaydi.
- Token yangi qiymatga almashtirilsa, eski havola darhol ishlamay qoladi (gunicorn restart kerak) — PM Expert'ga
  yangisini berish kerak.
- Fayl `buildex_catalog_YYYY-MM-DD.xlsx` nomi bilan yuklab olinadi (sana = oxirgi qurilgan kun).
- `Last-Modified` / `If-Modified-Since` → 304: CRM URL'dan import qilsa, o'zgarmagan faylni qayta yuklamaydi.

CRM URL'dan import qila olmasa — shu havoladan oyiga 1 marta qo'lda yuklab, ularga yuboriladi.

## Fayl ichida

**«Каталог»** varag'i, 1-qator sarlavha, keyin har tovar bir qator (id bo'yicha tartib):

| Ustun | Nima |
| --- | --- |
| `ID` | saytdagi tovar id'si |
| `Наименование` | tovar nomi **ruscha** (`name_ru`) |
| `Цена, UZS` | savat oladigan narx: chegirma narxi bo'lsa — u, aks holda narx; butun so'm |
| `Ед. изм.` | o'lchov birligi: шт, м, см, кг, г, л, упак, компл |

**«Обновлено»** varag'i: `Обновлено` = fayl qurilgan sana va vaqt (`26.11.2026 05:10`, Toshkent),
`Товаров` = qatorlar soni.

Qo'shimcha ustunlar — faqat PM Expert so'rasa. **Berilmaydi**: tannarx, kirim narxi, ombor bo'yicha qoldiq,
yetkazib beruvchi.

## Qaysi tovarlar tushadi

Saytda sotilayotganlar: **faol** (`is_active`) va narxi > 0. Saytda ko'rinish faqat `is_active` bilan
belgilanadi; admin paneldagi `publish_status` (qoralama / ko'rib chiqish / nashr) saytga ta'sir qilmaydi, shuning
uchun bu yerda ham hisobga olinmaydi.

## Nom bo'yicha moslik

PM Expert skripti saytdagi xariddan tovarni faqat nom / soni / narx bilan oladi (id yo'q), shuning uchun moslik
**nom bo'yicha**. Saytning `purchase` eventidagi `item_name` shu fayldagi `Наименование` bilan bir xil bo'lishi
uchun sayt **har doim ruscha nomni** (`name_ru`) yuborishi kerak — uz tilidagi sahifada ham. Bu saytning ishi
(frontend), backend'dan emas.

Tovar nomi admin panelda yoki audit bo'yicha o'zgarsa, ertasi kungi faylda yangi nom bo'ladi; eski nom bilan
kiritilgan xaridlar CRM'da eski nomda qoladi.

## Qachon yangilanadi

Celery beat **har kuni 05:10** (Toshkent) qayta quradi (`tasks.build_catalog_export`). Qo'lda:

```bash
env/Scripts/python.exe manage.py build_catalog_export
```

Fayl `private/catalog.xlsx` (loyiha ildizida, `PRIVATE_ROOT`) — `media/` emas, chunki nginx `media/`'ni
hammaga beradi. Fayl hali yo'q bo'lsa, birinchi so'rov uni o'zi quradi; fayl bir qadamda almashtiriladi.

## Serverda bir marta

1. `.env`'ga `CATALOG_EXPORT_TOKEN=` qo'shish:
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. gunicorn + Celery worker + beat restart.
3. `manage.py build_catalog_export` (yoki birinchi so'rovni kutish).
4. To'liq havolani PM Expert'ga berish.
