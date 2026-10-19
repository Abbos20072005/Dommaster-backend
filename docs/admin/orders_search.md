# Buyurtmalar qidiruvi — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>`.

`GET orders/?search=<matn>` — bitta maydon, beshta narsa bo'yicha qidiradi. Qolgan filtrlar (`status`, `from_created`, `manager`, ...), `ordering` va paginatsiya bilan birga ishlaydi; `orders/stats/?search=` ham xuddi shu qidiruvni hisobga oladi.

| Nima bo'yicha | Misol | Qanday mos keladi |
| --- | --- | --- |
| Buyurtma raqami | `28 610`, `28610`, `#28610` | `id` aynan teng |
| Telefonning istalgan qismi | `45 67`, `+998 90 123` | mijoz yoki qabul qiluvchi telefonida shu raqamlar ketma-ket uchraydi |
| Mijoz ismi | `Jamshid Karimov` | har bir so'z mijoz ismida yoki qabul qiluvchi ismida bor |
| Mahsulot nomi | `Avtomat NXB-63` | buyurtmadagi **bitta** mahsulot nomida (uz / ru) har bir so'z bor |
| SKU | `CHT-NXB63-1P-C16` | buyurtmadagi mahsulotning artikuli, 1C kodi yoki shtrix-kodida uchraydi |

## Qoidalar

- **Faqat raqamlardan iborat so'rov** (probel, `+`, `-`, qavs, `#`, `№` tashlab yuboriladi: `45 67` → `4567`) — raqam deb olinadi: buyurtma raqami **yoki** telefon qismi **yoki** mahsulot kodining (artikul / 1C kodi / shtrix-kod) qismi. Mijoz ismi va mahsulot nomi bo'yicha qidirilmaydi.
- **Qolgan har qanday so'rov** — matn: probel bo'yicha so'zlarga bo'linadi, hamma so'z topilishi shart. Mijoz / qabul qiluvchi ismi **yoki** buyurtmadagi bitta mahsulotning nomi va kodlari bo'yicha.
- Katta-kichik harf farqi yo'q, so'zning bir qismi ham yetarli (`karim` → `Karimov`).
- Bo'sh `search` — filtr yo'q.
- Natija tartibi o'zgarmaydi (`ordering`, default — yangilari birinchi): raqam bo'yicha qidirilganda aynan shu raqamli buyurtma ro'yxatning boshida bo'lishi shart emas.

## Misollar

```
GET orders/?search=28 610
GET orders/?search=45 67
GET orders/?search=Jamshid Karimov
GET orders/?search=Avtomat NXB-63&status=0&status=1
GET orders/?search=CHT-NXB63-1P-C16
```

Javob — odatdagi buyurtmalar ro'yxati (`count`, `next`, `previous`, `next_page`, `previous_page`, `results`).
