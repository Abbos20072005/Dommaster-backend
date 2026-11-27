# Buyurtma to'lovdan keyin Tushgan'da qoladi, karta puli tasdiqlanganda yechiladi — admin panel uchun

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

- Atmos yechishni rad etsa, server hold holatini Atmos'dan so'raydi: pul aslida yechilgan bo'lsa (masalan oldingi urinish javobi yo'qolgan), buyurtma `payment_status=2` bo'lib status o'tadi; bunda `ofd_url` bo'sh qolishi mumkin.
- **Yechiladigan summa = buyurtmaning hozirgi `total_price`** (avval muzlatilgan summaning hammasi yechilardi). Tasdiqlashdan oldin panelda tovarlar o'zgartirilib summa kamaysa — kamrog'i yechiladi; ko'paysa — Atmos rad etadi (`400`, muzlatilgandan ko'p yechib bo'lmaydi).
- **Soliq cheki** (`ofd_url`): yechishda server Atmos'ga chek qatorlarini yuboradi — har tovar alohida qator (nomi, soni, summasi, buyurtma qatoridagi IKPU, tovarda bo'lsa qadoq kodi) + yetkazib berish alohida qator (xizmat IKPU'si). Promokod chegirmasi tovar qatorlariga summasi bo'yicha taqsimlanadi, qatorlar yig'indisi = yechilgan summa. Shuning uchun tasdiqlashda har qatorda IKPU bo'lishi shart ([ikpu.md](ikpu.md)). Atmos qatorlarni qabul qilmasa, pul baribir yechiladi (qatorlarsiz), operatorga xato chiqmaydi — bu server logida ko'rinadi.
- Bir buyurtmani ikki marta bosish pulni ikki marta yechmaydi: yechilgan buyurtmada keyingi statuslar Atmos'ga murojaat qilmaydi.
- Formani to'liq qaytarib yuborsangiz ham (eski `payment_status: 1` bilan), yechilgan to'lov bekor bo'lmaydi.
- **BLD-547 (27.11)**: karta buyurtmasining `payment_status` i va `ofd_url` qo'lda o'zgarmaydi (boshqa `payment_status` → `400 {"payment_status": ["Set by Atmos only."]}`), detalda `payment_kind`, `atmos_transaction` (Atmos tranzaksiya ID), `project` bor, to'lov holatining har o'zgarishi `comments` da tizim izohi — batafsil [order_payment_block_changes.md](order_payment_block_changes.md).

## Eslatmalar

- **Muzlatish muddati cheklangan** (server sozlamasi `ATMOS_HOLD_DURATION`). Shu muddat ichida tasdiqlanmagan buyurtmaning puli Atmos tomonida o'zi qaytadi, keyin tasdiqlash `400` beradi.
- **Pul yechilgandan keyin bekor qilish** (`1` va undan keyingi statuslarda) pulni avtomatik qaytarmaydi. Atmos refund hali qilinmagan, pulni qo'lda qaytarish kerak.
- 1C statusni o'zgartirsa (`2` Collecting va h.k.), pul yechilmaydi. Hold'dagi buyurtmani panelda tasdiqlang.

## Boshqa to'lov turlari (18.11.2026 dan)

Hech qaysi to'lov buyurtmani o'zi Yig'ilmoqda (`2`) ga o'tkazmaydi. Buyurtma `0` Tushgan'da qoladi, operator tasdiqlaydi va yig'ishga o'tkazadi:

| To'lov | To'lovdan keyin | Avval |
| --- | --- | --- |
| Click / Payme / Uzum (pul darhol yechiladi) | `status=0`, `payment_status=2` To'langan | `status=2`, `payment_status` `0` qolardi |
| `4` qabul qilganda / do'konda (naqd yoki karta) | `status=0`, `payment_status=0` | `status=2` |
| Atmos karta | `status=0`, `payment_status=1` Hold, pul `1` da yechiladi | `status=2` |

- Payme yoki Uzum to'lovni qaytarsa (Payme cancel, Uzum reverse), to'langan buyurtma `payment_status=3` bo'ladi va staff guruhiga "pul qaytarildi" xabari ketadi. Payme qaytarishi buyurtma statusini endi o'zgartirmaydi (avval `0` ga qaytarardi), Uzum reverse avvalgidek bekor qiladi.
- Qoldiq faqat operator `2` ga o'tkazganda kamayadi. Yig'ilmoqda qilinayotganda qoldiq yetmasa, panel `400` qaytaradi.
- Tushgan buyurtmalar ro'yxatida to'langanlarini `orders/?status=0&payment_status=2` bilan ajratish mumkin.
