# Qo'llab-quvvatlash chati — client (ilova / sayt)

Base URL: `{{host}}/api/v1/base/`
Token: **ixtiyoriy**. Token bo'lsa — mijozning chati; tokensiz — mehmon chati (`chat_token` cookie bilan).

| Endpoint | Nima uchun |
| --- | --- |
| `GET chat/` | chatni ochish / xabarlarni olish |
| `POST chat/` | xabar yuborish (matn va / yoki rasm) |

Swagger: `/swagger/` → **Chat**.

> Chat bitta: mijozga bitta chat, mehmonga `chat_token` cookie bo'yicha bitta chat. Chat id'sini o'zingiz yubormaysiz — server aniqlaydi. Yuborilgan xabar xodimlarning Telegram guruhiga tushadi, operator esa admin paneldan javob yozadi ([admin hujjati](../admin/chat.md)).

---

## Chatni ochish

```
GET /api/v1/base/chat/
```

Javob — xabarlar ro'yxati:

```json
{
  "result": [
    {
      "id": 902,
      "chat": 14,
      "image": null,
      "message": "Buyurtmam qachon keladi?",
      "is_answer": false,
      "created_at": "2026-10-22T11:12:03.114820"
    },
    {
      "id": 903,
      "chat": 14,
      "image": "/media/chat/answer.jpg",
      "message": "Ertaga kuryer bog'lanadi.",
      "is_answer": true,
      "created_at": "2026-10-22T11:40:55.002001"
    }
  ],
  "ok": true
}
```

| Maydon | Izoh |
| --- | --- |
| `is_answer` | `false` = mijozning xabari, **`true` = operator javobi** |
| `message` | matn (`null` bo'lishi mumkin — faqat rasm yuborilgan bo'lsa) |
| `image` | rasm manzili yoki `null` |

### Ikki holatni hisobga oling

**1. Tokenli mijozda hali chat bo'lmasa**, birinchi `GET` **massiv emas**, chat obyektini qaytaradi:

```json
{ "result": { "id": 14, "customer": 51 }, "ok": true }
```

Chat shu chaqiriqda yaratiladi, keyingi `GET` oddiy (bo'sh) massiv beradi. Ya'ni `result` ni massiv deb hisoblamang — obyekt kelsa, uni "chat ochildi, xabar yo'q" deb o'qing.

**2. Tokensiz (mehmon)**: server `chat_token` cookie'ni o'qiydi, bo'lmasa yangi chat yaratib cookie'ni javobga qo'yadi (`Secure`, `SameSite=None`, `HttpOnly` emas). Shuning uchun mehmon **birinchi `GET chat/` ni qilmasdan yoza olmaydi** — cookie'siz `POST` `404` beradi. Ilova cookie'ni saqlab, keyingi so'rovlarda yuborishi kerak (sayt uchun `withCredentials`).

> Xabarlar tartibi backendda **kafolatlanmagan** (ro'yxatda `ordering` yo'q) va paginatsiya ham yo'q — hamma xabar bir martada keladi. Ekranda ko'rsatishdan oldin `created_at` bo'yicha o'zingiz saralang.

---

## Xabar yuborish

```
POST /api/v1/base/chat/
```

```json
{ "message": "Buyurtmam qachon keladi?" }
```

Rasm bilan — `multipart/form-data`: `image=<fayl>` (+ ixtiyoriy `message=`).

Javob — **`200`** (`201` emas), yaratilgan xabar:

```json
{ "result": { "id": 902, "chat": 14, "message": "Buyurtmam qachon keladi?", "image": null }, "ok": true }
```

- `chat` ni yuborish **kerak emas** — server o'zi qo'yadi (yuborilgani e'tiborga olinmaydi).
- `is_answer` javobda qaytmaydi, lekin `false` bo'lib saqlanadi (javoblarni faqat operator yozadi).
- **Bo'sh xabarni backend qaytarmaydi**: `message` ham, `image` ham bo'lmasa ham `200` keladi va bo'sh xabar yaratiladi. Shuning uchun **"yuborish" tugmasini ilovaning o'zi bloklashi kerak**.

---

## Operator javobi

- Javob kelganini bildiradigan **push yo'q**. Chat ekrani ochilganda va ochiq turganda `GET chat/` ni qayta so'rab turing (polling), websocket yo'q.
- **O'qilgan / o'qilmagan holati yo'q** — backend buni saqlamaydi. "Yangi javob" belgisini ilova o'zi hisoblaydi (masalan oxirgi ko'rilgan xabar id'sini local saqlab).
- Operator javobini o'zgartirishi yoki o'chirishi mumkin — ro'yxat qayta so'ralganda xabar o'zgargan yoki yo'q bo'lishi mumkin.

---

## Xatolar

Xatoda shakl: `{"detail": ..., "ok": false, "result": "", "error_code": N}`.

| Holat | HTTP | `error_code` | Izoh |
| --- | --- | --- | --- |
| Mehmon `POST` qildi, `chat_token` cookie yo'q | 404 | 4 (NOT_FOUND) | avval `GET chat/` ni chaqirib cookie oling |
| Cookie bor, lekin bunday chat yo'q (o'chirilgan) | 404 | 4 | cookie'ni tashlab, `GET chat/` bilan yangisini oching |
| Tokenli mijozda chat topilmadi | 404 | 4 | avval `GET chat/` (chatni yaratadi) |
| Yuborilgan ma'lumot yaroqsiz (masalan rasm fayli buzuq) | 400 | 5 (VALIDATION_FAILED) | `detail` ichida maydon xatosi |

---

## Eslatmalar

- Chat endpointlari **ochiq** (`auth_blocker` ro'yxatida yo'q): tokensiz ham ishlaydi.
- Mehmon chati keyin tizimga kirgan mijozga **ulanmaydi** — login qilgandan keyin chat bo'sh ko'rinadi, eski yozishmalar mehmon chatida qoladi. Agar bu kerak bo'lsa, backendda birlashtirish logikasi yozilishi kerak (hozir yo'q).
- Akkaunt o'chirilganda chat ham o'chadi — [delete_account.md](delete_account.md).
