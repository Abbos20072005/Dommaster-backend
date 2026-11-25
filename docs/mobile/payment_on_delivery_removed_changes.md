# Naqd to'lov («Оплата при получении») olib tashlandi — mobile / sayt uchun

**25.11.2026 dan** (launch audit B-03, qaror 25.11): checkout'da faqat **karta bilan onlayn** to'lov qoladi. «Наличные — оплата при получении» (va do'konda to'lash) endi yo'q — yetkazib berishda ham, pickup'da ham.

To'lov usullarining alohida API'si yo'q — checkout'dagi variantlar ro'yxati front / ilovaning o'zida. Shuning uchun naqd variantini **sayt va ilova o'zi olib tashlashi kerak**; server esa uni endi qabul qilmaydi.

| Endpoint | Oldin | Hozir | Eski front buziladimi |
| --- | --- | --- | --- |
| `POST order/` | `payment_type: 4` (+ `payment_method` `cash` / `card`) → buyurtma yaratilardi, `result: null` | `payment_type: 4` → **`400`, `error_code: 5`**, buyurtma yaratilmaydi, savat o'zgarmaydi | ha — naqd variantini tanlagan foydalanuvchi buyurtma bera olmaydi (variantni olib tashlang) |
| `POST order/pay/` | Pending buyurtmani `payment_type: 4` ga o'tkazardi | `payment_type: 4` → `400`, `error_code: 5`, buyurtma o'zgarmaydi | ha, xuddi shunday |
| `GET order/`, `GET order/<id>/` | — | o'zgarmadi: eski buyurtmalar `payment_type: 4`, `payment_method: "cash"` / `"card"` bilan avvalgidek qaytadi | yo'q |

`payment_type` qabul qilinadigan qiymatlar: `0` (hali tanlanmagan — Atmos karta, keyin `payment/hold/create/`), `1` Click, `2` Payme, `3` Uzum Bank.

Xato javobi:

```json
{
  "detail": { "payment_type": ["Оплата при получении недоступна, оплатите заказ картой онлайн"] },
  "ok": false,
  "result": "",
  "error_code": 5
}
```

Admin panel o'zgarmadi: eski naqd buyurtmalar ro'yxatda, filtrlarda (`orders/?payment_type=4`) va detail'da avvalgidek ko'rinadi va tahrirlanadi.

## Frontda qilinadigan ishlar

1. **Sayt (Rasul)**: checkout'dan «Наличные — оплата при получении» variantini olib tashlang; faqat «Оплата картой онлайн (Atmos)» qoladi. `payment_method` yubormang.
2. **Ilova (Dilshodbek)**: to'lov usuli tanlovidan naqd / qabul qilganda to'lash variantini olib tashlang (yetkazib berish va do'kondan olib ketish — ikkalasida ham). Eski versiyalar `4` yuborsa — `400` ni ko'rsating ("Faqat karta bilan onlayn to'lov mavjud").
3. Buyurtmalar tarixida eski `payment_type: 4` buyurtmalarni avvalgidek ko'rsating («При получении» / naqd) — ular o'chmaydi.
