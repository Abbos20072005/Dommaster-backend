# Mijoz manzillari — mobile / web uchun

Base URL: `{{host}}/api/v1/auth/`
Token kerak: `Authorization: Bearer <access_token>`. `Content-Type: application/json`.

```
GET    customer/addresses/        → ro'yxat
POST   customer/addresses/        → yangi manzil
PATCH  customer/addresses/<id>/   → o'zgartirish (faqat yuborilgan maydonlar)
DELETE customer/addresses/<id>/   → o'chirish
```

## Maydonlar

| Maydon | Tur | Majburiy | Dizayndagi nomi |
| --- | --- | --- | --- |
| `name` | string (≤ 150) | **ha** (create) | Название адреса |
| `location_name` | string (≤ 255) | yo'q | Улица и дом (xaritadagi belgidan) |
| `latitude`, `longitude` | number | yo'q | xaritadagi belgi |
| `apartment` | string (≤ 50) | yo'q | Квартира / офис |
| `intercom` | string (≤ 50) | yo'q | Домофон |
| `entrance` | string (≤ 20) | yo'q | Подъезд |
| `floor` | string (≤ 20) | yo'q | Этаж |
| `courier_comment` | string (≤ 500) | yo'q | Комментарий для курьера |
| `is_default` | bool | yo'q, faqat `PATCH` da | Сделать основным (`true` → boshqa manzillar default emas bo'ladi) |

- Yangi maydonlar (`apartment` … `courier_comment`) bo'sh bo'lsa `""` keladi. Bo'sh qiymat uchun `""` yuboring yoki maydonni yubormang — **`null` yubormang** (validatsiya xatosi).
- `entrance` / `floor` — matn (`"1"`, `"цоколь"`), son emas.
- `is_default` ni `POST` qabul qilmaydi: yangi manzilni asosiy qilish uchun yaratgandan keyin `PATCH {"is_default": true}` yuboring.

```bash
curl -X POST {{host}}/api/v1/auth/customer/addresses/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Объект на Чиланзаре",
    "location_name": "9-й квартал, 14",
    "latitude": 41.2856,
    "longitude": 69.2034,
    "apartment": "",
    "intercom": "",
    "entrance": "1",
    "floor": "1",
    "courier_comment": "Разгрузка с торца, есть грузовой лифт"
  }'
```

## Buyurtmada

`POST order/` da manzilning `apartment`, `intercom`, `entrance`, `floor`, `courier_comment` maydonlari buyurtmaga **nusxa** qilinadi. Shu sabab manzil keyin o'zgartirilsa yoki o'chirilsa ham, buyurtmada o'sha paytdagi qiymatlar qoladi. `GET order/<id>/` va buyurtmalar ro'yxatida shu 5 maydon buyurtmaning o'zida keladi. Ularni `order_location` ichidan emas, buyurtmaning o'zidan o'qing: `order_location` manzilning hozirgi holatini ko'rsatadi.
