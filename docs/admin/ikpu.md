# IKPU (MXIK) kodi — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

Soliq chekida har bir tovar uchun IKPU (MXIK) kodi bo'lishi shart — 17 xonali raqam, [tasnif.soliq.uz](https://tasnif.soliq.uz) dan olinadi. Kod **tovar kartochkasida** saqlanadi va buyurtma qatoriga nusxa olinadi. Menejer kodni buyurtmani tasdiqlashdan oldin buyurtma qatorida kiritadi / o'zgartiradi — tovar kartochkasi ham yangilanadi. Biror qatorda kod bo'lmasa buyurtmani tasdiqlab bo'lmaydi.

| Endpoint | Nima uchun |
| --- | --- |
| `GET / PATCH products/{id}/` | tovar kartochkasida `ikpu_code`, `package_code` (o'qish / yozish) |
| `GET products/?ikpu_missing=true` | IKPU'si yo'q tovarlar |
| `GET orders/{id}/` | buyurtma qatorlarida `items[].ikpu_code` |
| `PATCH orders/{id}/ikpu/` | buyurtma qatorlariga IKPU kiritish / o'zgartirish (faqat `status=0` Tushgan) |
| `PATCH orders/{id}/` `{"status": ...}` | tasdiqlash — kodsiz qator bo'lsa `400` |
| `GET ikpu-changes/` | o'zgarishlar tarixi (log) |

Swagger: `/swagger/admin/` → **products**, **orders**, **ikpu-changes**.

---

## 1. Tovar kartochkasi

`GET products/{id}/` va `GET products/` ro'yxatidagi har bir tovarda ikki yangi maydon:

```json
{
  "id": 812,
  "name": "Sement M400 50 kg",
  "ikpu_code": "02523001001000000",
  "package_code": "1500594",
  "...": "..."
}
```

| Maydon | Izoh |
| --- | --- |
| `ikpu_code` | IKPU (MXIK) kodi: **aniq 17 ta raqam**. `""` = kod yo'q. Ixtiyoriy |
| `package_code` | Qadoq kodi (код упаковки): faqat raqamlar, 1–20 ta. `""` = yo'q. Ixtiyoriy, faqat kartochkada (buyurtmada yo'q) |

Yozish — oddiy `PATCH products/{id}/` (yoki `POST products/` yaratishda):

```json
{"ikpu_code": "02523001001000000", "package_code": "1500594"}
```

- Bo'sh satr `""` yuborilsa kod o'chiriladi.
- Noto'g'ri qiymat (harf, 16 yoki 18 raqam) saqlanmaydi → `400`:

```json
{"ikpu_code": ["IKPU code must be exactly 17 digits."]}
```

```json
{"package_code": ["Package code must be digits only (up to 20)."]}
```

18 va undan ortiq belgida xato matni `"Ensure this field has no more than 17 characters."` bo'lishi mumkin.

- Har bir haqiqiy o'zgarish logga yoziladi (`source: "product"`), bir xil qiymat qayta yuborilsa — yozilmaydi.
- Kartochkada IKPU o'zgarsa, **tasdiqlanmagan** (Tushgan) buyurtmalardagi shu tovar qatorlari, agar ularda eski kod turgan bo'lsa (yoki bo'sh bo'lsa), yangi kodni oladi. Tasdiqlangan buyurtmalardagi kod o'zgarmaydi.

### Filtr «IKPU yo'q»

| Query | Natija |
| --- | --- |
| `?ikpu_missing=true` | faqat IKPU'si yo'q tovarlar |
| `?ikpu_missing=false` | faqat IKPU'si bor tovarlar |

Boshqa `products/` filtrlari bilan birga ishlaydi (`?ikpu_missing=true&is_active=true`).

---

## 2. Buyurtma qatorlari

`GET orders/{id}/` → `items[]` da `ikpu_code` (faqat o'qish uchun):

```json
"items": [
  {"id": 501, "product": {"id": 812, "name": "Sement M400 50 kg", "product_code": "00-123", "price": 62000, "discount_price": null},
   "quantity": 10, "ikpu_code": "02523001001000000"},
  {"id": 502, "product": {"id": 90, "name": "Gipsokarton 12.5 mm", "product_code": "00-456", "price": 54000, "discount_price": null},
   "quantity": 4, "ikpu_code": ""}
]
```

- Yangi buyurtma qatoriga (sayt / ilova checkout'i, admin paneldan yaratish) tovardagi IKPU **avtomatik** tushadi. Tovarda kod bo'lmasa — `""`.
- `PATCH orders/{id}/` da `items` ro'yxati qayta yuborilsa (tarkib o'zgartirilsa), qolgan tovarlar o'z kodini saqlaydi, yangi qo'shilgan tovar kartochkadagi kodni oladi. `items[].ikpu_code` bu yerda yozilmaydi — uning uchun pastdagi endpoint.

### `PATCH orders/{id}/ikpu/` — qatorlarga kod kiritish

Faqat buyurtma **Tushgan** (`status=0`) holatida. Bir yoki bir nechta qator bir so'rovda:

```json
{
  "items": [
    {"id": 502, "ikpu_code": "06807001001000000"}
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `items` * | bo'sh bo'lmagan ro'yxat |
| `items[].id` * | buyurtma qatori id'si (`items[].id`, tovar id'si emas) |
| `items[].ikpu_code` * | aniq 17 raqam; bo'sh qiymat qabul qilinmaydi |

Javob — butun buyurtma (`GET orders/{id}/` bilan bir xil shakl), `200`.

Nima bo'ladi:
1. Qatordagi kod yangilanadi, logga yoziladi (`source: "order"`, `order` = shu buyurtma, eski qiymat = qatordagi eski kod).
2. **Tovar kartochkasi ham** yangi kodni oladi.
3. Boshqa tasdiqlanmagan buyurtmalardagi shu tovar qatorlari, eski kod turgan bo'lsa, yangisini oladi; tasdiqlangan buyurtmalar o'zgarmaydi.

Xatolar (`400`):

| Javob | Qachon |
| --- | --- |
| `{"items": ["IKPU codes can only be changed while the order is pending."]}` | buyurtma Tushgan holatida emas (tasdiqlangan, yig'ilyapti, bekor qilingan …) |
| `{"items": [{"ikpu_code": ["IKPU code must be exactly 17 digits."]}]}` | kod formati noto'g'ri |
| `{"items": [{"ikpu_code": ["This field may not be blank."]}]}` | bo'sh kod |
| `{"items": ["Not items of the order: [777]"]}` | qator boshqa buyurtmaniki / yo'q |
| `{"items": ["Duplicate items."]}` | bitta qator ikki marta |

---

## 3. Tasdiqlash

"Tasdiqlash" = buyurtma Tushgan (`0`) holatidan **Bekor qilingan (`6`) dan boshqa** har qanday holatga o'tishi (odatda `1` Tasdiqlangan; Tasdiqlangan o'tkazib yuborilsa `2`, `3` … ham). Biror qatorda `ikpu_code` bo'sh bo'lsa — rad etiladi, holat o'zgarmaydi, Atmos karta to'lovi ham yechilmaydi:

`PATCH orders/{id}/` `{"status": 1}` → `400`

```json
{
  "status": ["Order items without an IKPU code: set them before confirming the order."],
  "missing_ikpu": [
    {"item_id": 502, "product": {"id": 90, "name": "Gipsokarton 12.5 mm"}}
  ]
}
```

- `missing_ikpu` — kodsiz qatorlar (`item_id` = qator id'si, shu qatorlarni belgilab, menejerga ko'rsating). Kodlarni `orders/{id}/ikpu/` bilan kiritib, tasdiqlashni qaytaring.
- Bir so'rovda `items` ham yuborilsa (tarkib o'zgarsa), tekshiruv yangi tarkib bo'yicha; yangi qatorlarning id'si hali yo'q → `item_id: null`.
- `POST orders/` (admin paneldan yaratish) tasdiqlangan holat bilan yuborilsa — xuddi shunday `400`, buyurtma yaratilmaydi (`item_id: null`).
- Bekor qilish (`6`) uchun kod kerak emas.
- Boshqa yo'llar ham bloklanadi: 1C status yangilashi, django admin. Tasdiqlangan buyurtmada IKPU'ni o'zgartirib bo'lmaydi.

---

## 4. O'zgarishlar tarixi — `GET ikpu-changes/`

Faqat o'qish. Paginatsiya: `?page=&page_size=` (default 20, max 100) → `count, next, previous, next_page, previous_page, results`. Yangisi birinchi.

```json
{
  "id": 14,
  "product": {"id": 90, "name": "Gipsokarton 12.5 mm", "product_code": "00-456", "articul_code": "GK-125"},
  "order": {"id": 3051, "status": 0},
  "field": "ikpu_code",
  "old_value": "",
  "new_value": "06807001001000000",
  "source": "order",
  "changed_by": {"id": 4, "username": "dilnoza", "full_name": "Dilnoza Karimova"},
  "created_at": "2026-11-25T15:02:11.204512"
}
```

| Maydon | Izoh |
| --- | --- |
| `product` | qaysi tovar |
| `order` | qaysi buyurtma qatorida o'zgartirildi; `null` = tovar kartochkasida |
| `field` | `ikpu_code` yoki `package_code` |
| `old_value` / `new_value` | eski / yangi qiymat (`""` = yo'q edi / o'chirildi) |
| `source` | `product` — tovar kartochkasi, `order` — buyurtma qatori |
| `changed_by` | kim (admin); `null` — foydalanuvchi o'chirilgan |
| `created_at` | qachon (Toshkent vaqti) |

Filtrlar:

| Query | Izoh |
| --- | --- |
| `product` | tovar id — tovar kartochkasidagi «Tarix» |
| `order` | buyurtma id — buyurtma sahifasidagi «Tarix» |
| `field` | `ikpu_code` / `package_code` |
| `source` | `product` / `order` |
| `changed_by` | admin id |
| `from_created`, `to_created` | sana (`YYYY-MM-DD`) |
| `search` | tovar nomi (uz / ru), eski / yangi qiymat |
| `ordering` | `id`, `created_at` (`-` bilan teskari) |

---

## Frontda qilinadigan ishlar

1. Tovar formasi: «IKPU (MXIK)» (17 raqam) va «Qadoq kodi» maydonlari; `400` xatoni maydon ostida ko'rsatish.
2. Tovarlar ro'yxati: «IKPU yo'q» filtri → `?ikpu_missing=true`.
3. Buyurtma sahifasi: har qatorda `ikpu_code`; bo'sh bo'lsa ogohlantirish. Tushgan buyurtmada tahrirlash → `PATCH orders/{id}/ikpu/`; boshqa holatlarda faqat o'qish.
4. «Tasdiqlash» bosilganda `400` + `missing_ikpu` kelsa — xabar chiqarib, shu qatorlarni belgilash.
5. Tarix: tovar kartochkasida `ikpu-changes/?product={id}`, buyurtmada `ikpu-changes/?order={id}`.
