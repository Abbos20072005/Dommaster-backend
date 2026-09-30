# Profil rasmi (avatar) — mobile uchun

Base URL: `{{host}}/api/v1/auth/`
Token kerak: `Authorization: Bearer <access_token>` (tokensiz → `401`).

Profil rasmi **mavjud profilni yangilash API'si** orqali yuklanadi, almashtiriladi va o'chiriladi — alohida avatar endpointi yo'q:

```
PATCH customer/update/
```

- Foydalanuvchi faqat o'z profilini o'zgartiradi — mijoz tokendan olinadi, ID yuborilmaydi.
- Rasm URL'i `GET auth/me/` va update javobida `avatar` maydonida keladi; rasm yo'q bo'lsa `null`.
- Swagger: `/swagger/` → **Auth** → "Update user information".

---

## Request

Rasm faqat `multipart/form-data` bilan yuboriladi. Faqat matnli maydonlarni (masalan `full_name`) o'zgartirish uchun oddiy JSON ham ishlaydi — `avatar` yuborilmasa rasm o'zgarmaydi.

| Amal | Content-Type | `avatar` qiymati |
| --- | --- | --- |
| Yuklash / almashtirish | `multipart/form-data` | rasm fayli |
| O'chirish | `multipart/form-data` | bo'sh qiymat (`avatar=`) |
| O'chirish | `application/json` | `null` |
| Rasmga tegmaslik | istalgan | maydonni yubormaslik |

Rasm yuklash (boshqa maydonlar bilan birga ham bo'ladi):

```bash
curl -X PATCH {{host}}/api/v1/auth/customer/update/ \
  -H "Authorization: Bearer <access_token>" \
  -F "avatar=@photo.jpg" \
  -F "full_name=Ali Valiyev"
```

Rasmni o'chirish (JSON):

```bash
curl -X PATCH {{host}}/api/v1/auth/customer/update/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"avatar": null}'
```

Rasmni o'chirish (multipart):

```bash
curl -X PATCH {{host}}/api/v1/auth/customer/update/ \
  -H "Authorization: Bearer <access_token>" \
  -F "avatar="
```

---

## Response

Muvaffaqiyatli update → `202 Accepted` + yangilangan profil. `avatar` — to'liq URL yoki `null`.

```json
{
  "result": {
    "id": 18,
    "full_name": "Ali Valiyev",
    "phone_number": "998901234567",
    "email": null,
    "role": "user",
    "avatar": "https://<host>/media/customer/avatar/photo.jpg"
  },
  "ok": true
}
```

`GET auth/me/` ham xuddi shu `result` obyektini `200 OK` bilan qaytaradi.

> Rasm almashtirilganda fayl nomi o'zgarishi mumkin (masalan `photo_ZXvP4Zh.jpg`) — URL'ni har doim javobdan oling, keshlashda ham kalit sifatida shu URL'dan foydalaning.

---

## Validatsiya va xatolar

- Formatlar: **jpg/jpeg, png, webp**. Maksimal hajm: **5 MB**.
- Format fayl kengaytmasidan emas, rasmning haqiqiy mazmunidan aniqlanadi (`.png` deb nomlangan gif rad etiladi).
- HEIC qabul qilinmaydi — iOS'da yuborishdan oldin JPEG'ga o'tkazing.

Noto'g'ri fayl → `400 Bad Request`, `error_code: 5` (VALIDATION_FAILED), xabar `detail.avatar` ichida:

```json
{
  "detail": { "avatar": ["Image size must not exceed 5 MB."] },
  "ok": false,
  "result": "",
  "error_code": 5
}
```

| Holat | HTTP | `detail.avatar` xabari |
| --- | --- | --- |
| Hajm 5 MB dan katta | 400 | Image size must not exceed 5 MB. |
| gif, bmp va boshqa format | 400 | Unsupported image format. Allowed: jpg/jpeg, png, webp. |
| Buzuq yoki rasm bo'lmagan fayl | 400 | Загрузите правильное изображение... (Django standart xabari) |
| JSON'da fayl o'rniga matn | 400 | Загруженный файл не является корректным файлом. |
| Token yo'q yoki yaroqsiz | 401 | — (`{"error": "Unauthorized access", "ok": false}`) |

> Xatoni aniqlashda xabar matniga emas, `error_code` va `detail.avatar` mavjudligiga tayaning.

---

## Eslatmalar

- Eski fayl serverda avtomatik o'chiriladi: rasm almashtirilganda, o'chirilganda va akkaunt o'chirilganda. Klient tomondan qo'shimcha so'rov kerak emas.
- `avatar` mijoz obyekti keladigan boshqa javoblarda ham bor (izohlar, savollar, buyurtmalar ichidagi `customer`) — foydalanuvchi rasmini ko'rsatishda ishlatish mumkin.
- Katta rasmlarni yuborishdan oldin kichraytirish tavsiya etiladi (masalan 1024 px gacha) — 5 MB chegarasiga tushmaydi va yuklash tezroq bo'ladi.
