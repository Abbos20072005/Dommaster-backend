# Buyurtma statusi o'zgarganda push (FCM) — mobile uchun

Buyurtma statusi o'zgarganda backend mijozning barcha qurilmalariga FCM push yuboradi. Alohida API yo'q — push olish uchun qurilma tokeni ro'yxatdan o'tgan bo'lishi kifoya:

```
PATCH  {{host}}/api/v1/auth/fcm/token/     {"device_id": "...", "fcm_token": "..."}
DELETE {{host}}/api/v1/auth/fcm/token/     {"device_id": "..."}
```

Token kerak: `Authorization: Bearer <access_token>`. Swagger: `/swagger/` → **FcmToken**. Logout'da tokenni `DELETE` bilan o'chirish kerak, aks holda push eski akkauntga boraveradi.

---

## Qachon yuboriladi

| `status` | Ma'nosi | Push |
| --- | --- | --- |
| 0 | Pending | yuborilmaydi |
| 1 | Collecting | yuboriladi |
| 2 | Delivering | yuboriladi |
| 3 | Completed | yuboriladi |
| 4 | Canceled | yuboriladi |

- Status kim tomonidan o'zgartirilishidan qat'i nazar yuboriladi: admin panel, 1C, to'lov tizimi callback'i (to'lov o'tgach `1`), mijozning o'zi bekor qilganda (`4`).
- Faqat status **haqiqatan o'zgarganda** yuboriladi; buyurtma yaratilganda (status `0`) push yo'q.
- `payment_status` o'zgarishi alohida push bermaydi.

---

## Push tarkibi

`notification` (tizim ko'rsatadigan matn, hozircha faqat rus tilida):

| `status` | `title` | `body` |
| --- | --- | --- |
| 1 | Заказ в сборке | Ваш заказ №125 принят и передан в сборку. |
| 2 | Заказ в доставке | Ваш заказ №125 передан в доставку. |
| 3 | Заказ выполнен | Ваш заказ №125 выполнен. Спасибо за покупку! |
| 4 | Заказ отменён | Ваш заказ №125 отменён. |

`data` (barcha qiymatlar **string**):

```json
{
  "type": "order_status",
  "order_id": "125",
  "status": "3"
}
```

- `type` — push turini ajratish uchun, buyurtma statusi uchun har doim `order_status`.
- `order_id` — push bosilganda shu buyurtma sahifasini ochish uchun.
- `status` — yangi status; ilova ochiq bo'lsa buyurtma ekranini shu qiymat bilan yangilash yoki matnni o'zi lokalizatsiya qilish mumkin.

---

## Eslatmalar

- Push yetib borishi kafolatlanmaydi (qayta yuborish yo'q) — buyurtma holatini har doim API'dan oling, push faqat signal.
- FCM "token ro'yxatdan o'tmagan" deb javob bersa, backend o'sha tokenni o'chiradi — ilova har ishga tushganda / token yangilanganda tokenni qayta yuborsin.
