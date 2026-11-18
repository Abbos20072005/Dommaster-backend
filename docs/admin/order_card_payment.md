# Karta bilan to'lov (Atmos): pul tasdiqlanganda yechiladi — admin panel uchun

BLD-486. Endpoint va maydonlar o'zgarmadi, `PATCH orders/<id>/` `{"status": ...}` ning ishlashi o'zgardi.

## Oqim

| Qadam | Kim | Buyurtma `status` | `payment_status` |
| --- | --- | --- | --- |
| Mijoz karta bilan to'ladi (pul kartada **muzlatildi**) | ilova / sayt | `0` Tushgan (**avval darhol `2` ga o'tardi**) | `1` Hold (to'lov kutilmoqda) |
| Operator **Tasdiqlangan** qildi | admin panel | `1` | `2` Paid — **pul shu yerda yechiladi** |
| Operator **Yig'ilmoqda** qildi | admin panel | `2` (qoldiq shu yerda kamayadi) | `2` |

- Hold'dagi buyurtma (`payment_status=1`, `hold_id` bor) `0` dan boshqa statusga o'tkazilganda server avval Atmos'dan pulni yechadi, keyin statusni saqlaydi. Odatda bu `1` Tasdiqlangan. Agar `1` o'tkazib yuborilib to'g'ridan `2` / `3` / ... qo'yilsa, pul o'sha paytda yechiladi.
- Yechilgandan keyin buyurtmada `ofd_url` (chek havolasi) paydo bo'ladi, `payment_status` = `2`.
- **Bekor qilish** (`6`) hold'dagi buyurtmada muzlatilgan pulni mijozga qaytaradi: `payment_status` = `3`, staff Telegram guruhiga "pul qaytarildi" xabari ketadi.
- Atmos rad etsa (masalan hold muddati o'tgan) yoki javob bermasa: `400`, status **o'zgarmaydi**:

```json
{"status": ["Atmos: charge refused (STPIMS-ERR-092: Hold expired)"]}
```

Xato matnini operatorga ko'rsating. Bunday buyurtmani bekor qilish yoki mijoz bilan bog'lanish kerak.

- Bir buyurtmani ikki marta bosish pulni ikki marta yechmaydi: yechilgan buyurtmada keyingi statuslar Atmos'ga murojaat qilmaydi.
- Formani to'liq qaytarib yuborsangiz ham (eski `payment_status: 1` bilan), yechilgan to'lov bekor bo'lmaydi.

## Eslatmalar

- **Muzlatish muddati cheklangan** (server sozlamasi `ATMOS_HOLD_DURATION`). Shu muddat ichida tasdiqlanmagan buyurtmaning puli Atmos tomonida o'zi qaytadi, keyin tasdiqlash `400` beradi.
- **Pul yechilgandan keyin bekor qilish** (`1` va undan keyingi statuslarda) pulni avtomatik qaytarmaydi. Atmos refund hali qilinmagan, pulni qo'lda qaytarish kerak.
- Faqat Atmos karta to'lovi shunday ishlaydi. Click / Payme / Uzum to'lovidan keyin buyurtma hozircha avvalgidek darhol `2` ga o'tadi.
- 1C statusni o'zgartirsa (`2` Collecting va h.k.), pul yechilmaydi. Hold'dagi buyurtmani panelda tasdiqlang.
