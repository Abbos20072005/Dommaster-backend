# FAQ (savol-javob) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`, admin bo'lmagan token → `403`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET faq-topics/` | mavzular ro'yxati (paginatsiyali) |
| `POST faq-topics/` | mavzu yaratish (JSON) |
| `GET / PATCH / PUT / DELETE faq-topics/{id}/` | bitta mavzu |
| `POST faq-topics/reorder/` | mavzular tartibi (drag & drop) |
| `GET faq-items/` | savollar ro'yxati (paginatsiyali) |
| `POST faq-items/` | savol yaratish (JSON) |
| `GET / PATCH / PUT / DELETE faq-items/{id}/` | bitta savol |
| `POST faq-items/reorder/` | bitta mavzu ichidagi savollar tartibi (drag & drop) |

Swagger: `/swagger/admin/` → **faq-topics**, **faq-items**.

> FAQ — sayt va ilova uchun yagona savol-javob manbai. **Mavzu** (Yetkazib berish, To'lov, ...) ichida **savollar** turadi. Har bir savolning matni bitta, lekin u bir nechta sahifada chiqishi mumkin: bu `page_keys` ro'yxati bilan belgilanadi. Sayt va ilova ro'yxatni ochiq `GET /api/v1/faq/` orqali oladi. Admindagi o'zgarish u yerda **darhol** ko'rinadi, chunki kesh tozalanadi.

---

## 1. Mavzu (`faq-topics/`)

### Obyekt

```json
{
  "id": 1,
  "name": "Доставка",
  "name_uz": "Yetkazib berish",
  "name_ru": "Доставка",
  "slug": "delivery",
  "position": 1,
  "is_active": true,
  "items_count": 6,
  "created_at": "2026-11-24T14:02:11.120334",
  "updated_at": "2026-11-24T14:02:11.120334"
}
```

| Maydon | Izoh |
| --- | --- |
| `name_uz` * | nom, o'zbekcha, 150 belgigacha; bo'sh bo'lsa saqlanmaydi |
| `name_ru` * | nom, ruscha, 150 belgigacha; bo'sh bo'lsa saqlanmaydi |
| `slug` * | unikal; faqat lotin harflari, raqamlar, `-`, `_` (100 belgigacha). Taklif: `delivery`, `payment`, `returns`, `pickup`, `legal-entities`, `pro`, `general` |
| `is_active` | default `true`; `false` bo'lsa mavzu va uning hamma savollari sayt / ilovada chiqmaydi |

Faqat o'qiladi: `id`, `name` (ruscha nom), `position` (yangi mavzu oxiriga qo'shiladi, tartib `reorder/` bilan o'zgartiriladi), `items_count` (mavzudagi savollar soni, nofaollari ham), `created_at`, `updated_at`.

Yaratish (`POST faq-topics/` → `201` + obyekt):

```json
{ "name_uz": "Yetkazib berish", "name_ru": "Доставка", "slug": "delivery" }
```

`PATCH faq-topics/{id}/` — faqat yuborilgan maydonlar o'zgaradi.

**O'chirish**: `DELETE faq-topics/{id}/` → `204`. Mavzuda savol bor bo'lsa, o'chirilmaydi: `400 {"detail": "Topic has questions, ..."}`. Avval savollarni boshqa mavzuga o'tkazing yoki o'chiring. Yashirish uchun `is_active: false` qilish kifoya.

### Ro'yxat

`GET faq-topics/?page=1&page_size=20` → `count, next, previous, next_page, previous_page, results` (default 20 ta, max 100).

| Parametr | Izoh |
| --- | --- |
| `is_active` | `true` / `false` |
| `search` | `name_uz`, `name_ru`, `slug` bo'yicha |
| `ordering` | `position` (default), `id`, `name_ru`, `name_uz`, `items_count`, `created_at`, `updated_at` (`-` = teskari) |

### Tartib

`POST faq-topics/reorder/`

```json
{ "ids": [3, 1, 2] }
```

Ro'yxatdagi indeks `position` bo'ladi. Yuborilmagan mavzular ulardan keyin, eski tartibida qoladi. Javob: `200 {"ids": [...]}`. Takroriy yoki mavjud bo'lmagan id → `400`.

---

## 2. Savol (`faq-items/`)

### Obyekt

```json
{
  "id": 12,
  "topic": { "id": 3, "name": "Возврат", "slug": "returns", "is_active": true },
  "question": "Можно ли вернуть товар?",
  "question_uz": "Mahsulotni qaytarsa bo'ladimi?",
  "question_ru": "Можно ли вернуть товар?",
  "answer": "<p>Да, в течение <b>14 дней</b>. <a href=\"/returns\" rel=\"noopener noreferrer\">Подробнее</a></p>",
  "answer_uz": "<p>Ha, <b>14 kun</b> ichida. <a href=\"/returns\" rel=\"noopener noreferrer\">Batafsil</a></p>",
  "answer_ru": "<p>Да, в течение <b>14 дней</b>. <a href=\"/returns\" rel=\"noopener noreferrer\">Подробнее</a></p>",
  "page_keys": ["faq", "returns"],
  "position": 1,
  "is_active": true,
  "created_at": "2026-11-24T14:10:00.000000",
  "updated_at": "2026-11-24T14:10:00.000000"
}
```

| Maydon | Izoh |
| --- | --- |
| `topic` * | mavzu: `{"id": 3}` yoki shunchaki `3`; javobda obyekt bo'lib keladi |
| `question_uz` * | savol, o'zbekcha, 500 belgigacha, oddiy matn (HTML emas) |
| `question_ru` * | savol, ruscha, 500 belgigacha, oddiy matn |
| `answer_uz` * | javob, o'zbekcha, **cheklangan HTML** (pastda) |
| `answer_ru` * | javob, ruscha, cheklangan HTML |
| `page_keys` | savol qaysi sahifalarda chiqadi. Qiymatlar: `faq`, `courier-delivery`, `payment-methods`, `returns`, `pickup`, `legal-entities`, `pro`. Yaratishda yuborilmasa `["faq"]` bo'ladi. Takrorlar olib tashlanadi, `[]` = hech qaysi sahifaga bog'lanmagan (faqat umumiy `GET /api/v1/faq/` da chiqadi) |
| `is_active` | default `true`; `false` = sayt / ilovada chiqmaydi |

Faqat o'qiladi: `id`, `question` / `answer` (ruscha), `position` (yangi savol mavzusining oxiriga qo'shiladi; savol boshqa mavzuga o'tkazilsa, o'sha mavzuning oxiriga tushadi), `created_at`, `updated_at`.

**Ikkala til majburiy**: `*_uz` yoki `*_ru` bo'sh bo'lsa, savol saqlanmaydi (`400`) va xatoda qaysi maydon bo'shligi ko'rsatiladi. Bu `PATCH` ga ham tegishli: `"answer_ru": ""` → `400`.

```json
{ "question_uz": ["This field may not be blank."], "answer_uz": ["The answer has no text after cleaning."] }
```

### Javob HTML'i

Saqlashda javob tozalanadi, faqat quyidagilar qoladi:

| Teg | Izoh |
| --- | --- |
| `<a href="...">` | havola: `https://`, `http://`, `mailto:`, `tel:` yoki sayt ichidagi yo'l (`/returns`). Boshqa `href` (masalan, `javascript:`) olib tashlanadi, matn qoladi. `rel="noopener noreferrer"` o'zi qo'shiladi |
| `<b>`, `<strong>` | qalin |
| `<ul>`, `<ol>`, `<li>` | ro'yxat |
| `<p>`, `<br>` | paragraf, yangi qator |

Boshqa teglar (`<i>`, `<span>`, `<img>`, `<h2>` ...) olib tashlanadi, matni qoladi. `<script>`, `<style>`, `<iframe>` matni bilan birga o'chiriladi. `href` dan boshqa barcha atributlar (`style`, `class`, `onclick` ...) ham o'chiriladi. Tozalangandan keyin javobda matn qolmasa → `400`. Javobda qaytadigan HTML — saqlangan, tozalangan variant. Admin muharririda shu teglar bilan ishlaydigan oddiy rich-text yetarli.

### Yaratish / tahrirlash

`POST faq-items/` → `201` + obyekt:

```json
{
  "topic": 3,
  "question_uz": "Mahsulotni qaytarsa bo'ladimi?",
  "question_ru": "Можно ли вернуть товар?",
  "answer_uz": "<p>Ha, <b>14 kun</b> ichida.</p>",
  "answer_ru": "<p>Да, в течение <b>14 дней</b>.</p>",
  "page_keys": ["faq", "returns"]
}
```

`PATCH faq-items/{id}/` — faqat yuborilgan maydonlar o'zgaradi. `page_keys` yuborilsa, ro'yxat to'liq almashtiriladi.

`DELETE faq-items/{id}/` → `204`.

### Ro'yxat

`GET faq-items/?page=1&page_size=20` → `count, next, previous, next_page, previous_page, results`. Default tartib: mavzu tartibi, keyin mavzu ichidagi savol tartibi.

| Parametr | Izoh |
| --- | --- |
| `topic` | mavzu id |
| `is_active` | `true` / `false` |
| `page_key` | shu sahifaga bog'langan savollar (`returns`, `pickup`, ...). E'tibor bering: `page` emas — `page` sahifalash uchun |
| `search` | `question_uz/ru`, `answer_uz/ru` bo'yicha |
| `ordering` | `position`, `id`, `created_at`, `updated_at` (`-` = teskari) |

### Tartib

`POST faq-items/reorder/`

```json
{ "ids": [15, 12, 14] }
```

Faqat **bitta mavzuning** savollari yuboriladi (turli mavzular aralashsa → `400 "Questions of one topic only."`). Indeks `position` bo'ladi, mavzuning yuborilmagan savollari ulardan keyin qoladi. Javob: `200 {"ids": [...]}`.

---

## Xatolar

| Status | Qachon |
| --- | --- |
| `400` | majburiy maydon bo'sh / yo'q, noto'g'ri `page_keys` qiymati, `slug` band, javobda matn qolmagan, savoli bor mavzuni o'chirish, `reorder` da takroriy / mavjud bo'lmagan id yoki turli mavzular |
| `401` | token yo'q yoki eskirgan |
| `403` | admin emas |
| `404` | mavzu / savol topilmadi |
