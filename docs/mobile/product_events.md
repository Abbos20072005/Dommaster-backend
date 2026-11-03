# Tovar voronkasi hodisalari — sayt va ilova uchun

BLD-371 / 372: har bir tovar bo'yicha voronka — **ko'rish → savatga qo'shish → rasmiylashtirish boshlanishi → xarid**. Sayt va ilova hodisalari bitta joyda (backendda) sanaladi, GA4 ishlatilmaydi. Ma'lumot klient shu hodisalarni yubora boshlagan kundan yig'iladi — o'tmish tiklanmaydi, shuning uchun imkon qadar tezroq chiqaring.

| Hodisa | Kim yozadi | Klientdan nima kerak |
| --- | --- | --- |
| `product_view` | backend, `POST /api/v1/events/` kelganda | **yangi chaqiruv** |
| `add_to_cart` | backend, `POST /api/v1/cart/item/` da o'zi | mavjud so'rovga `platform` qo'shish |
| `checkout_start` | backend, `POST /api/v1/events/` kelganda | **yangi chaqiruv** |
| `purchase` | buyurtmalardan olinadi | hech narsa |

Hamma so'rovlarda:
- `platform` = `site` | `ios` | `android` (buyurtmadagi `channel` bilan bir xil qiymatlar).
- Login qilmagan foydalanuvchi uchun `X-Device-Id` header (ilova allaqachon yuboradi; **sayt** — localStorage'da saqlangan uuid, har so'rovda bir xil). Login qilgan bo'lsa token yetarli.
- Ism, telefon, manzil yuborilmaydi va saqlanmaydi.

## `POST /api/v1/events/`

Auth kerak emas (token bo'lsa yuboring — hodisa mijozga bog'lanadi).

### Tovar kartasi ochildi

```json
{"type": "product_view", "product_id": 1234, "platform": "site"}
```

- **Sayt (Rasul):** faqat **brauzerdan**, sahifa ko'rsatilgandan keyin (`useEffect` / mount). SSR serverdan, `generateMetadata`, prefetch yoki `<Link prefetch>` dan **yubormang** — aks holda ikki marta sanaladi. Bir ochilishga bitta so'rov.
- **Ilova (Dilshodbek):** tovar ekrani ochilganda bitta so'rov. Orqaga qaytib shu ekranga qayta kirish = yangi ko'rish.
- Javobni kutmang, xatosini foydalanuvchiga ko'rsatmang (fire-and-forget).

### Rasmiylashtirish boshlandi

```json
{"type": "checkout_start", "platform": "ios"}
```

Rasmiylashtirish (checkout) sahifasi / ekrani ochilganda bitta so'rov. `product_id` yuborilmaydi: backend savatdagi **belgilangan** (`is_checked`) tovarlarni o'zi oladi — login bo'lsa mijozning savati, bo'lmasa `cart_token` cookie'sidagi savat. Savat bo'sh bo'lsa hech narsa yozilmaydi.

### Javob

```json
{"result": "accepted", "ok": true}
```

Doim `200` (bot, takror va hokazo bo'lsa ham — hodisa shunchaki yozilmaydi). Noto'g'ri body → `400`, `error_code` = validation:

```json
{"detail": {"product_id": ["required for product_view"]}, "ok": false, "result": "", "error_code": 5}
```

## Savatga qo'shish — `POST /api/v1/cart/item/`

Mavjud so'rov o'zgarmaydi, body'ga faqat `platform` qo'shiladi:

```json
{"product": 1234, "quantity": 1, "platform": "android"}
```

Backend muvaffaqiyatli qo'shilgan har bir tovar uchun `add_to_cart` yozadi. `platform` yuborilmasa ham qo'shish ishlaydi, faqat hodisa kanalsiz (noma'lum) yoziladi — voronkada sayt / ilovaga tushmaydi. Miqdorni o'zgartirish (`PATCH cart/item/`) savatga qo'shish emas, sanalmaydi.

## Nima sanalmaydi

- Botlar: `product_view` / `checkout_start` faqat brauzer JS'idan (sahifa ko'rsatilgandan keyin) yoki ilovadan keladi, bot JS ishlatmaydi va bu so'rovni yubormaydi. Shuning uchun SSR'dan yubormaslik muhim.
- Prefetch so'rovlari (`Sec-Purpose: prefetch`, `Purpose: prefetch`).
- Bitta foydalanuvchi (token yoki `X-Device-Id`) bir tovar bo'yicha bir xil hodisani **30 soniya ichida** qayta yuborsa — bitta deb olinadi (qayta render, ikki marta bosish). Shuning uchun keyin qayta ochish baribir yangi ko'rish bo'ladi.

## Tekshirish uchun

```bash
curl -X POST https://api.buildex.uz/api/v1/events/ -H "Content-Type: application/json" -H "X-Device-Id: test-123" -d "{\"type\": \"product_view\", \"product_id\": 1234, \"platform\": \"site\"}"
```
