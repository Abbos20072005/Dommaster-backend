# Akkauntni o'chirish — mobile uchun

Base URL: `{{host}}/api/v1/`

Ikkita endpoint:

| Endpoint | Nima uchun | Token |
| --- | --- | --- |
| `GET base/delete-button/` | Profilda "Akkauntni o'chirish" tugmasini ko'rsatish / yashirish | kerak emas |
| `DELETE auth/delete/account/` | Joriy mijozning akkauntini o'chirish | `Authorization: Bearer <access_token>` |

Swagger: `/swagger/` → **Delete Button** va **Auth** → "Account delete".

---

## 1. Tugmani ko'rsatish kerakmi — `GET base/delete-button/`

Admin panelda (django admin → "Delete button") boshqariladigan flag. Ilova ochilganda (yoki profil ekranida) so'raladi.

```bash
curl {{host}}/api/v1/base/delete-button/
```

```json
{
  "result": { "is_deleted": true },
  "ok": true
}
```

| `is_deleted` | Ilova nima qiladi |
| --- | --- |
| `true` | "Akkauntni o'chirish" tugmasi ko'rsatiladi |
| `false` | tugma yashiriladi |

- Oxirgi qo'shilgan yozuv olinadi; admin panelda birorta ham yozuv bo'lmasa `false` keladi.
- Javob keshlanmaydi — admin o'zgartirsa, keyingi so'rovda yangi qiymat keladi.

---

## 2. Akkauntni o'chirish — `DELETE auth/delete/account/`

Body yo'q. Mijoz tokendan olinadi — ID yuborilmaydi, faqat o'z akkauntini o'chiradi.

```bash
curl -X DELETE {{host}}/api/v1/auth/delete/account/ \
  -H "Authorization: Bearer <access_token>"
```

### Javob

Muvaffaqiyat → **`204 No Content`**.

> Backend `{"result": "Account successfully deleted", "ok": true}` body ham yuboradi, lekin 204 da HTTP klientlar (Dio, URLSession, OkHttp) body'ni o'qimasligi mumkin. **Muvaffaqiyatni faqat status kodi bo'yicha tekshiring** (`204`), body'ni parse qilmang.

### Xatolar

| Holat | Status | Body |
| --- | --- | --- |
| Token yuborilmagan / mijoz topilmadi (allaqachon o'chirilgan) | `400` | `{"detail": "User Does not exist", "ok": false, "result": "", "error_code": 7}` |
| Mijoz bloklangan | `400` | `{"detail": "User Blocked, Contact admins", "ok": false, "result": "", "error_code": 9}` |
| Token yaroqsiz / muddati o'tgan | `401` | standart JWT xatosi — avval `POST auth/token/refresh/` qiling |

> Bu endpoint tokensiz so'rovda `401` emas, **`400` + `error_code: 7`** qaytaradi.

---

## Nima o'chadi, nima qoladi

O'chirish **qaytarib bo'lmaydi** (hard delete, "korzina" yo'q). Ilovada albatta tasdiqlash dialogi bo'lsin.

**O'chadi** (mijoz bilan birga):
- profil (ism, telefon, avatar), manzillar;
- qurilmalar / FCM tokenlar — push endi kelmaydi; OTP kodlar, Telegram bog'lanishi;
- savat, sevimlilar, yaqinda ko'rilganlar;
- saqlangan kartalar (Atmos);
- savollar va savol/sharhlarga yozilgan javoblar, sharh rasmlari;
- promokodlar, bildirishnomalarning o'qilgan holati.

**Qoladi** (mijozsiz, `customer = null`):
- buyurtmalar — buxgalteriya / 1C uchun saqlanadi, lekin endi hech qaysi akkauntga bog'lanmagan;
- mahsulot sharhlari (reyting o'zgarmaydi);
- support chat va loyalty karta.

---

## O'chirgandan keyin ilova nima qiladi

1. `204` kelgach, **access va refresh tokenlarni darhol o'chiring** (secure storage), savat/sevimlilar keshini tozalang, mehmon (guest) holatiga o'ting — login ekrani yoki bosh sahifa.
2. **Eski token bilan hech qanday so'rov yubormang.** Token hali muddati o'tmagan bo'lsa ham mijoz bazada yo'q — token talab qiladigan endpointlar xato beradi (ba'zilari `500`).
3. `DELETE fcm/token/` ni alohida chaqirish shart emas — FCM tokenlar akkaunt bilan birga o'chadi.
4. Shu telefon raqami bilan qayta kirish mumkin: `auth/auth/phone/` → OTP odatdagidek ishlaydi, lekin bu **yangi akkaunt** (`is_new: true`) — eski buyurtmalar, manzillar va boshqalar qaytmaydi.

---

## Tavsiya etilgan oqim

```
Profil ekrani
  └─ GET base/delete-button/ → is_deleted = true bo'lsa tugmani ko'rsat
       └─ "Akkauntni o'chirish" bosildi
            └─ Tasdiqlash dialogi ("Buyurtmalar tarixi, manzillar va kartalar o'chadi. Qaytarib bo'lmaydi.")
                 └─ DELETE auth/delete/account/
                      ├─ 204 → tokenlarni o'chir, keshni tozala, guest holatiga o't
                      ├─ 401 → token refresh, keyin qayta urin
                      └─ 400 (error_code 7) → allaqachon o'chirilgan: tokenlarni o'chir, guest holatiga o't
```
