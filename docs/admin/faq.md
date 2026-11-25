# FAQ (savol-javob) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`, admin bo'lmagan token → `403`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET faq-items/` | savollar ro'yxati (paginatsiyali) |
| `POST faq-items/` | savol yaratish (JSON) |
| `GET / PATCH / PUT / DELETE faq-items/{id}/` | bitta savol |
| `POST faq-items/reorder/` | bitta kategoriya ichidagi savollar tartibi (drag & drop) |

Swagger: `/swagger/admin/` → **faq-items**.

> FAQ — sayt va ilova uchun yagona savol-javob manbai. Savol **kategoriyaga** kiradi; kategoriyalar **qat'iy (statik) ro'yxat**, admin ularni qo'sha, o'zgartira yoki o'chira olmaydi — faqat savolga kategoriyani tanlaydi (kategoriyalar uchun alohida endpoint yo'q, ro'yxat quyida). Bitta savolning matni bitta, lekin u bir nechta sahifada chiqishi mumkin: bu `page_keys` ro'yxati bilan belgilanadi. Sayt va ilova ro'yxatni ochiq `GET /api/v1/faq/` orqali oladi. Admindagi o'zgarish u yerda **darhol** ko'rinadi, chunki kesh tozalanadi.

## Kategoriyalar (statik)

Sayt FAQ sahifasidagi tablar shular, tartibi ham shu:

| `category` | O'zbekcha | Ruscha |
| --- | --- | --- |
| `general` | Umumiy | Общие |
| `technical` | Texnik | Технические |
| `payment` | To'lov | Оплата |
| `orders` | Buyurtmalar | Заказы |
| `delivery` | Yetkazib berish | Доставка |

Ro'yxatni panelda qattiq yozib qo'ying (select / tab). Boshqa qiymat → `400`.

---

## Obyekt

```json
{
  "id": 12,
  "category": "orders",
  "category_name": "Заказы",
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
| `category` * | yuqoridagi 5 ta qiymatdan biri |
| `question_uz` * | savol, o'zbekcha, 500 belgigacha, oddiy matn (HTML emas) |
| `question_ru` * | savol, ruscha, 500 belgigacha, oddiy matn |
| `answer_uz` * | javob, o'zbekcha, **cheklangan HTML** (pastda) |
| `answer_ru` * | javob, ruscha, cheklangan HTML |
| `page_keys` | savol qaysi sahifalarda chiqadi. Qiymatlar: `faq`, `courier-delivery`, `payment-methods`, `returns`, `pickup`, `legal-entities`, `pro`. Yaratishda yuborilmasa `["faq"]` bo'ladi. Takrorlar olib tashlanadi, `[]` = hech qaysi sahifaga bog'lanmagan (faqat umumiy `GET /api/v1/faq/` da chiqadi) |
| `is_active` | default `true`; `false` = sayt / ilovada chiqmaydi |

Faqat o'qiladi: `id`, `category_name` (kategoriya nomi, ruscha), `question` / `answer` (ruscha), `position` (yangi savol kategoriyasining oxiriga qo'shiladi; savol boshqa kategoriyaga o'tkazilsa, o'sha kategoriyaning oxiriga tushadi), `created_at`, `updated_at`.

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
  "category": "orders",
  "question_uz": "Mahsulotni qaytarsa bo'ladimi?",
  "question_ru": "Можно ли вернуть товар?",
  "answer_uz": "<p>Ha, <b>14 kun</b> ichida.</p>",
  "answer_ru": "<p>Да, в течение <b>14 дней</b>.</p>",
  "page_keys": ["faq", "returns"]
}
```

`PATCH faq-items/{id}/` — faqat yuborilgan maydonlar o'zgaradi. `page_keys` yuborilsa, ro'yxat to'liq almashtiriladi.

`DELETE faq-items/{id}/` → `204`.

## Ro'yxat

`GET faq-items/?page=1&page_size=20` → `count, next, previous, next_page, previous_page, results`. Default tartib: kategoriya tartibi (yuqoridagi jadvaldagidek), keyin kategoriya ichidagi savol tartibi.

| Parametr | Izoh |
| --- | --- |
| `category` | `general` / `technical` / `payment` / `orders` / `delivery` |
| `is_active` | `true` / `false` |
| `page_key` | shu sahifaga bog'langan savollar (`returns`, `pickup`, ...). E'tibor bering: `page` emas — `page` sahifalash uchun |
| `search` | `question_uz/ru`, `answer_uz/ru` bo'yicha |
| `ordering` | `position`, `id`, `created_at`, `updated_at` (`-` = teskari) |

## Tartib

`POST faq-items/reorder/`

```json
{ "ids": [15, 12, 14] }
```

Faqat **bitta kategoriyaning** savollari yuboriladi (turli kategoriyalar aralashsa → `400 "Questions of one category only."`). Indeks `position` bo'ladi, kategoriyaning yuborilmagan savollari ulardan keyin qoladi. Javob: `200 {"ids": [...]}`.

---

## Xatolar

| Status | Qachon |
| --- | --- |
| `400` | majburiy maydon bo'sh / yo'q, noto'g'ri `category` yoki `page_keys` qiymati, javobda matn qolmagan, `reorder` da takroriy / mavjud bo'lmagan id yoki turli kategoriyalar |
| `401` | token yo'q yoki eskirgan |
| `403` | admin emas |
| `404` | savol topilmadi |
