# Buyurtma bosqichlari vaqti — admin panel uchun

Dashboard grafigi: buyurtma har bosqichda qancha turadi, oylar bo'yicha. Uchta metrika:

| Kalit | Metrika | Boshlanish | Tugash |
| --- | --- | --- | --- |
| `confirm` | Tasdiqlashgacha vaqt | buyurtma yaratilgan payt | birinchi marta `1` Tasdiqlangan |
| `to_preparing` | Tayyorlashga o'tish vaqti | birinchi marta `1` Tasdiqlangan | birinchi marta `2` Tayyorlash |
| `delivery` | O'rtacha yetkazib berish vaqti | buyurtma yaratilgan payt | birinchi marta `5` Yakunlandi |

Base URL: `{{host}}/api/v1/admin/`. Token: `Authorization: Bearer <admin access token>` (faqat admin; tokensiz → `401`).

| Metod | URL | Nima |
| --- | --- | --- |
| GET | `dashboard/order-stages/` | tanlangan davrning har oyi uchun 3 metrika |

Swagger: `/swagger/admin/` → **dashboard**.

---

## So'rov

```
GET dashboard/order-stages/?period=quarter&delivery_method=all
```

| Parametr | Qiymatlar | Default | Izoh |
| --- | --- | --- | --- |
| `period` | `quarter` / `half_year` / `year` | `quarter` | oxirgi 3 / 6 / 12 kalendar oy, joriy oy ham kiradi |
| `delivery_method` | `all` / `courier` / `pickup` | `all` | `courier` = yetkazib berishli (`delivery_type=0`), `pickup` = olib ketishli (`delivery_type=1`) buyurtmalar; uchala metrikaga ta'sir qiladi |

Boshqa qiymat → `400 {"period": [...]}` / `{"delivery_method": [...]}`.

## Javob

```json
{
  "period": "quarter",
  "delivery_method": "all",
  "months": [
    {
      "month": "2026-09",
      "confirm":      { "avg_seconds": null, "median_seconds": null, "count": 0 },
      "to_preparing": { "avg_seconds": 2678400, "median_seconds": 2678400, "count": 1 },
      "delivery":     { "avg_seconds": 86400, "median_seconds": 86400, "count": 1 }
    },
    {
      "month": "2026-10",
      "confirm":      { "avg_seconds": 6300, "median_seconds": 5400, "count": 4 },
      "to_preparing": { "avg_seconds": 5400, "median_seconds": 5400, "count": 2 },
      "delivery":     { "avg_seconds": 129600, "median_seconds": 129600, "count": 2 }
    },
    {
      "month": "2026-11",
      "confirm":      { "avg_seconds": null, "median_seconds": null, "count": 0 },
      "to_preparing": { "avg_seconds": 1036800, "median_seconds": 1036800, "count": 1 },
      "delivery":     { "avg_seconds": 1123200, "median_seconds": 1123200, "count": 1 }
    }
  ]
}
```

| Maydon | Turi | Izoh |
| --- | --- | --- |
| `period`, `delivery_method` | string | qo'llangan qiymatlar |
| `months[]` | list | davrning **har bir** oyi, eskisidan yangisiga (`quarter` = 3 ta, `year` = 12 ta) |
| `month` | string | `YYYY-MM` — bosqich **tugagan** oy (Toshkent vaqti) |
| `avg_seconds` | int / null | o'rtacha, sekundda (butun songa yaxlitlangan) |
| `median_seconds` | int / null | mediana, sekundda; bitta qotib qolgan buyurtma o'rtachani buzadi, mediana buzilmaydi |
| `count` | int | hisobga kirgan buyurtmalar soni (tooltip uchun) |

Oyda buyurtma bo'lmasa `avg_seconds` / `median_seconds` = `null` (0 emas), `count` = `0`. Grafikda bo'sh nuqta qilib ko'rsating, 0 qilib emas.

## Hisoblash qoidalari

- **Manba — status jurnali.** Har status o'zgarishi (admin panel, 1C, to'lov tizimi, mijozning bekor qilishi) vaqti bilan yoziladi. Jurnal **02.11.2026 dan boshlanadi**, undan oldingi oylar bo'sh (`null`).
- **Takroriy status.** Buyurtma bir statusga bir necha marta o'tgan bo'lsa, birinchi o'tish olinadi.
- **Oy** = metrikaning tugash hodisasi bo'lgan oy. Masalan, oktyabrda tasdiqlanib noyabrda yig'ishga o'tgan buyurtma `confirm` da oktyabrga, `to_preparing` da noyabrga yoziladi. Oxirigacha yetmagan buyurtma o'sha metrikaga kirmaydi.
- **Kirmaydi:**
  - hozir bekor qilingan (`6`) buyurtmalar, hamma metrikadan;
  - bosqichni o'tkazib yuborgan buyurtma, faqat shu metrikadan. Masalan, `1` siz yig'ishga o'tgan buyurtma (online to'lovdan keyin to'g'ridan-to'g'ri `2`) `confirm` va `to_preparing` ga kirmaydi, lekin yakunlansa `delivery` ga kiradi.
- **Vaqt** — kalendar vaqt (kecha va dam olish kunlari ham), ish vaqti emas.
- Test buyurtmalarni ajratib bo'lmaydi (bunday belgi yo'q), ular ham hisobga kiradi.

## Xatolar

| Status | Qachon |
| --- | --- |
| `400` | `period` yoki `delivery_method` noto'g'ri |
| `401` | token yo'q / yaroqsiz |
| `403` | admin emas |
