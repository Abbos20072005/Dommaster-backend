# Savat, buyurtma va parol bilan kirish tekshiruvlari — mobile / sayt uchun

**13.11.2026 dan** (BLD-441, pentest natijasi) server noto'g'ri qiymatlarni qabul qilmaydi. To'g'ri ishlayotgan ilova / sayt uchun hech narsa o'zgarmaydi. Endpoint'lar, maydonlar va javob shakli avvalgidek.

## Nima o'zgardi

| Endpoint | Endi rad etiladi | Javob | Eski front buziladimi |
| --- | --- | --- | --- |
| `POST cart/item/` | `quantity` < 1 (0, manfiy) | 400, `error_code` 5 | yo'q |
| `PATCH cart/item/` | `quantity` < 0 (`0` avvalgidek tovarni savatdan o'chiradi) | 400, `error_code` 5 | yo'q |
| `POST order/` | `delivery_price` manfiy | 400, `error_code` 5 | yo'q |
| `POST order/` | `payment_type` 0–4 dan tashqari (`0` = hali tanlanmagan — avvalgidek qabul qilinadi) | 400, `error_code` 5 | yo'q |
| `POST order/` | `delivery_type` 0 yoki 1 emas | 400, `error_code` 5 | yo'q |
| `POST order/` | savatda belgilangan (`is_checked`) tovar yo'q | 400, **`error_code` 46** «No checked products in the cart» | yo'q — avval 0 so'mlik bo'sh buyurtma yaratilardi |
| `POST auth/login/` (eski, parol bilan) | telefon raqami SMS kod bilan tasdiqlanmagan mijoz | 403, **`error_code` 45** «Phone number is not verified» | yo'q — sayt ham, ilova ham `auth/phone/` → `otp/verify/` bilan kiradi |
| `POST auth/register/` (eski) | `role` yuborilsa e'tiborsiz qoldiriladi, mijoz doim `user` | 201, avvalgidek | yo'q |

Summadagi promokod savat summasidan katta bo'lsa, buyurtma summasi 0 bo'ladi (avval manfiy chiqardi).

## Frontga tavsiya
- **46**: "Savatda tanlangan tovar yo'q" deb ko'rsating va savatga qaytaring. Odatda "Buyurtma berish" tugmasi bo'sh savatda o'chirilgan bo'lsa, bu xato chiqmaydi.
- **45**: parol bilan kirish oynasi qolgan bo'lsa, foydalanuvchini SMS kod bilan kirishga (`auth/phone/`) yo'naltiring.
