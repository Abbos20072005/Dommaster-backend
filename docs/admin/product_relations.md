# Bog'liq mahsulotlar (related / alternative / cross-sell) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

Alohida endpoint yo'q — bog'lanishlar mahsulotning o'zida, uchta maydon sifatida keladi va yoziladi:

| Endpoint | Nima uchun |
| --- | --- |
| `GET products/{id}/` | mahsulot + uning bog'langan mahsulotlari |
| `PATCH products/{id}/` | bog'lanishlarni o'zgartirish |
| `POST products/` | mahsulot yaratishda birga yuborish ham mumkin |

Swagger: `/swagger/admin/` → **products**.

---

## Uch tur

| Maydon | Ma'nosi | Misol |
| --- | --- | --- |
| `related_products` | Bog'liq — shu mahsulot bilan birga olinadigan (mahsulot sahifasi) | plitka → yelim, zatirka |
| `alternative_products` | Muqobil — shu mahsulot o'rniga olinadigan (mahsulot sahifasi) | drel → boshqa brendning shunday dreli |
| `cross_sell_products` | Cross-sell — mahsulot savatda turganda taklif qilinadigan | bo'yoq → valik, lenta |

Bog'lanish **bir tomonlama**: A mahsulotga B ni qo'shish B ning ro'yxatiga A ni qo'shmaydi. Ikki tomonlama kerak bo'lsa, B mahsulotda ham alohida qo'shiladi.

---

## Obyekt

`GET products/{id}/` javobida (qolgan maydonlar qisqartirilgan):

```json
{
  "id": 571,
  "related_products": [
    {
      "id": 573,
      "name": "Выключатель 3-клавишный Schneider Electric Asfora Антрацит",
      "image": "https://.../media/product_image/shnider_3.jpg",
      "product_code": null,
      "articul_code": "EPH2100171",
      "price": 47610.0,
      "discount_price": null,
      "quantity": 992,
      "is_active": true
    }
  ],
  "alternative_products": [],
  "cross_sell_products": []
}
```

| Maydon | Izoh |
| --- | --- |
| `image` | asosiy (birinchi) rasm; rasmi yo'q bo'lsa `null` |
| `quantity`, `is_active` | qoldiq va holat — tugagan / o'chirilgan mahsulotni formada belgilash uchun |

Ro'yxat tartibi — admin panelda qo'yilgan tartib. Mahsulotlar ro'yxatida (`GET products/`) bu maydonlar **yo'q**, faqat detailda.

---

## Yozish

`PATCH products/{id}/`

```json
{
  "related_products": [{ "id": 573 }, { "id": 572 }],
  "alternative_products": [574]
}
```

- Element: `{"id": 573}` yoki shunchaki `573`.
- Yuborilgan ro'yxat shu turdagi bog'lanishlarni **to'liq almashtiradi**; ro'yxatdagi tartib saqlanadi.
- Yuborilmagan tur o'zgarmaydi (yuqoridagi misolda `cross_sell_products` joyida qoladi).
- Bo'sh ro'yxat `[]` — shu turdagi hamma bog'lanishni olib tashlaydi.
- Bitta mahsulot bir nechta turda bo'lishi mumkin (masalan `related_products` va `cross_sell_products` da).
- Har bir turda ko'pi bilan **20 ta** mahsulot.
- Forma uchun mahsulot qidirish: `GET products/?search=<nom / kod / artikul / shtrixkod>`.

Xatolar (`400`):

- `{"related_products": ["A product can't be linked to itself."]}` — mahsulot o'ziga bog'lanmaydi
- `{"related_products": ["Products must be unique."]}` — bitta ro'yxatda mahsulot takrorlangan
- `{"related_products": [{"id": "Object with id=999 does not exist."}]}` — bunday mahsulot yo'q
- `{"related_products": {"non_field_errors": ["Ensure this field has no more than 20 elements."]}}` — 20 tadan ko'p

---

## Bilish kerak

- Nofaol (`is_active=false`) yoki tugagan mahsulotni ham bog'lash mumkin — ro'yxatda qoladi, admin panel uni `is_active` / `quantity` bo'yicha belgilab ko'rsatishi mumkin.
- Mahsulot o'chirilsa, uning bog'lanishlari ham (ikkala tomondan) o'chadi.
- 1C sinxronlash bog'lanishlarga tegmaydi.

> Bog'lanishlar hozircha faqat admin API'da — mijoz (sayt / ilova) API'lariga chiqarilmagan, ya'ni kiritilgan ro'yxatlar hali hech qayerda ko'rinmaydi.
