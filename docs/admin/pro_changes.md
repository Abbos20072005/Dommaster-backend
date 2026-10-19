# PRO mijozlar — admin panel uchun o'zgarishlar

Base URL: `{{host}}/api/v1/admin/`

Mijozga PRO maqomi berish / olib qo'yish va PRO mijozlar loyihalarini ko'rish. To'liq tavsif:
[pro_customers.md](pro_customers.md).

## Mavjud endpointlarda nima o'zgardi

| Endpoint | Oldin | Hozir | Eski front buziladimi |
| --- | --- | --- | --- |
| `GET customers/`, `customers/<id>/` | — | `+ account_type`: `customer` / `pro` (faqat o'qiladi) | yo'q |
| `PATCH customers/<id>/` | — | `account_type` yuborilsa **e'tiborga olinmaydi** | yo'q |
| `GET customers/?account_type=pro` | — | yangi filtr | yo'q |
| `GET customers/stats/` | `total, active, b2b, blocked` | `+ pro` | yo'q |
| `PATCH orders/<id>/` (`order_items`) | qatorlar qayta yaratiladi | o'zgarmagan; buyurtmada qolgan mahsulot loyihaga bog'lanishini saqlaydi | yo'q |

`role` (`user` / `prorab`) va `b2b` hisobi o'zgarmagan. PRO alohida maqom, mavjud `prorab` mijozlar PRO ga
o'tkazilmagan.

## Yangi endpointlar

| Endpoint | Nima qiladi |
| --- | --- |
| `POST customers/<id>/account-type/` | PRO berish / olib qo'yish: `{"account_type": "pro" \| "customer", "reason": "..."}`; javob = mijoz detali |
| `GET customers/<id>/account-type-history/` | o'zgarishlar tarixi (sahifalangan): `old_value, new_value, changed_by, reason, created_at` |
| `GET pro-projects/` | barcha mijozlarning loyihalari, faqat o'qish; filtr `customer`, `status`, `has_items`, `search` |
| `GET pro-projects/<id>/` | loyiha + `expenses` (jami) + `categories` |

`account-type/` da `400` qachon chiqadi:

- PRO olib qo'yilayotganda `reason` bo'sh bo'lsa;
- yuborilgan qiymat hozirgisi bilan bir xil bo'lsa.

## Frontda qilinadigan ishlar

1. Mijozlar ro'yxati: "PRO" belgisi (`account_type == "pro"`) va filtr (`?account_type=pro`), statistika kartasida
   `pro`.
2. Mijoz kartasi: "PRO berish" / "PRO ni olish" tugmasi. Olishda sabab maydoni majburiy. Ostida
   `account-type-history/` ro'yxati.
3. Mijoz kartasida "Loyihalar" bloki: `pro-projects/?customer=<id>`. Tahrirlash tugmalari yo'q — admin faqat
   ko'radi.
