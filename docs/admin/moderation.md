# Moderatsiya — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET moderation/stats/` | kartochkalar + tab sonlari |
| `GET moderation/?status=pending` | navbat (tablar: `pending` / `approved` / `rejected`) |
| `GET moderation/{id}/` | modal: mahsulot preview + tayyorlik ro'yxati |
| `POST moderation/{id}/approve/` | tasdiqlash |
| `POST moderation/{id}/reject/` | qaytarish (sabab bilan) |
| `POST moderation/bulk-approve/` | "Tanlanganlarni tasdiqlash" |

Swagger: `/swagger/admin/` → **moderation**.

---

## Mahsulot navbatga qanday tushadi

Mahsulot formasida `PATCH products/{id}/` bilan `"publish_status": "review"` yuborilganda — navbatda yangi qator paydo bo'ladi, **yuborgan** = shu so'rovni qilgan admin.

| Formada `publish_status` | Navbat |
| --- | --- |
| → `review` | yangi qator (`pending`); mahsulot allaqachon navbatda bo'lsa — yangisi ochilmaydi |
| → `published` (qo'lda) | navbatdagi qator `approved` bo'ladi (tayyorlik **tekshirilmaydi**) |
| → `draft` | navbatdagi qator o'chiriladi (yuborish qaytarib olindi) |

Tasdiqlash → `publish_status: "published"`, qaytarish → `"draft"`. Qaytarilgan mahsulot tuzatilib yana `review` ga yuboriladi — yangi qator ochiladi (eskisi tarixda qoladi).

Mahsulot detalida (`GET products/{id}/`) oxirgi yuborish ko'rinadi — kontent jamoasi qaytarish sababini shu yerdan o'qiydi:

```json
"last_moderation": {
  "id": 12, "status": "rejected", "submitted_at": "2026-10-13T10:02:11",
  "reviewed_by": "Sanjar T.", "reviewed_at": "2026-10-14T09:15:40", "reason": "RU tavsif yo'q"
}
```

`null` — mahsulot hech qachon yuborilmagan.

> `publish_status` hozircha hech qayerda mantiqqa ega emas: mijozlarga mahsulot ko'rinishini faqat `is_active` hal qiladi. Tasdiqlash `is_active` ga tegmaydi.

---

## Kartochkalar — `GET moderation/stats/`

Ro'yxat filtrlariga bog'liq emas.

```json
{
  "pending": 28,
  "approved": 312,
  "rejected": 41,
  "approved_today": 46,
  "rejected_today": 9,
  "avg_wait_seconds": 50400,
  "oldest_submitted_at": "2026-10-11T08:40:00",
  "oldest_wait_seconds": 263000
}
```

| Maydon | Dizayndagi joy |
| --- | --- |
| `pending` | "Navbatda", tab "Navbatda (28)" |
| `avg_wait_seconds` | "O'rtacha kutish" — navbatdagi qatorlar hozirgacha qancha kutyapti (o'rtacha); navbat bo'sh → `null` |
| `approved_today` / `rejected_today` | "Bugun tasdiqlandi" / "Qaytarildi" |
| `approved` / `rejected` | tab sonlari (hamma vaqt uchun) |
| `oldest_submitted_at`, `oldest_wait_seconds` | "Eng eskisi 3 kun kutmoqda"; navbat bo'sh → `null` |

Tablarda faqat bugungilar kerak bo'lsa — `approved_today` / `rejected_today` ni qo'ying va ro'yxatga `reviewed_from=<bugun>` yuboring.

---

## Ro'yxat — `GET moderation/`

Paginatsiyali (`page`, `page_size`).

| Parametr | Izoh |
| --- | --- |
| `status` | `pending` (navbat, **eng eskisi birinchi**), `approved`, `rejected` (oxirgi ko'rilgani birinchi) |
| `search` | mahsulot nomi (uz/ru), 1C kodi, artikul, shtrixkod |
| `product` | bitta mahsulotning yuborishlar tarixi |
| `submitted_by`, `reviewed_by` | admin (`User`) id |
| `reviewed_from`, `reviewed_to` | ko'rilgan sana oralig'i (`YYYY-MM-DD`) |
| `ordering` | `submitted_at`, `reviewed_at`, `id` (`-` bilan teskari) |

```json
{
  "id": 7,
  "status": "pending",
  "product": {
    "id": 3121,
    "name": "Avtomat Chint NXB-63 1P C25 6 kA",
    "name_uz": "Avtomat Chint NXB-63 1P C25 6 kA",
    "name_ru": null,
    "product_code": "00-00012345",
    "articul_code": "CHT-NXB63-1P-C25",
    "image": "https://.../media/product_image/915.png",
    "publish_status": "review",
    "is_active": true
  },
  "submitted_by": { "id": 4, "username": "sanjar", "full_name": "Sanjar T." },
  "submitted_at": "2026-10-13T05:12:00",
  "waiting_seconds": 101000,
  "reviewed_by": null,
  "reviewed_at": null,
  "reason": "",
  "readiness": { "done": 6, "total": 8, "ready": false, "missing": ["name_ru", "description_ru"] }
}
```

| Maydon | Izoh |
| --- | --- |
| `waiting_seconds` | "Kutmoqda": `pending` — yuborilgandan beri; ko'rilgan — ko'rilguncha qancha kutgan |
| `submitted_by` | "Yuborgan"; `null` — noma'lum (moderatsiyadan oldin `review` da turgan mahsulotlar) |
| `readiness.ready` | `false` → "Tasdiqlash" tugmasi o'chiq |
| `readiness.missing` | "2 ta yetishmaydi · RU nomi" — yetishmayotgan bandlar (ro'yxatdagi tartibda) |

---

## Modal — `GET moderation/{id}/`

Ro'yxat qatoridagi hamma maydonlar + kengroq `product` (preview uchun) va to'liq `readiness`:

```json
"product": {
  "...": "ro'yxatdagi maydonlar",
  "description_uz": "<p>...</p>",
  "description_ru": "",
  "brand": { "id": 24, "name": "Chint" },
  "product_item_category": {
    "id": 33, "name": "Avtomatlar",
    "product_sub_category": { "id": 8, "name": "...", "product_category": { "id": 2, "name": "Elektr jihozlari" } }
  },
  "price": 54000.0, "discount_price": null, "discount": null, "unit": "pcs", "quantity": 120,
  "images": [{ "id": 1, "image": "https://...", "position": 1, "created_at": "..." }],
  "attribute_values": [
    { "id": 5, "name_uz": "Qutblar", "name_ru": "Полюса", "name_en": null,
      "value_uz": "1", "value_ru": "1", "value_en": null, "unit_uz": "", "unit_ru": "", "unit_en": "" }
  ]
},
"readiness": {
  "done": 6, "total": 8, "ready": false,
  "missing": ["name_ru", "description_ru"],
  "checks": [
    { "key": "name_uz", "done": true },
    { "key": "name_ru", "done": false },
    { "key": "description_uz", "done": true },
    { "key": "description_ru", "done": false },
    { "key": "image", "done": true },
    { "key": "required_attributes", "done": true },
    { "key": "category", "done": true },
    { "key": "brand", "done": true }
  ],
  "missing_attributes": []
}
```

Kategoriya nomlari `Accept-Language` bo'yicha keladi. Preview'dagi UZ/RU almashtirgich uchun mahsulot nomi va tavsifi ikkala tilda beriladi.

### Tayyorlik bandlari

Hammasi majburiy — bittasi bajarilmasa ham tasdiqlab bo'lmaydi.

| `key` | Dizayn | Qachon bajarilgan |
| --- | --- | --- |
| `name_uz` | UZ nomi | `name_uz` bo'sh emas |
| `name_ru` | RU nomi | `name_ru` bo'sh emas |
| `description_uz` | Tavsif UZ | HTML teglarisiz matn bor (`<p></p>` — bo'sh) |
| `description_ru` | Tavsif RU | xuddi shunday |
| `image` | Kamida 1 ta rasm | kamida bitta rasm |
| `required_attributes` | Majburiy xususiyatlar | kategoriyaning majburiy atributlari hammasi to'ldirilgan; yetishmaganlari `missing_attributes` da (`id`, `name`, `name_uz`, `name_ru`) |
| `category` | Kategoriya | predmet kategoriyasi tanlangan |
| `brand` | Brend | brend tanlangan |

Majburiy atribut — kategoriyaning atributlar ro'yxatida `is_required: true` (`PUT item-categories/{id}/attributes/`, `attributes.md`). Faol bo'lmagan (`is_active: false`) atribut talab qilinmaydi. Kategoriyasiz mahsulotda `required_attributes` bajarilgan hisoblanadi (o'rniga `category` yetishmaydi).

"To'ldirish" tugmasi — mahsulot formasini (`products/{id}/`) shu `key` ga mos maydonda oching.

---

## Tasdiqlash — `POST moderation/{id}/approve/`

Body yo'q. Javob — modal obyekti (`status: "approved"`), mahsulot `publish_status: "published"` bo'ladi.

| Xato (`400`) | Sabab |
| --- | --- |
| `{"detail": "The product is not ready.", "missing": ["name_ru"]}` | tayyorlik bandlari bajarilmagan |
| `{"detail": "The row is already reviewed."}` | qator allaqachon ko'rilgan (boshqa admin ulgurgan) |

## Qaytarish — `POST moderation/{id}/reject/`

```json
{ "reason": "RU nomi va tavsifi yo'q" }
```

`reason` majburiy (≤ 1000 belgi). Javob — modal obyekti (`status: "rejected"`), mahsulot `publish_status: "draft"` bo'ladi. Ko'rilgan qatorga — `400` (`already reviewed`). Qaytarishga tayyorlik shart emas.

## Tanlanganlarni tasdiqlash — `POST moderation/bulk-approve/`

```json
{ "ids": [7, 8, 9] }
```

Moderatsiya qatorlarining id'lari (mahsulotniki emas), ≤ 100 ta. Tayyorlari tasdiqlanadi, qolganlari o'tkazib yuboriladi — so'rov baribir `200`:

```json
{
  "approved": [7, 9],
  "skipped": [
    { "id": 8, "reason": "not_ready", "missing": ["image"] }
  ]
}
```

`reason`: `not_ready` — tayyorlik bandlari bajarilmagan (`missing`), `not_pending` — bunday qator yo'q yoki allaqachon ko'rilgan. Keyin `stats/` va ro'yxatni qayta yuklang.
