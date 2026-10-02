# Buyurtma yaratish (order create) — mobile uchun

Base URL: `{{host}}/api/v1/`
Token kerak: `Authorization: Bearer <access_token>` (tokensiz → `401`). `Content-Type: application/json`.

```
POST order/
```

- Buyurtma **serverdagi savatdan** yaratiladi — mahsulotlar ro'yxati request'da yuborilmaydi.
- Savatdagi faqat **belgilangan** (`is_checked: true`) mahsulotlar buyurtmaga o'tadi va savatdan o'chadi; belgilanmaganlari savatda qoladi.
- Mijoz tokendan olinadi, ID yuborilmaydi.
- Swagger: `/swagger/` → **Order** → "Create order".

## Umumiy flow

```
1. GET  cart/                              → savat, narxlar (is_checked'larni tekshirish)
2. GET  auth/customer/addresses/           → manzil tanlash (address_id)
3. POST integration/yandex/check-price/    → yetkazish narxi (faqat delivery_type = 0)
   GET  base/branches/                     → filial tanlash (faqat delivery_type = 1)
4. POST base/promocode/checker/            → promokod bo'lsa, tekshirish (ixtiyoriy)
5. POST order/                             → order_id + to'lov havolasi   ✅
6. To'lov havolasini ochish (Click / Payme / Uzum) yoki payment_type = 4 bo'lsa tugadi
```

---

## Request

| Maydon | Tur | Majburiy | Izoh |
| --- | --- | --- | --- |
| `payment_type` | int | **ha** | `1` Click, `2` Payme, `3` Uzum Bank, `4` qabul qilganda to'lash |
| `payment_method` | string | yo'q | faqat `payment_type = 4` da ishlatiladi: `cash` yoki `card` |
| `delivery_type` | int | yo'q (default `0`) | `0` yetkazib berish, `1` olib ketish (pickup) |
| `address_id` | int | yo'q | mijozning manzili. Yuborilmasa default manzil olinadi |
| `branch_id` | int | `delivery_type = 1` da **ha** | olib ketiladigan filial (`GET base/branches/`), aktiv bo'lishi kerak |
| `delivery_price` | string | yo'q | yetkazish narxi (`yandex/check-price/` javobidan). `delivery_type = 0` da umumiy summaga qo'shiladi |
| `promocode` | string (≤ 15) | yo'q | promokod kodi |
| `receiver_name` | string (≤ 255) | yo'q | qabul qiluvchi ismi |
| `receiver_phone` | string (≤ 14) | yo'q | qabul qiluvchi telefoni |
| `is_web` | bool | yo'q | faqat web uchun (to'lovdan keyin saytga qaytarish). Mobile yubormaydi |

Muhim qoidalar:

- **`payment_type`** — faqat `1`–`4` yuboring. Boshqa qiymat validatsiyadan o'tib ketadi, lekin to'lov havolasi `null` bo'ladi.
- **`address_id`** yuborilsa, shu manzil mijozning **default** manzili bo'lib qoladi. Yuborilmasa va default manzil ham bo'lmasa → `404`. Manzil **pickup'da ham kerak** (`delivery_type = 1` bo'lsa ham default manzil yoki `address_id` bo'lishi shart).
- **`delivery_price`** — `"25000"`, `"25 000"`, `"25000.50"`, `"25,5"` yoki son (`25000`) qabul qilinadi. Bo'sh string (`""`) → validatsiya xatosi; narx yo'q bo'lsa maydonni umuman yubormang. Pickup'da yubormang.
- **`promocode`** — `promocode/checker/` dan o'tgan kodni **kichik harflarda** yuboring. Kod topilmasa xato qaytmaydi — buyurtma promokodsiz, to'liq narxda yaratiladi.
- **`branch_id`** ni faqat pickup'da yuboring.

Yetkazib berish + Click:

```bash
curl -X POST {{host}}/api/v1/order/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_type": 1,
    "delivery_type": 0,
    "address_id": 12,
    "delivery_price": "25000",
    "promocode": "sale10",
    "receiver_name": "Ali Valiyev",
    "receiver_phone": "998901234567"
  }'
```

Olib ketish + qabul qilganda naqd to'lash:

```bash
curl -X POST {{host}}/api/v1/order/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_type": 4,
    "payment_method": "cash",
    "delivery_type": 1,
    "branch_id": 3
  }'
```

---

## Response

Muvaffaqiyatli → `201 Created`. `result` — to'lov havolasi (string) yoki `null`; `order_id` `result` ichida emas, **yonida** keladi.

```json
{
  "result": "https://my.click.uz/services/pay?service_id=...&merchant_id=...&amount=175000.0&transaction_param=123",
  "order_id": 123,
  "ok": true
}
```

| `payment_type` | `result` | Buyurtma holati |
| --- | --- | --- |
| `1` Click | `https://my.click.uz/services/pay?...` | `status: 0` (Pending), to'lov kutilmoqda |
| `2` Payme | `https://checkout.paycom.uz/<base64>` | `status: 0` (Pending), to'lov kutilmoqda |
| `3` Uzum Bank | `https://www.uzumbank.uz/open-service?...` | `status: 0` (Pending), to'lov kutilmoqda |
| `4` qabul qilganda | `null` | darhol `status: 1` (Collecting), ombordagi qoldiq kamayadi |

`payment_type = 4` javobi:

```json
{ "result": null, "order_id": 124, "ok": true }
```

- Havolani brauzer / WebView / to'lov ilovasida oching. To'lov natijasini `GET order/<order_id>/` orqali tekshiring.
- To'lov qilinmay qolgan (Pending) buyurtma uchun yangi havola yoki boshqa to'lov turi: `POST order/pay/` (`order_id`, `payment_type`, `payment_method`).
- Buyurtma ma'lumotlari javobda kelmaydi — kerak bo'lsa `GET order/<order_id>/` dan oling.

### Summa qanday hisoblanadi

```
total_price = savat summasi (belgilangan mahsulotlar, chegirma narxi bilan)
              − promokod chegirmasi
              + delivery_price        (faqat delivery_type = 0)
```

- Promokod foizli bo'lsa: `savat × (1 − foiz / 100)`; summali bo'lsa: `savat − summa`.
- Hamma narx serverda hisoblanadi — klient yuborgan yagona summa `delivery_price`.
- Buyurtmadagi `products_total_price` — chegirmasiz summa, `saved_price` — mahsulot chegirmalaridan tejalgan summa.

---

## Xatolar

Xato formati:

```json
{
  "detail": "Customer location not found",
  "ok": false,
  "result": "",
  "error_code": 4
}
```

| Holat | HTTP | `error_code` | `detail` |
| --- | --- | --- | --- |
| Token yo'q yoki yaroqsiz | 401 | — | — (`{"result": "", "error": "Unauthorized access", "ok": false}`) |
| Mijozda savat yo'q | 404 | 4 | Cart not found |
| Validatsiya xatosi | 400 | 5 | obyekt (pastga qarang) |
| `address_id` topilmadi / default manzil yo'q | 404 | 4 | Customer location not found |
| Promokod muddati o'tgan | 400 | 19 | Promocode expired |
| Omborda mahsulot yetarli emas (`payment_type = 4`) | 400 | 21 | Product does not enough in warehouse |

Validatsiya (`error_code: 5`) — `detail` maydonlar bo'yicha obyekt:

```json
{
  "detail": { "payment_type": ["Обязательное поле."] },
  "ok": false,
  "result": "",
  "error_code": 5
}
```

| Holat | `detail` |
| --- | --- |
| `payment_type` yuborilmagan | `{"payment_type": ["Обязательное поле."]}` |
| `delivery_type = 1`, `branch_id` yo'q | `{"non_field_errors": ["branch_id is required for pickup delivery"]}` |
| Filial topilmadi yoki aktiv emas | `{"non_field_errors": ["Market branch not found"]}` |
| `delivery_price` noto'g'ri yoki bo'sh string | `{"delivery_price": ["Некорректная цена доставки"]}` |

> Xatoni aniqlashda xabar matniga emas, `error_code` ga tayaning (`detail` matni o'zgarishi mumkin).

> **`error_code: 21` haqida:** bu xato kelganda buyurtma **allaqachon yaratilgan** (`status: 0`) va belgilangan mahsulotlar savatdan o'chgan bo'ladi, lekin javobda `order_id` yo'q. So'rovni qayta yubormang — buyurtmani `GET order/active/` dan toping va kerak bo'lsa `POST order/<id>/cancel/` bilan bekor qiling.

---

## Eslatmalar

- So'rovdan oldin savatda kamida bitta belgilangan mahsulot borligini tekshiring — server buni tekshirmaydi, bo'sh buyurtma yaratilib qoladi.
- Muvaffaqiyatli javobdan keyin savatni qayta yuklang (`GET cart/`) — belgilangan mahsulotlar o'chgan bo'ladi.
- Buyurtmani bekor qilish: `POST order/<id>/cancel/` — faqat `status` `0` yoki `1` bo'lganda.
- Buyurtmalar ro'yxati: `GET order/active/`, `GET order/history/`.
- Holatlar: `status` — `0` Pending, `1` Collecting, `2` Delivering, `3` Completed, `4` Canceled.
