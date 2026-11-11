# AI assistant (product search and advice)

A chat with an AI shopping assistant (Google Gemini): the customer writes what they need in Uzbek or Russian
("hammom uchun suvga chidamli kafel", "перфоратор бош подешевле"), the assistant searches the catalog, asks a
short question when the request is vague, and answers with a text plus **product cards**.

No auth required — guests can use it too. Two ways to talk to it, the same answers:

| | |
|---|---|
| `POST /api/v1/assistant/chat/` | one request → the whole answer (2–6 s) |
| `ws(s)://<api host>/ws/assistant/` | WebSocket: the text comes in pieces while it is written |
| `GET /api/v1/assistant/conversations/<id>/` | the messages of a conversation (to reopen the chat screen) |

Send as everywhere: `Authorization` (if logged in), `Accept-Language` (uz / ru), the `cart_token` /
`favourite_token` cookies (for `in_cart` / `is_favourite` of the cards), and **`X-Device-Id`** for a guest.

## Rules for the app

- **Product cards** are in `products` (same shape as [`products/`](products_list.md), `ProductSerializer`, live
  price and stock) + **`stock_status`** for the badge of the card. Show them under the answer text. The text never
  contains prices you must trust — the card does. The link of a card = the product page `/product/<slug>`.

  | `stock_status` | badge |
  |---|---|
  | `in_stock` | «В наличии» / «Mavjud» |
  | `low` | «Мало» / «Kam qoldi» (≤ 10) |
  | `check` | «Уточните наличие» / «Mavjudligini tekshiring» — the stock number from 1C is not reliable (≥ 500, a placeholder), the assistant never promises it |
  | `out_of_stock` | «Нет в наличии» / «Mavjud emas» |
- **Operator button**: `operator: true` → show «Operator bilan bog'lanish» / «Связаться с оператором» under the
  answer. The assistant sets it when a person must help (order status / changes, payment, delivery, returns,
  complaints, nothing found after searching, a masked card / phone). The button opens the contact sheet — phone,
  Telegram, working hours from `GET /api/v1/base/info/` (`phone_number`, `telegram_support`, `working_hours`).
  The answer text never contains the operator's phone or links.
- **Personal data**: phone and card numbers in the message are **masked before they are saved or sent to the
  AI** (`8600 **** **** 9012`, `+998 90 *** ** 67`). `question.text` is the message as saved — replace the
  customer's bubble with it; `question.pii_masked: true` → show the notice «Xavfsizlik uchun karta raqami va SMS
  kodni yozmang» and the operator button.
- The text is plain text (no markdown, no links). It has no product ids or markers.
- **Conversation**: the first answer returns `conversation_id`; send it with the next messages, the assistant
  remembers the last 10 messages. Start a new chat = do not send it. A `conversation_id` that is not the caller's
  is ignored (a new conversation starts).
- **Who the caller is**: the customer (token), else `X-Device-Id`, else the `cart_token` cookie, else the IP.
  A guest's conversations belong to that device id — send the same one every time.
- **Limits** (may change): 6 messages a minute → error `44`; a day 20 for a guest, 60 for a logged in customer →
  error `42`. A guest is also counted by the IP (20 a minute, 200 a day), so a new `X-Device-Id` does not reset it.
- **Budget**: when the month's / day's AI budget is spent the assistant answers error `41` until the next month /
  day — show the "switched off" screen with the operator contacts (`base/info/`).
- Message: 1–1000 characters.

## POST assistant/chat/

```json
{ "message": "perforator kerak, 30 mln gacha", "conversation_id": 15, "platform": "android" }
```

| Field | |
|---|---|
| `message` | required, 1–1000 chars |
| `conversation_id` | optional, from the previous answer |
| `platform` | optional: `site` / `ios` / `android` |

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

| Field | |
|---|---|
| `conversation_id` | send it with the next message |
| `message_id` | id of the answer |
| `question` | `{id, text, pii_masked}` — the customer's message as saved (phone / card numbers masked) |
| `text` | the answer, plain text |
| `operator` | `true` → show the operator button under the answer |
| `products` | product cards (`ProductSerializer` + `stock_status`), 0–8 |

`products` may be empty (the assistant asked a question, or nothing was found).

## WebSocket ws/assistant/

`wss://api.buildex.uz/ws/assistant/?token=<access token>&device_id=<X-Device-Id>&lang=uz`

| Parameter | |
|---|---|
| `token` | optional: the access JWT of a logged in customer. Bad / expired → the socket is closed with code **4001** (refresh the token and connect again) |
| `device_id` | the same value as the `X-Device-Id` header (guests) |
| `lang` | `uz` / `ru`; without it the handshake's `Accept-Language`, else ru |

The browser sends the cookies itself; the app may send a `Cookie` header with `cart_token`.

Client → server (one JSON message per question):

```json
{ "type": "message", "message": "perforator kerak", "conversation_id": 15, "platform": "ios" }
```

Server → client, in this order:

```json
{ "type": "start", "conversation_id": 15, "message_id": 342, "question": { "id": 341, "text": "perforator kerak", "pii_masked": false } }
{ "type": "tool", "name": "search_products" }
{ "type": "delta", "text": "Uy ishlari uchun " }
{ "type": "delta", "text": "Bosch GBH 2-26 mos keladi..." }
{ "type": "done", "conversation_id": 15, "message_id": 342, "question": { ... }, "text": "...", "operator": false, "products": [ ... ] }
```

| Type | |
|---|---|
| `start` | the question is accepted; keep `conversation_id`, replace the customer's bubble with `question.text` |
| `tool` | the assistant is searching (0 or more times) — show "Qidiryapman…" |
| `delta` | the next piece of the text: append it |
| `done` | the end: **replace** the streamed text with `done.text` (the final, cleaned one), show `products` and, when `operator` is true, the operator button |
| `error` | `{"type": "error", "error_code": 42, "detail": "..."}` — the answer is over |

One question at a time per socket: a `message` sent before `done` / `error` gets an `error` with code `5`.
The socket stays open between questions; reconnect after a network drop and keep sending `conversation_id`
(an answer that was being written when the socket dropped is still saved and comes with the history).

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

Oldest first, failed answers left out. Another customer's / device's conversation → `404` (`error_code` 4).

## Errors

| `error_code` | HTTP | |
|---|---|---|
| 5 | 400 | bad request (empty message, too long, a second message on the socket) |
| 41 | 503 | the assistant is switched off (or its budget is spent) — "Yordamchi vaqtincha ishlamayapti" + operator contacts |
| 42 | 429 | daily limit used up — "Bugungi limit tugadi, ertaga yozing" |
| 43 | 503 | the assistant could not answer now (AI service error) — "Qayta urinib ko'ring" |
| 44 | 429 | too many messages in a minute — "Biroz kuting va qayta yozing" |
