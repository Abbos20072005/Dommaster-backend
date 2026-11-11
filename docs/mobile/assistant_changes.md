# AI yordamchi — o'zgarishlar (mobile / sayt uchun)

AI yordamchi API'siga yangi maydonlar va xatolar qo'shildi (BLD-400, BLD-405, tool'lar taski, «AI Yordamchi 6» dizayni).
To'liq kontrakt: `docs/mobile/assistant.md`. Eski maydonlar o'chirilmagan — eski front buzilmaydi, faqat yangi holatlarni ko'rsatmaydi.

## Nima o'zgardi

| Endpoint | Oldin | Hozir | Eski front buziladimi |
|---|---|---|---|
| `POST /api/v1/assistant/chat/` → `result` | `conversation_id`, `message_id`, `text`, `products` | + `question` `{id, text, pii_masked}`, + `operator` (bool) | Yo'q |
| `products[]` (chat, WebSocket `done`, conversations) | `ProductSerializer` | + `stock_status`: `in_stock` / `low` / `check` / `out_of_stock` | Yo'q |
| WebSocket `start` eventi | `conversation_id`, `message_id` | + `question` `{id, text, pii_masked}` | Yo'q |
| WebSocket `done` eventi | chat `result` bilan bir xil | + `question`, + `operator` | Yo'q |
| `GET /api/v1/assistant/conversations/<id>/` → `messages[]` | `id, role, text, created_at, products` | + `pii_masked`, + `operator` | Yo'q |
| Xato `41` | assistent o'chirilgan | o'chirilgan **yoki** oylik / kunlik AI byudjeti tugagan (keyingi oy / ertangi kungacha) | Yo'q — matn o'zgaradi (pastda) |
| Xato `44` (yangi, HTTP 429) | — | bir daqiqada juda ko'p xabar (6 tadan ortiq) | Eski front uni noma'lum xato deb ko'rsatadi |
| Foydalanuvchi matni | qanday yozilsa shunday saqlanardi | karta va telefon raqami **saqlashdan oldin** yashiriladi | Yo'q |

## Yangi maydonlar

### `question`

```json
"question": { "id": 341, "text": "kartam 8600 **** **** 9012, pul yechildi", "pii_masked": true }
```

| Maydon | |
|---|---|
| `id` | foydalanuvchi xabarining id'si |
| `text` | xabar **saqlangan ko'rinishda**: karta raqami `8600 **** **** 9012`, telefon `+998 90 *** ** 67` ko'rinishida |
| `pii_masked` | `true` = xabarda karta yoki telefon raqami bor edi va u yashirildi |

Tovar raqamlariga tegilmaydi: `600x300x200`, `600 300 200`, 13 xonali shtrix-kod, narxlar o'zgarmaydi. SMS kodlarni aniqlab bo'lmaydi.

### `operator`

`true` → javob ostida «Operator bilan bog'lanish» / «Связаться с оператором» tugmasi chiqadi. Assistent uni quyidagi
hollarda qo'yadi: buyurtma holati, uni o'zgartirish yoki bekor qilish, to'lov, yetkazib berish, qaytarish, shikoyat,
ulgurji buyurtma, qidirsa ham tovar topilmasa. Karta yoki telefon yashirilgan bo'lsa (`pii_masked`) ham `true` bo'ladi.

Tugma kontakt oynasini ochadi. Ma'lumot mavjud endpointdan olinadi: `GET /api/v1/base/info/` → `phone_number`
(qo'ng'iroq), `telegram_support` (Telegram), `working_hours` (ish vaqti). Javob matnida operatorning telefoni va
havolasi bo'lmaydi.

### `stock_status` (tovar kartochkasida)

| Qiymat | Belgi (uz / ru) | Qachon |
|---|---|---|
| `in_stock` | «Mavjud» / «В наличии» | qoldiq 11–499 |
| `low` | «Kam qoldi» / «Мало» | qoldiq 1–10 |
| `check` | «Mavjudligini tekshiring» / «Уточните наличие» | qoldiq 500 va undan ko'p — 1C'dan kelgan son ishonchsiz (placeholder 1000), assistent «bor» deb va'da bermaydi |
| `out_of_stock` | «Mavjud emas» / «Нет в наличии» | qoldiq 0 |

Hozir katalogdagi tovarlarning deyarli hammasi `check` bo'lib chiqadi — 1C haqiqiy qoldiqni yubormaguncha shunday
bo'ladi. Chegaralar (10 va 500) PM bilan kelishiladi va o'zgarishi mumkin; front `stock_status` ni o'qisin, `quantity`
bo'yicha o'zi hisoblamasin.

## Limitlar

| Kim | Daqiqada | Kunda |
|---|---|---|
| Mehmon (`X-Device-Id`, yo'q bo'lsa `cart_token`, yo'q bo'lsa IP) | 6 → xato `44` | 20 → xato `42` |
| Mehmonning IP manzili (yangi `X-Device-Id` limitni yangilamaydi) | 20 → `44` | 200 → `42` |
| Login qilgan mijoz (faqat akkaunt bo'yicha) | 6 → `44` | 60 → `42` |

Raqamlar server sozlamasida turadi va o'zgarishi mumkin.

## Xatolar

| `error_code` | HTTP | Ekranda |
|---|---|---|
| 41 | 503 | «Yordamchi vaqtincha ishlamayapti» + operator kontaktlari (`base/info/`) — kirish nuqtasini yashirmang, byudjet ertaga yoki keyingi oy qayta ochiladi |
| 42 | 429 | «Bugungi limit tugadi, ertaga yozing» |
| 43 | 503 | «Hozir javob bera olmadim, qayta urinib ko'ring» |
| 44 | 429 | «Biroz kuting va qayta yozing» (yangi) |

Xato formati o'zgarmagan: `{"detail": "...", "ok": false, "result": "", "error_code": 44}`. WebSocket'da:
`{"type": "error", "error_code": 44, "detail": "..."}`.

## Frontda qilinadigan ishlar

1. Javob kelganda (`chat` javobi yoki WebSocket `start`) foydalanuvchi pufakchasidagi matnni `question.text` bilan almashtiring — yashirilgan karta yoki telefon ekranda ham ko'rinmasin.
2. `question.pii_masked: true` bo'lsa, pufakcha ostida ogohlantirish chiqaring: «Xavfsizlik uchun karta raqami va SMS kodni yozmang» / «В целях безопасности не пишите номер карты и SMS-код».
3. `operator: true` bo'lsa, javob ostida operator tugmasini ko'rsating. U `base/info/` ma'lumotlari bilan kontakt oynasini ochadi: qo'ng'iroq, Telegram, ish vaqti.
4. Tovar kartochkasidagi belgini `stock_status` bo'yicha chiqaring (jadval yuqorida). `check` holatida «Уточните наличие» chiqsin, «В наличии» emas.
5. Xato `44` uchun «biroz kuting» xabarini qo'shing.
6. Xato `41` da kirish nuqtasini yashirmang: «vaqtincha ishlamayapti» ekrani va operator kontaktlarini ko'rsating.
7. Suhbat tarixini (`conversations/<id>/`) qayta ochganda ham har xabarning `operator` va `pii_masked` maydonlari bo'yicha tugma va ogohlantirishni ko'rsating.
