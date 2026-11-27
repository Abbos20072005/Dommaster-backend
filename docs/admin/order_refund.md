# Karta to'lovini qaytarish (to'liq yoki qisman) — admin panel uchun

BLD-545. Atmos orqali karta bilan **yechilgan** to'lovni panelning o'zidan qaytarish: bitta tovarning bir necha donasi, bir necha tovar, yetkazish yoki hammasi. Server Atmos'ga qaytariladigan chek qatorlarini (`ofd_items`) yuboradi, qaytarish cheki shu qatorlardan chiqadi.

Pul hali **muzlatilgan** bo'lsa (hold, `payment_status=1`) bu endpoint kerak emas: buyurtmani bekor qilsangiz (`6`), pul o'zi qaytadi ([order_card_payment.md](order_card_payment.md)).

## Endpointlar

Hammasi admin token bilan. Summalar **tiyinda** (1 so'm = 100).

### `GET /api/v1/admin/orders/<id>/refunds/available/` — nima qaytarsa bo'ladi

```json
{
  "order": 412,
  "payment_status": 2,
  "can_refund": true,
  "reason": "",
  "charged_amount": 1738000,
  "refunded_amount": 90000,
  "lines": [
    {"item_id": 901, "ofd_code": "06901001001000001", "name": "Lampa", "amount": 90000, "quantity": 1,
     "package_code": "1500594", "charged_quantity": 2, "charged_amount": 180000},
    {"item_id": 902, "ofd_code": "10202001001000002", "name": "Kabel", "amount": 270000, "quantity": 1,
     "package_code": "", "charged_quantity": 1, "charged_amount": 270000},
    {"item_id": null, "ofd_code": "10112006002000000", "name": "Yetkazib berish xizmati", "amount": 1288000,
     "quantity": 1, "package_code": "", "charged_quantity": 1, "charged_amount": 1288000}
  ]
}
```

- `lines` — to'lov chekidagi qatorlar, **hali qaytarilmagan qismi**: `quantity` / `amount` = qaytarsa bo'ladigan son va summa, `charged_*` = chekda bo'lgani. To'liq qaytarilgan qator ro'yxatda yo'q.
- `item_id` = buyurtma qatorining id si (`items[].id`), `null` = yetkazish.
- `can_refund: false` bo'lsa, tugmani yashiring va `reason` ni ko'rsating. Sabablar: karta bilan Atmos orqali to'lanmagan, to'lov holati «To'langan» emas, to'lov chek qatorlarisiz o'tgan (qatorda IKPU yo'q edi), hammasi qaytarilgan.

### `POST /api/v1/admin/orders/<id>/refunds/` — qaytarish

Quyidagilardan biri yoki bir nechtasi:

```json
{"items": [{"item_id": 901, "quantity": 1}], "delivery": false, "reason": "Brak"}
```

```json
{"all": true, "reason": "Mijoz voz kechdi"}
```

| Maydon | Ma'nosi |
| --- | --- |
| `items` | buyurtma qatori + nechta dona qaytariladi (`quantity` ≥ 1, qolganidan ko'p emas) |
| `delivery` | `true` = yetkazish qatori ham qaytariladi |
| `all` | `true` = qolgan hamma narsa (tovarlar + yetkazish), `items` / `delivery` e'tiborga olinmaydi |
| `reason` | ixtiyoriy, ≤ 255 belgi, Atmos'ga ham ketadi |

- **Summani yubormaysiz**: u to'lov chekidan hisoblanadi. Bir dona = qator summasining ulushi (promokod chegirmasi bilan, chekdagi narx). Qatorning oxirgi donalari qolgan summani oladi, shuning uchun bir qatorning hamma qaytarishlari yig'indisi chekdagi qatorga teng bo'ladi.
- Pul **darhol** qaytariladi (Atmos: qisman qaytarish yaratiladi va o'sha zahoti tasdiqlanadi). Tasdiqlash oynasini panelda ko'rsating: summa va qatorlar.
- Muvaffaqiyat: `201` + qaytarish obyekti (pastda), `status: "confirmed"`.
- Hammasi qaytarilgach buyurtma `payment_status` = `3` (Qaytarilgan) bo'ladi va staff Telegram guruhiga "pul qaytarildi" xabari ketadi. Qisman qaytarishda `2` qoladi.
- Buyurtma **statusi va qoldiq (stock) o'zgarmaydi**. Kerak bo'lsa statusni alohida o'zgartiring.

Xatolar — `400`:

```json
{"detail": "Позиция 901: можно вернуть от 1 до 1"}
```

```json
{"detail": "Atmos отказал: STPIMS-ERR-133 Reverse not allowed", "refund": "17"}
```

- Atmos'ga yetmagan xatolarda (`items` noto'g'ri, son ko'p, to'lanmagan buyurtma) `refund` kaliti yo'q, hech narsa saqlanmaydi. `refund` bo'lsa — matn ko'rinishidagi id (`"17"`).
- Atmos rad etsa, qaytarish `failed` bo'lib ro'yxatda qoladi (`refund` = uning id si), pul qaytmagan, shu qatorlarni yana qaytarsa bo'ladi.
- Atmos tasdiqlashga javob bermasa, qaytarish `pending` bo'lib qoladi: pul qaytgan bo'lishi mumkin, shuning uchun bu qatorlar qaytarilgan hisoblanadi (ikki marta qaytmasin). Bunday holatni Atmos bilan tekshirish kerak; `error` da matni bor.

### `GET /api/v1/admin/orders/<id>/refunds/` — tarix

Odatiy sahifalash (`page`, `page_size`), eng yangisi birinchi:

```json
{
  "count": 1, "next": null, "previous": null, "next_page": null, "previous_page": null,
  "results": [{
    "id": 17,
    "amount": 90000,
    "lines": [{"item_id": 901, "ofd_code": "06901001001000001", "name": "Lampa", "amount": 90000, "quantity": 1,
               "package_code": "1500594"}],
    "reason": "Brak",
    "status": "confirmed",
    "partial_reverse_id": 3,
    "reverted_amount": 90000,
    "left_amount": 1648000,
    "error": "",
    "created_by": {"id": 2, "username": "operator", "first_name": "", "last_name": ""},
    "created_at": "2026-11-27T12:10:00"
  }]
}
```

`status`: `confirmed` qaytarildi, `failed` Atmos rad etdi (pul qaytmadi), `pending` Atmos javobi noma'lum. `reverted_amount` / `left_amount` — Atmos aytgan, tranzaksiya bo'yicha qaytarilgan / qolgan summa.

## Eslatmalar

- Faqat Atmos orqali yechilgan karta to'lovi. Click / Payme / Uzum va eski "qabul qilganda to'lash" buyurtmalari bu yerda qaytarilmaydi.
- 27.11 gacha yechilgan to'lovlarning chek qatorlari saqlanmagan: ular buyurtmaning hozirgi qatorlaridan qayta hisoblanadi.
- Atmos hujjatida qisman qaytarishning qaysi tranzaksiya id si bilan ishlashi aniq yozilmagan; server `success_trans_id` ni yuboradi (to'liq qaytarish uchun hujjatda aytilgani). Birinchi haqiqiy qaytarishni Atmos bilan birga tekshiring.
