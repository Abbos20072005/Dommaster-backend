# Mahsulot rasmlari — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `POST products/{id}/images/` | rasm yuklash (multipart, maydon `image`) |
| `POST products/{id}/images/reorder/` | rasmlar tartibi / asosiy rasmni almashtirish |
| `DELETE products/{id}/images/{image_id}/` | rasmni o'chirish |

Swagger: `/swagger/admin/` → **products**.

Rasmlar mahsulotning `images` maydonida (ro'yxat va detail) **tartib bo'yicha** keladi. **Birinchi rasm — asosiy rasm** (alohida `is_main` maydoni yo'q). Sayt va ilovada ham shu tartib ishlaydi.

```json
"images": [
  { "id": 15, "image": "https://.../media/product_image/a.png", "position": 1, "created_at": "2026-10-09T11:02:10" },
  { "id": 12, "image": "https://.../media/product_image/b.png", "position": 2, "created_at": "2026-10-08T17:40:02" }
]
```

`position` faqat o'qiladi — uni `reorder/` o'zgartiradi.

---

## Yuklash

`POST products/{id}/images/` — bitta so'rovda bitta rasm. Yangi rasm har doim ro'yxat **oxiriga** qo'shiladi. Javob `201` — rasm obyekti.

Mahsulot qo'shishda: avval `POST products/` (mahsulot yaratiladi), keyin shu `id` bilan rasmlar yuklanadi va kerak bo'lsa `reorder/` chaqiriladi.

---

## Tartibni o'zgartirish / asosiy rasm

`POST products/{id}/images/reorder/`

```json
{ "ids": [12, 9, 15] }
```

- `ids` — rasm ID'lari yangi tartibda; ro'yxatdagi o'rni `position` bo'ladi.
- Asosiy rasmni almashtirish: tanlangan ID ro'yxat **boshiga** qo'yiladi.
- Ro'yxatda yo'q rasmlar (masalan faqat `{"ids": [15]}` yuborilsa) o'z tartibida yuborilganlardan **keyin** qoladi.

Javob `200` — yakuniy to'liq tartib:

```json
{ "ids": [12, 9, 15] }
```

Xatolar:

- `400 {"ids": ["Not found: [17]"]}` — ID shu mahsulotning rasmi emas
- `400 {"ids": ["Duplicate ids."]}` — ID takrorlangan
- `400` — `ids` bo'sh
- `404` — mahsulot topilmadi

---

## O'chirish

`DELETE products/{id}/images/{image_id}/` → `204`. Asosiy rasm o'chirilsa, keyingi rasm asosiy bo'ladi.
