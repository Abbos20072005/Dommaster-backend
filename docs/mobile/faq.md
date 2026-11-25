# FAQ (savol-javob) — mobile / sayt uchun

| Endpoint | Nima uchun |
| --- | --- |
| `GET /api/v1/faq/` | statik kategoriyalar (Umumiy, Texnik, To'lov, Buyurtmalar, Yetkazib berish) va ularning faol savollari (`/faq` sahifasi) |
| `GET /api/v1/faq/?page=<key>` | faqat shu sahifaga bog'langan savollar (axborot sahifalaridagi FAQ bloki) |

Ochiq endpoint: token kerak emas, cookie ishlatilmaydi. Swagger: `/swagger/` → **FAQ**.

Savol-javoblar admin paneldan boshqariladi. Matn bitta, lekin bitta savol bir nechta sahifada chiqishi mumkin.

## Qachon chaqiriladi

| Sahifa (sayt / ilova) | So'rov |
| --- | --- |
| `/faq` — to'liq FAQ | `GET /api/v1/faq/` |
| `/faq` — faqat shu sahifaga belgilanganlar kerak bo'lsa | `GET /api/v1/faq/?page=faq` |
| `/courier-delivery` | `?page=courier-delivery` |
| `/payment-methods` | `?page=payment-methods` |
| `/returns` | `?page=returns` |
| `/pickup` | `?page=pickup` |
| `/legal-entities` | `?page=legal-entities` |
| PRO sahifasi | `?page=pro` |

`page` qiymatlari faqat shular. Boshqa qiymat → `400`.

## Javob

```json
{
  "result": [
    {
      "slug": "payment",
      "name": "To'lov",
      "questions": [ ... ]
    },
    {
      "slug": "delivery",
      "name": "Yetkazib berish",
      "questions": [
        {
          "id": 4,
          "question": "Yetkazib berish qancha vaqt oladi?",
          "answer": "<p>Toshkent bo'ylab <b>1–2 kun</b>.</p><ul><li>...</li></ul>",
          "page_keys": ["faq", "courier-delivery"],
          "updated_at": "2026-11-24T14:10:00.000000"
        }
      ]
    }
  ],
  "ok": true
}
```

| Maydon | Izoh |
| --- | --- |
| `result[]` | **statik kategoriyalar** (sahifadagi tablar), har doim shu tartibda: `general` (Umumiy), `technical` (Texnik), `payment` (To'lov), `orders` (Buyurtmalar), `delivery` (Yetkazib berish). Faqat faol savoli bor kategoriyalar keladi (`?page=` bilan — shu sahifada savoli bor kategoriyalar). Hech narsa bo'lmasa `[]`. Kategoriyalar admin tomonidan o'zgarmaydi, `id` yo'q |
| `slug` | kategoriyaning doimiy kaliti (yuqoridagi 5 ta qiymat); anchor / ikonka tanlash uchun ishlatsa bo'ladi |
| `name` | kategoriya nomi, so'rov tilida |
| `questions[]` | kategoriyaning faol savollari, admindagi tartibda |
| `questions[].question` | savol — **oddiy matn**. Matn sifatida chiqaring (escape qiling), HTML sifatida render qilmang |
| `questions[].answer` | javob — **cheklangan HTML**: `<a href>`, `<b>`, `<strong>`, `<ul>`, `<ol>`, `<li>`, `<p>`, `<br>`. Server boshqa teglar va atributlarni olib tashlagan. `href`: `https://`, `http://`, `mailto:`, `tel:` yoki sayt ichidagi yo'l (`/returns`) |
| `questions[].page_keys` | savol qaysi sahifalarda chiqadi |
| `questions[].updated_at` | savol oxirgi marta qachon o'zgargan (Toshkent vaqti) |

## Til

`Accept-Language: uz` → o'zbekcha, `ru` (yoki boshqa / yo'q) → ruscha. Admin ikkala tilni ham majburiy to'ldiradi.

## Kesh

Server javobni 15 daqiqa keshlaydi. Admindagi o'zgarishda kesh darhol tozalanadi. Sayt o'z keshini (ISR / revalidate) 15 daqiqadan uzun qilmasin.

## Xatolar

| Status | `error_code` | Qachon |
| --- | --- | --- |
| `400` | `5` | noma'lum `page` qiymati; `detail` da ruxsat etilgan qiymatlar ko'rsatiladi |

## Frontda qilinadigan ishlar

1. `/faq` sahifasi: `GET /api/v1/faq/` → kategoriya tablari (`name`) + tanlangan kategoriyaning accordion (savol / javob) ro'yxati.
2. Axborot sahifalari: `GET /api/v1/faq/?page=<key>` → sahifa oxirida FAQ bloki. Bo'sh `result` bo'lsa, blokni ko'rsatmang.
3. `answer` ni HTML sifatida render qiling (sayt: `dangerouslySetInnerHTML` / ilova: HTML-matn vidjeti). `question` va `name` ni oddiy matn sifatida chiqaring.
4. Sayt ichidagi havolalarni (`/returns`) sayt routeri bilan oching. Ilovada ularni mos ekranga yoki `https://buildex.uz` + yo'l bo'yicha oching.
5. SEO uchun FAQPage JSON-LD kerak bo'lsa, uni sayt shu javobdan quradi.
