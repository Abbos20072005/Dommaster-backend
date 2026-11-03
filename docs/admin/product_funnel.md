# Tovar voronkasi — admin panel uchun («Tahlil → Savdo»)

BLD-372: har bir tovar bo'yicha tanlangan davrda **ko'rish → savatga qo'shish → rasmiylashtirish → xarid**. Hodisalarni sayt va ilova yuboradi (BLD-378, `docs/mobile/product_events.md`). Ma'lumot ular yubora boshlagan kundan yig'iladi, o'tmish yo'q.

Base URL: `{{host}}/api/v1/admin/`. Token: `Authorization: Bearer <admin access token>`.

| Metod | URL | Nima |
| --- | --- | --- |
| GET | `analytics/product-funnel/` | jadval (sahifalangan) |
| GET | `analytics/product-funnel/export/` | shu jadval Excel (`.xlsx`) — hamma qatorlar, sahifalashsiz |

Swagger: `/swagger/admin/` → **analytics**.

## Query parametrlari

| Parametr | Default | Nima |
| --- | --- | --- |
| `days` | `30` | bugun bilan tugaydigan oxirgi N kun (1–365) |
| `date_from` + `date_to` | — | `days` o'rniga aniq oraliq (ikkalasi birga, ikkala kun ham kiradi, Toshkent vaqti) |
| `channel` | `all` | `all` / `site` / `app` (ilova = iOS + Android) |
| `search` | — | nom (uz yoki ru) yoki artikul bo'yicha qidiruv |
| `ordering` | `-views,-purchases` | istalgan ustun: `views`, `add_to_cart`, `checkout_start`, `purchases`, `incomplete`, `completion_rate`, `other_purchases`, `name_ru`, `articul_code`, `id`; kamayish = `-` bilan. `completion_rate` bo'sh (null) qatorlar ikkala yo'nalishda ham oxirida |
| `page`, `page_size` | `1`, `20` | sahifa, hajm (maks. 100) |
| `language` | `ru` | **faqat `export/`**: Excel sarlavhalari va tovar nomi tili (`ru` / `uz`) |

## Javob

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "next_page": null,
  "previous_page": null,
  "results": [
    {
      "id": 1234,
      "name": "Перфоратор Bosch GBH 2-26",
      "articul_code": "0611253768",
      "image": "https://api.buildex.uz/media/product/bosch.jpg",
      "views": 17,
      "add_to_cart": 6,
      "checkout_start": 5,
      "purchases": 2,
      "incomplete": 3,
      "completion_rate": 40.0,
      "other_purchases": 0
    },
    {
      "id": 1240,
      "name": "Молоток 500 г",
      "articul_code": "ART-B",
      "image": null,
      "views": 3,
      "add_to_cart": 0,
      "checkout_start": 0,
      "purchases": 1,
      "incomplete": -1,
      "completion_rate": null,
      "other_purchases": 0
    }
  ]
}
```

| Ustun (dizayn) | Kalit | Formula |
| --- | --- | --- |
| Ko'rishlar | `views` | tovar kartasi ochilishlari (`product_view`) |
| Savatga qo'shish | `add_to_cart` | savatga qo'shishlar |
| Rasmiylashtirishni boshlash | `checkout_start` | rasmiylashtirish ochilganda savatda belgilangan bo'lgan marta |
| Xaridlar | `purchases` | shu tovar bor **«Yakunlandi»** buyurtmalar soni (buyurtma davrga yaratilgan sanasi bo'yicha, dashboard «Umumiy daromad» qoidasi; bitta buyurtma = 1, miqdordan qat'i nazar), sayt / ilova kanalidan |
| Yakunlanmagan | `incomplete` | `checkout_start − purchases` |
| Yakunlangan ulushi | `completion_rate` | `purchases / checkout_start × 100`, 1 xonagacha. `checkout_start = 0` → **`null`** — «—» ko'rsating, «0%» emas |
| — | `other_purchases` | kanalsiz buyurtmalar: admin panelda operator yaratgan (va eski ilova versiyalari). Ularda rasmiylashtirish bo'lmaydi, shuning uchun `purchases` / `incomplete` / ulushga **kirmaydi**; faqat `channel=all` da, qolganida `0`. Panelda alohida ustun yoki tooltip bilan ko'rsatsa bo'ladi |

- `name` — ru nomi (Excel'da `language=uz` bo'lsa uz, bo'sh bo'lsa ru). `image` — asosiy (birinchi) rasm, yo'q bo'lsa `null`.
- `incomplete` manfiy bo'lishi mumkin: xarid rasmiylashtirishdan ko'p — masalan, hodisalar yig'ila boshlashidan oldin rasmiylashtirilib, keyin yakunlangan buyurtma yoki eski ilova versiyasi (hodisa yubormaydi). Bu holat vaqt o'tishi bilan kamayadi.
- **Qaysi tovarlar chiqadi:** davrda kamida bitta hodisasi yoki xaridi bor tovarlar (tanlangan kanal bo'yicha). Hech narsasi yo'q tovar ro'yxatda yo'q — qidiruvda ham.

## Excel

`GET analytics/product-funnel/export/?date_from=2026-10-05&date_to=2026-11-03&channel=site&ordering=-purchases&search=bosch&language=uz`

Jadval bilan bir xil filtr va saralash, `page` / `page_size` e'tiborga olinmaydi — hamma qatorlar. Ustunlar: ID, Nomi, Artikul, Ko'rishlar, Savatga qo'shish, Rasmiylashtirishni boshlash, Xaridlar, Yakunlanmagan, Yakunlangan ulushi %, Kanalsiz xaridlar (operator). Ulush bo'sh bo'lsa katak bo'sh. Rasm Excel'ga kirmaydi. Fayl nomi `product_funnel_YYYYMMDD_HHMM.xlsx`.
