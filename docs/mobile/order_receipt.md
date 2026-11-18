# To'lov cheki (`ofd_url`) — mobile / sayt uchun

Karta bilan (Atmos) to'langan buyurtmaning fiskal cheki — Atmos OFD sahifasining havolasi. Backend uni buyurtmaga saqlaydi va buyurtma detalida qaytaradi; ilova uni "Chekni ko'rish" tugmasi qilib ochadi.

| Endpoint | Nima | `ofd_url` |
|---|---|---|
| `GET /api/v1/order/<id>/` | buyurtma detali | ✅ `result.ofd_url` |
| `POST /payment/hold/charge/` | muzlatilgan pulni yechish | ✅ javobning o'zida |
| `GET /api/v1/order/active/`, `GET /api/v1/order/history/` | ro'yxatlar | ❌ yo'q — chekni detaldan oling |

Swagger: `/swagger/` → **Order**, **Atmos**. Token kerak: `Authorization: Bearer <access_token>`.

## Chek qachon paydo bo'ladi

Atmos karta to'lovi ikki bosqichli:

1. **Muzlatish** — `POST /payment/hold/create/` `{"order_id": 401}`: kartadagi pul muzlatiladi (hold), hali yechilmaydi. Buyurtma **`status=0` (Yangi) da qoladi**, `payment_status=1` (to'lov kutilmoqda). **Chek yo'q** — `ofd_url: null`.
2. **Yechish** — operator buyurtmani admin panelda **Tasdiqlangan** (`status=1`) qilganda pulni **server o'zi yechadi**. Atmos chek yaratadi → `ofd_url` buyurtmaga yoziladi, `payment_status=2`. Ilova hech narsa chaqirmaydi.
3. Keyin operator buyurtmani Yig'ilmoqda (`status=2`) ga o'tkazadi.

Operator bekor qilsa (`status=6`) yoki mijoz buyurtmani bekor qilsa, muzlatilgan pul qaytariladi (`payment_status=3`). Muzlatish muddati cheklangan: shu vaqt ichida tasdiqlanmasa, pul Atmos tomonida o'zi qaytadi va chek bo'lmaydi.

> **Ilova `POST /payment/hold/charge/` ni chaqirmasin** (BLD-486). Endpoint eski versiyalar uchun qoldi: endi faqat mijozning o'z buyurtmasida ishlaydi (boshqa buyurtma → `404`) va buyurtma statusini **o'zgartirmaydi** (avval `3` ga o'tkazardi). `POST /payment/hold/cancel/` ham faqat o'z buyurtmasiga.

Shuning uchun `ofd_url`:
- `null` — buyurtma karta bilan to'lanmagan (naqd, Click, Payme, Uzum, do'konda to'lov) yoki pul hali faqat muzlatilgan;
- havola — pul yechilgan, chek bor.

Click / Payme / Uzum to'lovlarida `ofd_url` to'ldirilmaydi — bu maydon faqat Atmos uchun.

## `GET /api/v1/order/<id>/`

Faqat o'z buyurtmasi; boshqa mijozning yoki yo'q id → `404`.

```json
{
  "result": {
    "id": 401,
    "status": 3,
    "total_price": 1000.0,
    "payment_type": 0,
    "ofd_url": "https://ofd2.atmos.uz/api/ofd/K3Qyc243L2s5TVhWN3U2RE9kRWY5dXlqYVBmWXJhaTAvZWNiUVl6TmRibz0=",
    "created_at": "2026-11-17T16:11:50",
    "order_items": []
  },
  "ok": true
}
```

(Qisqartirilgan — buyurtma detalining boshqa maydonlari o'zgarmagan.)

| Maydon | Tur | Izoh |
|---|---|---|
| `ofd_url` | string (URL) \| null | Atmos chek sahifasi (`https://ofd2.atmos.uz/api/ofd/...`). Ochiq havola — login kerak emas. Bir marta yoziladi, keyin o'zgarmaydi. |

## `POST /payment/hold/charge/` javobi

Eski ilova versiyasi pulni o'zi yechsa, chek javobning o'zida keladi:

```json
{
  "message": "Payment successful",
  "ofd_url": "https://ofd2.atmos.uz/api/ofd/...",
  "transaction": {
    "trans_id": 123456,
    "amount": 100000,
    "total": 100000,
    "status_code": "0",
    "status_message": "Successful transaction",
    "pc_type": "HUMO"
  }
}
```

Bu endpoint `{"result", "ok"}` o'rami**siz** javob beradi (to'lov endpointlari shunday). `transaction.amount` / `total` — **tiyinda** (100000 = 1000 so'm). Xato bo'lsa — `400` va `{"error": "..."}` yoki Atmos javobi (`result.code`, `result.description`).

## Ilovada qilinadigan ishlar

1. Buyurtma detali ekranida `ofd_url` bo'lsa — "Chekni ko'rish" tugmasini ko'rsating; `null` bo'lsa — tugma yo'q.
2. Tugma havolani brauzerda yoki WebView'da ochadi (sahifa Atmos'niki, PDF emas).
3. Ro'yxat ekranlarida chek yo'q — kerak bo'lsa detalni oching.
4. Chek buyurtma tasdiqlangandan keyin paydo bo'ladi. Status o'zgarishi push bilan keladi (`order_status_push.md`), push kelganda detalni yangilash yetarli.
5. `hold/create/` dan keyin buyurtmani "To'lov kutilmoqda / Yangi" deb ko'rsating (`status=0`, `payment_status=1`), "Yig'ilmoqda" emas.
