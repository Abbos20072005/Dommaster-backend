# AI yordamchi (tovar qidirish va maslahat) — mobile / sayt uchun

AI yordamchi (Google Gemini) bilan chat. Mijoz nima kerakligini o'zbekcha yoki ruscha yozadi («hammom uchun suvga
chidamli kafel», «перфоратор бош подешевле»). Yordamchi katalogdan qidiradi, so'rov noaniq bo'lsa qisqa savol beradi
va matn bilan **tovar kartochkalarini** qaytaradi.

Login shart emas — mehmon ham foydalana oladi. Ikki usulda ishlaydi, javoblar bir xil:

| Endpoint | |
|---|---|
| `POST /api/v1/assistant/chat/` | bitta so'rov → butun javob (2–6 soniya) |
| `ws(s)://<api host>/ws/assistant/` | WebSocket: matn yozilayotgan paytda bo'laklab keladi |
| `GET /api/v1/assistant/conversations/<id>/` | suhbat xabarlari (chat ekranini qayta ochish uchun) |
| `GET /api/v1/base/info/` | operator kontaktlari (mavjud endpoint): `phone_number`, `telegram_support`, `working_hours` |

Hamma joydagidek yuboriladi: `Authorization` (login qilgan bo'lsa), `Accept-Language` (`uz` / `ru`), `cart_token` /
`favourite_token` cookie'lari (kartochkadagi `in_cart` / `is_favourite` uchun), mehmon uchun esa **`X-Device-Id`**.

## Ilova uchun qoidalar

- **Tovar kartochkalari** `products` da keladi: [`products/`](products_list.md) dagi bilan bir xil shakl
  (`ProductSerializer`, joriy narx va qoldiq) + kartochka belgisi uchun **`stock_status`**. Ularni javob matni ostida
  ko'rsating. Ishonish kerak bo'lgan narx matnda emas, kartochkada. Kartochka havolasi = tovar sahifasi
  `/product/<slug>`.
- **Qoldiq belgisi** — `stock_status` bo'yicha (o'zingiz `quantity` dan hisoblamang, chegaralar o'zgarishi mumkin):

  | `stock_status` | Belgi (uz / ru) | Qachon |
  |---|---|---|
  | `in_stock` | «Mavjud» / «В наличии» | qoldiq 11–499 |
  | `low` | «Kam qoldi» / «Мало» | qoldiq 1–10 |
  | `check` | «Mavjudligini tekshiring» / «Уточните наличие» | qoldiq 500 va undan ko'p — 1C'dan kelgan son ishonchsiz (placeholder 1000), yordamchi «bor» deb va'da bermaydi |
  | `out_of_stock` | «Mavjud emas» / «Нет в наличии» | qoldiq 0 |

  Hozir katalogdagi tovarlarning deyarli hammasi `check` bo'lib chiqadi — 1C haqiqiy qoldiqni yubormaguncha shunday.
- **Operator tugmasi**: `operator: true` → javob ostida «Operator bilan bog'lanish» / «Связаться с оператором»
  tugmasini ko'rsating. Yordamchi uni odam yordami kerak bo'lganda qo'yadi: buyurtma holati, uni o'zgartirish yoki bekor
  qilish, to'lov, yetkazib berish, qaytarish, shikoyat, ulgurji buyurtma, qidirsa ham tovar topilmasa. Shaxsiy ma'lumot
  yashirilgan bo'lsa ham `true` bo'ladi. Tugma kontakt oynasini ochadi: `GET /api/v1/base/info/` dan qo'ng'iroq
  (`phone_number`), Telegram (`telegram_support`), ish vaqti (`working_hours`). Javob matnida operatorning telefoni va
  havolasi bo'lmaydi.
- **Shaxsiy ma'lumot**: xabardagi shaxsiy ma'lumot **saqlashdan va AI'ga yuborishdan oldin** belgi bilan
  almashtiriladi (qiymatdan hech narsa qolmaydi):

  | Nima | Qoida | Belgi |
  |---|---|---|
  | Telefon | +998 / 998 va 9 raqam, yoki operator / shahar kodi bilan boshlanadigan 9 raqam (bo'shliq, chiziqcha, qavs bilan ham) | `[TELEFON]` |
  | Karta | 16 raqam (bo'shliq / chiziqcha bilan ham), Luhn tekshiruvidan o'tsa | `[KARTA]` |
  | Email | oddiy shakl | `[EMAIL]` |
  | JShShIR | ketma-ket 14 raqam | `[HUJJAT]` |
  | Pasport / ID karta | 2 lotin harf va 7 raqam (`AA1234567`, `AB 1234567`) | `[HUJJAT]` |
  | SMS kod | «kod / код / sms / смс / parol / пароль / code» yonidagi 4–6 raqam (`SMS kod: 123456`, `4821 kodi`); «artikul / mahsulot / tovar / shtrix» dan keyingi kod emas | `[KOD]` |

  Misol: `kartam 8600 1234 5678 9012, tel +998 90 123-45-67` → `kartam [KARTA], tel [TELEFON]`. Tovar raqamlariga
  tegilmaydi (`600x300x200`, `600 300 200`, 13 xonali shtrix-kod, narxlar, `artikul 12345678`, `mahsulot kodi 12345`);
  shuning uchun operator kodisiz 9 raqam telefon hisoblanmaydi. `question.text` — xabar saqlangan ko'rinishda: mijoz
  pufakchasidagi matnni shu bilan almashtiring. `question.pii_masked: true` → pufakcha ostida ogohlantirish (`pii_warning`
  matni) chiqaring: «Xavfsizlik uchun karta raqami, hujjat va SMS kodni yozmang» / «В целях безопасности не пишите номер
  карты, данные документа и SMS-код». AI'ga faqat xabar matnlari ketadi: mijoz id'si, IP, qurilma id'si, buyurtma
  ma'lumotlari yuborilmaydi.
- Javob matni oddiy matn: markdown yo'q, havola yo'q, tovar id'lari va belgilar yo'q.
- **Suhbat**: birinchi javob `conversation_id` qaytaradi — keyingi xabarlar bilan uni yuboring, yordamchi oxirgi 10 ta
  xabarni eslab qoladi. Yangi suhbat = `conversation_id` yubormaslik. Boshqa odamning `conversation_id` si e'tiborga
  olinmaydi (yangi suhbat boshlanadi).
- **Kim yozayotgani**: mijoz (token), bo'lmasa `X-Device-Id`, bo'lmasa `cart_token` cookie, bo'lmasa IP. Mehmonning
  suhbatlari shu device id'ga tegishli — har safar bir xil qiymatni yuboring.
- **Limitlar** (server sozlamasida, o'zgarishi mumkin):

  | Kim | Daqiqada | Kunda |
  |---|---|---|
  | Mehmon (`X-Device-Id`, bo'lmasa `cart_token`, bo'lmasa IP) | 6 → xato `44` | 20 → xato `42` |
  | Mehmonning IP manzili (yangi `X-Device-Id` limitni yangilamaydi) | 20 → `44` | 200 → `42` |
  | Login qilgan mijoz (faqat akkaunt bo'yicha) | 6 → `44` | 60 → `42` |
- **Byudjet**: oylik yoki kunlik AI byudjeti tugasa, yordamchi keyingi oy yoki ertangi kungacha xato `41` qaytaradi —
  «vaqtincha ishlamayapti» ekranini operator kontaktlari bilan ko'rsating.
- Xabar uzunligi: 1–1000 belgi.

## POST assistant/chat/

```json
{ "message": "perforator kerak, 30 mln gacha", "conversation_id": 15, "platform": "android" }
```

| Maydon | |
|---|---|
| `message` * | 1–1000 belgi |
| `conversation_id` | ixtiyoriy, oldingi javobdan |
| `platform` | ixtiyoriy: `site` / `ios` / `android` |

```json
{
  "result": {
    "conversation_id": 15,
    "message_id": 342,
    "question": { "id": 341, "text": "perforator kerak, 30 mln gacha", "pii_masked": false },
    "text": "Uy ishlari uchun Bosch GBH 2-26 mos keladi: 800 Vt, beton uchun yetarli. Arzonroq variant — Makita HR2470.",
    "operator": false,
    "products": [ { "id": 578, "name": "Perforator Bosch GBH 2-26", "price": 1500000.0, "discount_price": 1200000.0, "images": [ ... ], ..., "stock_status": "check" } ]
  },
  "ok": true
}
```

| Maydon | |
|---|---|
| `conversation_id` | keyingi xabar bilan yuboring |
| `message_id` | javob id'si |
| `question` | `{id, text, pii_masked}` — mijoz xabari saqlangan ko'rinishda (shaxsiy ma'lumot belgi bilan almashtirilgan) |
| `text` | javob, oddiy matn |
| `operator` | `true` → javob ostida operator tugmasi |
| `products` | tovar kartochkalari (`ProductSerializer` + `stock_status`), 0–8 ta |

`products` bo'sh bo'lishi mumkin (yordamchi savol bergan yoki hech narsa topilmagan).

## WebSocket ws/assistant/

`wss://api.buildex.uz/ws/assistant/?token=<access token>&device_id=<X-Device-Id>&lang=uz`

| Parametr | |
|---|---|
| `token` | ixtiyoriy: login qilgan mijozning access JWT'si. Noto'g'ri yoki eskirgan → socket **4001** kodi bilan yopiladi (tokenni yangilab qayta ulaning) |
| `device_id` | `X-Device-Id` sarlavhasidagi qiymat (mehmon uchun) |
| `lang` | `uz` / `ru`; bo'lmasa ulanishdagi `Accept-Language`, bo'lmasa ru |

Brauzer cookie'larni o'zi yuboradi; ilova `cart_token` bilan `Cookie` sarlavhasini yuborishi mumkin.

Client → server (har savol uchun bitta JSON xabar):

```json
{ "type": "message", "message": "perforator kerak", "conversation_id": 15, "platform": "ios" }
```

Server → client, shu tartibda:

```json
{ "type": "start", "conversation_id": 15, "message_id": 342, "question": { "id": 341, "text": "perforator kerak", "pii_masked": false } }
{ "type": "tool", "name": "search_products" }
{ "type": "delta", "text": "Uy ishlari uchun " }
{ "type": "delta", "text": "Bosch GBH 2-26 mos keladi..." }
{ "type": "done", "conversation_id": 15, "message_id": 342, "question": { ... }, "text": "...", "operator": false, "products": [ ... ] }
```

| Turi | |
|---|---|
| `start` | savol qabul qilindi: `conversation_id` ni saqlang, mijoz pufakchasini `question.text` bilan almashtiring |
| `tool` | yordamchi qidiryapti (0 yoki bir necha marta) — «Qidiryapman…» ko'rsating |
| `delta` | matnning navbatdagi bo'lagi — oxiriga qo'shing |
| `done` | tugadi: kelgan matnni `done.text` bilan **almashtiring** (yakuniy, tozalangan matn), `products` ni ko'rsating, `operator` true bo'lsa — operator tugmasini |
| `error` | `{"type": "error", "error_code": 42, "detail": "..."}` — javob tugadi |

Bitta socketda bir vaqtda bitta savol: `done` / `error` kelmasidan oldin yuborilgan `message` ga `5` kodli `error`
keladi. Socket savollar orasida ochiq turadi; tarmoq uzilsa qayta ulaning va `conversation_id` ni yuborishda davom
eting (uzilish paytida yozilayotgan javob baribir saqlanadi va tarixda chiqadi).

## GET assistant/conversations/<id>/

```json
{
  "result": {
    "conversation_id": 15,
    "messages": [
      { "id": 341, "role": "user", "text": "perforator kerak", "pii_masked": false, "operator": false, "created_at": "2026-11-09T12:00:00", "products": [] },
      { "id": 342, "role": "assistant", "text": "...", "pii_masked": false, "operator": true, "created_at": "2026-11-09T12:00:04", "products": [ ... ] }
    ]
  },
  "ok": true
}
```

Eskisidan yangisiga qarab, javob berilmagan xabarlarsiz. Boshqa mijoz yoki qurilmaning suhbati → `404`
(`error_code` 4). Tarixni ochganda ham har xabarning `operator` va `pii_masked` maydonlari bo'yicha tugma va
ogohlantirishni ko'rsating.

## Xatolar

Format: `{"detail": "...", "ok": false, "result": "", "error_code": 44}`; WebSocket'da
`{"type": "error", "error_code": 44, "detail": "..."}`.

| `error_code` | HTTP | Qachon / ekranda |
|---|---|---|
| 5 | 400 | noto'g'ri so'rov (bo'sh xabar, juda uzun, socketda ikkinchi xabar) |
| 41 | 503 | yordamchi o'chirilgan yoki byudjeti tugagan — «Yordamchi vaqtincha ishlamayapti» + operator kontaktlari; kirish nuqtasini yashirmang, ertaga yoki keyingi oy qayta ochiladi |
| 42 | 429 | kunlik limit tugadi — «Bugungi limit tugadi, ertaga yozing» |
| 43 | 503 | yordamchi hozir javob bera olmadi (AI xizmati xatosi) — «Qayta urinib ko'ring» |
| 44 | 429 | bir daqiqada juda ko'p xabar — «Biroz kuting va qayta yozing» |

## Ilova / sayt nima qilishi kerak

1. Har so'rovda `Accept-Language`, login bo'lsa `Authorization`, mehmon uchun doim bir xil `X-Device-Id` yuboring (WebSocket'da `token`, `device_id`, `lang` parametrlari).
2. Xabar yuborilgach, javobdagi `conversation_id` ni saqlang va keyingi xabarlar bilan yuboring. «Yangi suhbat» tugmasi = `conversation_id` siz yuborish.
3. Sayt uchun WebSocket'dan foydalaning: `delta` larni ketma-ket qo'shib boring, `tool` kelganda «Qidiryapman…» ko'rsating, `done` da matnni `done.text` bilan almashtiring. WebSocket ishlamasa, `POST assistant/chat/` ga o'ting.
4. Javob kelganda (`chat` javobi yoki WebSocket `start`) mijoz pufakchasidagi matnni `question.text` bilan almashtiring — yashirilgan ma'lumot (`[KARTA]`, `[TELEFON]` ...) ekranda ham ko'rinmasin.
5. `question.pii_masked: true` bo'lsa, pufakcha ostida ogohlantirish chiqaring: «Xavfsizlik uchun karta raqami, hujjat va SMS kodni yozmang».
6. Javob matni ostida `products` kartochkalarini ko'rsating. Kartochka belgisi `stock_status` bo'yicha bo'lsin: `check` holatida «Mavjudligini tekshiring» chiqsin, «Mavjud» emas. Kartochka bosilganda tovar sahifasi `/product/<slug>` ochilsin.
7. `operator: true` bo'lsa, javob ostida operator tugmasini ko'rsating. U `base/info/` ma'lumotlari bilan kontakt oynasini ochadi: qo'ng'iroq, Telegram, ish vaqti.
8. Har xato uchun o'z ekranini chiqaring (jadval yuqorida). `41` da kirish nuqtasini yashirmang — «vaqtincha ishlamayapti» ekrani va operator kontaktlari bo'lsin.
9. Chat ekranini qayta ochganda tarixni `conversations/<id>/` dan yuklang va har xabarning `operator` va `pii_masked` maydonlari bo'yicha tugma va ogohlantirishni ko'rsating.
