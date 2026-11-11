# Buyurtma statuslari o'zgardi — admin panel uchun

**02.11.2026 dan** buyurtma `status` kodlari yangilandi: yangi **«Tasdiqlangan»** (`1` Confirmed) statusi qo'shildi va kodlar buyurtma yo'li tartibida qayta raqamlandi. Endpoint'lar va maydon nomlari o'zgarmadi.

## Yangi kodlar

| `status` | Backend nomi | Panelda | Oldingi kodi |
| --- | --- | --- | --- |
| `0` | Pending | Tushgan | `0` |
| `1` | Confirmed | **Tasdiqlangan** (yangi) | — |
| `2` | Collecting | Tayyorlash (yig'ilmoqda) | `1` |
| `3` | Delivering | Yetkazilmoqda | `2` |
| `4` | Ready for pickup | Olib ketishga tayyor (faqat olib ketish) | `5` |
| `5` | Completed | Yakunlandi | `3` |
| `6` | Canceled | Bekor qilingan | `4` |

- `1` ni faqat admin panel qo'yadi (`PATCH orders/<id>/` `{"status": 1}`). 1C bu statusni yubormaydi. Online to'lovdan keyin buyurtma avvalgidek darhol `2` ga o'tadi.
- Qoldiq (`Product.quantity`) avvalgidek `2` Collecting ga o'tganda kamayadi. `1` da qoldiq olinmaydi, bekor qilinsa qaytariladigan narsa yo'q.
- Qoidalar ma'nosi bo'yicha o'zgarmadi: `4` faqat pickup buyurtmaga va faqat `2` dan qo'yiladi; `4` dan faqat `5` yoki `6`; mahsulotlarni faqat `0` da o'zgartirish mumkin; `2` / `3` / `4` dagi buyurtmani o'chirib bo'lmaydi.
- Har status o'zgarishi endi jurnalga yoziladi (admin panel, 1C, to'lov, mijoz): "Buyurtma bosqichlari vaqti" grafigi shundan hisoblanadi (`dashboard_order_stages.md`). Jurnal 02.11.2026 dan boshlanadi.

## 02.11.2026 dan oldingi buyurtmalar

Migration bazadagi eski buyurtmalarning raqamini o'zgartirmagan edi: 02.11.2026 dan oldin yaratilgan buyurtmalar eski kod bilan qolgan va panelda noto'g'ri ko'ringan (masalan, bekor qilingan `4` "Olib ketishga tayyor" bo'lib chiqqan, yakunlangan `3` esa "Yetkazilmoqda" bo'lib chiqqan). Ular `manage.py convert_old_order_statuses` bilan yangi kodlarga o'tkaziladi (eski kod → yangi kod, yuqoridagi jadval bo'yicha). Shundan keyin `orders/`, filtrlar, `stats/` va dashboard eski buyurtmalarni ham to'g'ri ko'rsatadi. Frontda hech narsa qilish kerak emas. Bu buyurtmalarning status jurnali yo'q, shu sababli ular "Buyurtma bosqichlari vaqti" grafigiga tushmaydi.

## Nima o'zgardi

| Endpoint | Oldin | Hozir | Eski front buziladimi |
| --- | --- | --- | --- |
| `orders/`, `orders/<id>/`, `dashboard/` `recent_orders`, `today/` `recent_orders` — `status` | `0`–`5` | `0`–`6` (yangi ma'no) | **ha** — nomlar xaritasini yangilang |
| `orders/?status=` filtri | eski kodlar | yangi kodlar | **ha** — tab / filtr qiymatlarini yangilang |
| `orders/stats/` | `pending`, `collecting`, ... | + **`confirmed`** | yo'q (yangi maydon) |
| `today/` `cards` | `pending`, `collecting`, `delivering` | + **`confirmed`** | yo'q |
| `today/` `attention.unassigned_orders` | ochiq = `0`, `1`, `2`, `5` | ochiq = `0`–`4` (`orders/?status=0&status=1&status=2&status=3&status=4&has_manager=false`) | "Ochish" havolasini yangilang |
| `today/` `attention.refund_pending_orders` | `status=4` | `status=6` | havolani yangilang |
| `orders/?pickup_expired=` / `ready_for_pickup` | status `5` | status `4` | havolalarni yangilang |
| Mijozlar `orders_count` / `returns_count` | status `3` / `4` | status `5` / `6` | yo'q (son o'zi hisoblanadi), lekin `orders/?customer=<id>&status=6` havolasini yangilang |

## Yangi endpoint

`GET dashboard/order-stages/` — buyurtma bosqichlari vaqti, oylar bo'yicha: `dashboard_order_stages.md`.

## Frontda qilinadigan ishlar

1. Status nomlari / ranglari / tablari xaritasini yangi jadval bo'yicha yangilang, `1` Tasdiqlangan qo'shing.
2. Buyurtma kartasida status tanlash: `0 → 1 → 2 → ...`; "Tasdiqlash" tugmasi = `PATCH {"status": 1}`.
3. `?status=` bilan qurilgan barcha havolalar (bugungi ishlar, mijoz sahifasi, filtrlar) kodlarini yangilang.
4. `orders/stats/` va `today/` kartalariga `confirmed` hisoblagichini qo'shing (kerak bo'lsa).
