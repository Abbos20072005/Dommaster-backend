# Do'konlar va olib ketish (pickup) — sayt va mobile uchun

Offline do'konlar ro'yxati (xarita, "hozir ochiq / yopiq"), checkout'da olib ketish uchun do'kon tanlash va "Olib ketishga tayyor" holati.

Do'kon = filial: `base/stores/` — `base/branches/` dagi filiallarning do'kon va showroom turidagilari (omborlar chiqmaydi), ID'lar bir xil. `base/branches/` eski ilova uchun o'zgarishsiz qoladi.

Base URL: `{{host}}/api/v1/`. Swagger: `/swagger/` → **Stores**, **Order**.

---

## Do'konlar ro'yxati

```
GET base/stores/          → faol do'konlar (showroom / market), sort_order bo'yicha (pagination yo'q)
GET base/stores/<id>/     → bitta faol do'kon (nofaol yoki yo'q → 404, error_code 4)
```

Token kerak emas. Matnlar `Accept-Language` tilida (`uz` / `ru`, boshqasi → `ru`; `uz` matni bo'sh bo'lsa `ru` qaytadi).

```json
{
  "result": [
    {
      "id": 3,
      "name": "Chilonzor",
      "address": "Bunyodkor ko'chasi 1",
      "landmark": "Chilonzor metro yonida",
      "phone": "+998901234567",
      "photo": "https://.../media/branch/image/chilonzor.jpg",
      "latitude": 41.28,
      "longitude": 69.2,
      "schedule": [
        {"day": 0, "is_open": true, "open_time": "09:00", "close_time": "20:00"},
        {"day": 1, "is_open": true, "open_time": "09:00", "close_time": "20:00"},
        {"day": 2, "is_open": true, "open_time": "09:00", "close_time": "20:00"},
        {"day": 3, "is_open": true, "open_time": "09:00", "close_time": "20:00"},
        {"day": 4, "is_open": true, "open_time": "09:00", "close_time": "20:00"},
        {"day": 5, "is_open": true, "open_time": "10:00", "close_time": "18:00"},
        {"day": 6, "is_open": false, "open_time": null, "close_time": null}
      ],
      "is_open_now": false,
      "closes_at": null,
      "next_open": {"day": 0, "time": "09:00", "date": "2026-10-26"},
      "sort_order": 1
    }
  ],
  "ok": true
}
```

| Maydon | Izoh |
| --- | --- |
| `address` | manzil, so'rov tilida (bo'sh uz matni ru'ga tushadi); bo'lmasa `""` |
| `landmark` | mo'ljal (ориентир), bo'sh bo'lishi mumkin (`""`) |
| `phone` | telefon yoki `null` |
| `photo` | bitta rasm yoki `null` |
| `schedule` | doim 7 qator, `day`: `0` dushanba … `6` yakshanba. Yopiq kun — `is_open: false`, vaqtlar `null` |
| `is_open_now` | jadval bo'yicha **Toshkent vaqtida** hozir ochiqmi (server hisoblaydi) |
| `closes_at` | ochiq bo'lsa bugun yopilish vaqti (`"HH:MM"`), aks holda `null` |
| `next_open` | yopiq bo'lsa keyingi ochilish: kun, vaqt, sana; hafta bo'yi yopiq bo'lsa `null` |

- Yarim tundan keyin ishlaydigan jadval yo'q (yopilish har doim ochilishdan keyin, o'sha kunda).
- Bayram jadvali hali yo'q (v2) — `is_open_now` faqat haftalik jadvalga qaraydi.
- `is_open_now` so'rov paytidagi qiymat; ekran uzoq ochiq tursa, ro'yxatni qayta yuklang.
- Do'kon kesimida qoldiq tekshirilmaydi (v2): har qanday do'konni tanlash mumkin.

---

## Checkout: olib ketish

`POST order/` — `delivery_type: 1` + `branch_id` (do'kon ID'si; to'liq tavsif: `order_create.md`).

```json
{ "payment_type": 1, "channel": "ios", "delivery_type": 1, "branch_id": 3 }
```

- Manzil (`address_id`) **kerak emas**, yetkazish narxi `0`.
- To'lovning **hamma usuli** qabul qilinadi: `1` Click, `2` Payme, `3` Uzum va `4` (do'konda to'lash, `payment_method` `cash` / `card`). `4` da to'lov havolasi `null` qaytadi, buyurtma darhol `1` Collecting bo'ladi, `payment_status` esa do'konda to'lov qabul qilinmaguncha `0` Pending turadi.
- Nofaol, mavjud bo'lmagan yoki ombor turidagi `branch_id` → `400`, `error_code: 5`, `{"branch_id": ["Store not found or inactive"]}`.
- Do'kon nomi, manzili, telefoni va koordinatasi buyurtmaga **shu paytdagi holatida** saqlanadi — do'kon keyin tahrirlansa yoki nofaol qilinsa ham buyurtmada eski ma'lumot qoladi.

---

## Buyurtmadagi maydonlar

`GET order/<id>/`, `GET order/active/`, `GET order/history/` — har bir buyurtmada:

| Maydon | Izoh |
| --- | --- |
| `pickup_store` | `{id, name, address, landmark, phone, latitude, longitude}` — buyurtma paytidagi do'kon (so'rov tilida); yetkazib berishda `null` |
| `ready_for_pickup_at` | buyurtma "Olib ketishga tayyor" bo'lgan vaqt (Toshkent), aks holda `null` |
| `pickup_deadline` | shu vaqtgacha olib ketish kerak (`ready_for_pickup_at` + 2 kun), aks holda `null` |
| `pickup_expired` | `true` = buyurtma hali tayyor holatda va muddat o'tgan |
| `pickup_branch` | o'sha do'kon **hozirgi** holatida, eski `base/branches/` shaklida — olib ketish buyurtmalarida har doim to'lgan. `pickup_store` bo'lsa shuni ishlating; bu maydon do'kon keyin tahrirlangan bo'lsa boshqa ma'lumot ko'rsatishi mumkin |

> Bu o'zgarishdan **oldin** berilgan olib ketish buyurtmalarida `pickup_store` `null` bo'ladi (snapshot o'sha paytda saqlanmagan) — ularda `pickup_branch`ni ko'rsating. Yangi buyurtmalarda ikkalasi ham keladi.

---

## "Olib ketishga tayyor" holati

Yangi status: **`5` Ready for pickup** (faqat pickup buyurtmalar). Odatdagi yo'l: `0` Pending → to'lovdan keyin `1` Collecting → `5` Ready for pickup → `3` Completed (mijoz olib ketdi).

- `5` ga o'tganda `pickup_deadline` = hozir + 2 kun yoziladi va ilovaga push boradi (`order_status_push.md`): "Заказ готов к выдаче", matnda buyurtma raqami, do'kon nomi va muddat; `data` da `branch_id`, `pickup_deadline`.
- `5` holatidagi buyurtmani mijoz bekor qila olmaydi (`POST order/<id>/cancel/` faqat `0` / `1` da).
- Muddat o'tsa buyurtma avtomatik bekor qilinmaydi — `pickup_expired: true` bo'ladi, xodimlar hal qiladi.
- `5` status `GET order/active/` ro'yxatida chiqadi.
