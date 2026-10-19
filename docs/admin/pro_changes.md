# PRO mijozlar — admin panel uchun o'zgarishlar

Base URL: `{{host}}/api/v1/admin/`

Mijozga PRO maqomi berish / olib qo'yish va PRO mijozlar loyihalarini ko'rish. To'liq tavsif:
[pro_customers.md](pro_customers.md).

PRO = eski **prorab**: `role` = `prorab` — PRO, `user` — PRO emas. Yangi maydon yo'q, mavjud prorablar o'z-o'zidan
PRO.

## Mavjud endpointlarda nima o'zgardi

| Endpoint | Oldin | Hozir | Eski front buziladimi |
| --- | --- | --- | --- |
| `POST / PATCH customers/` → `role` | yozish mumkin edi | **faqat o'qiladi** (yuborilsa e'tiborga olinmaydi) — `customers/<id>/role/` orqali o'zgaradi | rol tahrirlash formasi ishlamay qoladi |
| `GET customers/`, `customers/<id>/`, `?role=`, `stats/` (`b2b`) | — | o'zgarmagan | yo'q |
| `PATCH orders/<id>/` (`order_items`) | qatorlar qayta yaratiladi | o'zgarmagan; buyurtmada qolgan mahsulot loyihaga bog'lanishini saqlaydi | yo'q |

## Yangi endpointlar

| Endpoint | Nima qiladi |
| --- | --- |
| `POST customers/<id>/role/` | PRO berish / olib qo'yish: `{"role": "prorab" \| "user", "reason": "..."}`; javob = mijoz detali |
| `GET customers/<id>/role-history/` | o'zgarishlar tarixi (sahifalangan): `old_value, new_value, changed_by, reason, created_at` |
| `GET pro-projects/` | barcha mijozlarning loyihalari, faqat o'qish; filtr `customer`, `status`, `has_items`, `search` |
| `GET pro-projects/<id>/` | loyiha + `expenses` (jami) + `categories` |

`role/` da `400` qachon chiqadi:

- PRO olib qo'yilayotganda (`prorab` → `user`) `reason` bo'sh bo'lsa;
- yuborilgan rol hozirgisi bilan bir xil bo'lsa.

## Frontda qilinadigan ishlar

1. Mijoz kartasi: rolni select bilan o'zgartirish o'rniga "PRO berish" / "PRO ni olish" tugmasi (`role/`). Olishda
   sabab maydoni majburiy. Ostida `role-history/` ro'yxati.
2. Mijozlar ro'yxatida "PRO" belgisi — `role == "prorab"` (filtr `?role=prorab`, karta `b2b`).
3. Mijoz kartasida "Loyihalar" bloki: `pro-projects/?customer=<id>`. Tahrirlash tugmalari yo'q — admin faqat
   ko'radi.
