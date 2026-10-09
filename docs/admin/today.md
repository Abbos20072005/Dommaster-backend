# Bugungi ishlar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET today/` | "Bugungi ishlar" sahifasidagi **barcha** vidjetlar bitta javobda |

Swagger: `/swagger/admin/` → **today**. Query parametr yo'q.

---

## Javob

```json
{
  "now": "2026-10-03T11:59:17.503601",
  "cards": { ... },
  "attention": { ... },
  "catalog": { ... },
  "orders_chart": { ... },
  "recent_orders": [ ... ]
}
```

Umumiy qoidalar:

- Vaqtlar — Toshkent vaqti, timezone'siz. "7 soat", "2 kun qoldi" kabi muddatlarni `now` ga nisbatan hisoblang (brauzer soatiga emas).
- Summalar — so'mda, `float`.
- Javob keshlanmaydi — har so'rovda bazadan hisoblanadi.

### `cards` — yuqoridagi kartochkalar

```json
"cards": {
  "today_orders": 78,
  "today_total": 61240000.0,
  "today_customers": 12,
  "pending": 14,
  "stale_pending": 5,
  "stale_minutes": 30,
  "collecting": 9,
  "delivering": 23
}
```

| Maydon | Izoh |
| --- | --- |
| `today_orders`, `today_total` | bugun yaratilgan **barcha** buyurtmalar soni va summasi (holatidan qat'i nazar) |
| `today_customers` | bugun ro'yxatdan o'tgan mijozlar |
| `pending` | "Kutilmoqda" (`status=0`) holatidagi barcha buyurtmalar — "Tasdiq kutmoqda" |
| `stale_pending` | shulardan `stale_minutes` daqiqadan ko'p kutayotganlari |
| `stale_minutes` | chegara, hozir `30` |
| `collecting` | "Yig'ilmoqda" (`status=1`) holatidagi barcha buyurtmalar |
| `delivering` | "Yetkazilmoqda" (`status=2`) holatidagi barcha buyurtmalar |

### `attention` — diqqat talab qiladi

```json
"attention": {
  "total": 3,
  "banner_days": 3,
  "items": [
    {
      "key": "stale_pending_orders",
      "group": "orders",
      "level": "warning",
      "count": 5,
      "amount": null,
      "date": "2026-10-03T10:38:00",
      "objects": [
        { "id": 28594, "name": null, "date": "2026-10-03T10:38:00" }
      ]
    },
    {
      "key": "out_of_stock_products",
      "group": "catalog",
      "level": "danger",
      "count": 7,
      "amount": null,
      "date": null,
      "objects": [
        { "id": 134, "name": "Штукатурка модель 2", "date": null }
      ]
    },
    {
      "key": "expiring_banners",
      "group": "content",
      "level": "warning",
      "count": 2,
      "amount": null,
      "date": "2026-10-04T00:00:00",
      "objects": [
        { "id": 4, "name": "Knauf kuzgi aksiya", "date": "2026-10-04T00:00:00" },
        { "id": 9, "name": "Chint −15%", "date": "2026-10-05T00:00:00" }
      ]
    }
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `total` | qatorlar soni (`items` uzunligi) — menyudagi nishon |
| `banner_days` | `expiring_banners` oynasi, hozir `3` kun |
| `items[]` | faqat `count > 0` bo'lgan qatorlar; tartib tayyor: guruh bo'yicha (`orders` → `catalog` → `feedback` → `content`), guruh ichida muhimlik bo'yicha |
| `items[].key` | qator turi — pastdagi jadval. Matn (sarlavha, izoh) frontendda `key` bo'yicha yoziladi |
| `items[].group` | `orders` / `catalog` / `feedback` / `content` |
| `items[].level` | `danger` / `warning` / `info` — ikonka rangi |
| `items[].count` | nechta obyekt |
| `items[].amount` | faqat `refund_pending_orders`: buyurtmalar summasi; qolganlarida `null` |
| `items[].date` | eng shoshilinch obyektning sanasi (`objects[0].date`), `null` bo'lishi mumkin |
| `items[].objects[]` | eng shoshilinch **3 tagacha** obyekt: `id`, `name`, `date` |

Qatorlar:

| `key` | `group` | `level` | Nima sanaladi | `date` | `objects[].name` | "Ochish" → ro'yxat |
| --- | --- | --- | --- | --- | --- | --- |
| `stale_pending_orders` | orders | warning | 30 daqiqadan ko'p "Kutilmoqda" turgan buyurtmalar | yaratilgan vaqt (eng eskisi) | `null` | `orders/?status=0&ordering=created_at` |
| `refund_pending_orders` | orders | warning | bekor qilingan (`status=4`), lekin to'lovi `Hold`/`To'langan` buyurtmalar — pul qaytarilmagan | oxirgi o'zgargan vaqt | `null` | `orders/?status=4&payment_status=1` va `...&payment_status=2` |
| `unassigned_orders` | orders | info | menejer biriktirilmagan ochiq buyurtmalar (`status` 0–2) | yaratilgan vaqt | `null` | `orders/?status=0&status=1&status=2&has_manager=false` |
| `out_of_stock_products` | catalog | danger | faol, qoldig'i `<= 0` mahsulotlar | `null` | mahsulot nomi | `products/?is_active=true&in_stock=false` |
| `no_price_products` | catalog | danger | faol, narxi `0` mahsulotlar | `null` | mahsulot nomi | `products/?is_active=true&max_price=0` |
| `review_products` | catalog | info | moderatsiyadagi mahsulotlar (`publish_status=review`) | `null` | mahsulot nomi | `products/?publish_status=review` |
| `unanswered_questions` | feedback | warning | ko'rinadigan, admin javob bermagan savollar | savol vaqti | savol matni | `questions/?is_visible=true&answered=false` |
| `unanswered_chats` | feedback | warning | oxirgi xabari mijozdan bo'lgan chatlar | oxirgi xabar vaqti | `null` | `chats/?unanswered=true` |
| `moderation_queue` | feedback | info | savollarga mijozlar yozgan, hali tasdiqlanmagan javoblar | javob vaqti | javob matni | `question-replies/?is_visible=false&is_admin=false` |
| `expiring_banners` | content | warning | faol, `banner_days` kun ichida tugaydigan bannerlar | tugash vaqti (`ends_at`) | banner nomi | `banners/?status=active&ordering=ends_at` |
| `draft_notifications` | content | info | qoralama bildirishnomalar (hali e'lon qilinmagan) | `publish_at` | sarlavha | `notifications/?status=draft` |

`unanswered_questions`, `unanswered_chats`, `moderation_queue`, `out_of_stock_products` — bosh sahifadagi (`dashboard/` → `attention`) sonlar bilan bir xil qoida.

### `catalog` — katalog holati

```json
"catalog": {
  "published": 18402,
  "draft": 1136,
  "review": 28,
  "incomplete": 1492,
  "no_translation": 612,
  "no_image": 488,
  "no_characteristics": 392,
  "out_of_stock": 7
}
```

| Maydon | Izoh |
| --- | --- |
| `published`, `draft`, `review` | **barcha** mahsulotlar `publish_status` bo'yicha (nashr etilgan / qoralama / moderatsiyada); yig'indisi = jami mahsulotlar |
| `incomplete` | to'liqsiz **faol** mahsulotlar: pastdagi uchtadan kamida bittasi yetishmaydi |
| `no_translation` | faol, `name_uz` yoki `name_ru` bo'sh |
| `no_image` | faol, rasmi yo'q |
| `no_characteristics` | faol, birorta ham atribut qiymati yo'q |
| `out_of_stock` | faol, qoldig'i `<= 0` |

`no_translation` + `no_image` + `no_characteristics` kesishadi — yig'indisi `incomplete` dan katta bo'lishi mumkin.

> `publish_status` hozircha faqat admin panelda qo'lda qo'yiladigan maydon: mijozga ko'rinish `is_active` ga bog'liq.
> Shuning uchun `incomplete` / `out_of_stock` **faol** (`is_active=true`) mahsulotlardan sanaladi, `published` dan emas.

### `orders_chart` — buyurtmalar, 7 kun

```json
"orders_chart": {
  "days": 7,
  "count": 711,
  "average_per_day": 102,
  "points": [
    { "date": "2026-09-27", "count": 90, "total": 71400000.0 },
    { "date": "2026-10-03", "count": 78, "total": 61240000.0 }
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `days` | har doim `7` (bugun ham kiradi; bugungi ustun — hozirgacha) |
| `count` | davrda yaratilgan barcha buyurtmalar (holatidan qat'i nazar) |
| `average_per_day` | `count / days`, butun songa yaxlitlangan |
| `points[]` | har bir kun: `date`, `count`, `total` (summa); bo'sh kunlar `0` bilan, eskidan yangiga |

### `recent_orders` — oxirgi buyurtmalar

Oxirgi **10 ta** buyurtma (yangi birinchi). Obyekt `orders/` ro'yxatidagi bilan bir xil — maydonlar `dashboard.md` → `recent_orders` da.

---

## Dizaynda bor, API'da yo'q

| Dizayndagi element | Sabab |
| --- | --- |
| 1C bloklari: "1C · 16:46 · OK", "1C sinxronizatsiya", "1C xatosi bor buyurtmalar", "1C'da qabul qilinmagan", jadvaldagi 1C ustuni, "Bog'lanmagan SKU" | hozircha hisobga olinmagan |
| Sayt / Ilova bo'linishi (grafik), jadvaldagi "Kanal" ustuni | buyurtmada kanal (sayt / iOS / Android) saqlanmaydi |
| "Bugun yetkaziladi: 17" | buyurtmada yetkazish sanasi yo'q |
| "Yetkazib berish amalga oshmadi" | yetkazish xatosi holati saqlanmaydi |
| "Karta moderatsiyadan qaytarildi" | "qaytarilgan" holati yo'q — o'rniga `review_products` (moderatsiyada turganlar) |
| "Nashr etilmagan sahifalar" | statik sahifalar modeli yo'q |
| "Tasdiq kutayotgan push kampaniya" | tasdiqlash jarayoni yo'q — o'rniga `draft_notifications` (qoralamalar) |
