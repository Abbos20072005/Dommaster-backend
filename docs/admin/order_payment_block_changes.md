# Buyurtma: to'lov bloki va «Loyiha» qatori — admin panel uchun o'zgarishlar

BLD-547 (backend), front: BLD-551. Launch audit 25.11, B-07.

Base URL: `{{host}}/api/v1/admin/`, header `Authorization: Bearer <admin access token>`.
Swagger: `/swagger/admin/` → `orders`.

## Nima o'zgardi

| Endpoint | Oldin | Hozir | Eski front buziladimi |
| --- | --- | --- | --- |
| `GET orders/`, `GET orders/<id>/` | to'lov usulini front `payment_type` / `payment_method` dan o'zi chiqarardi (#406: Atmos to'lovi «Qabulda · karta» bo'lib chiqqan) | yangi read-only **`payment_kind`**: `atmos` / `on_delivery` | yo'q, maydon qo'shildi |
| `GET orders/<id>/` | Atmos tranzaksiyasi yo'q edi | yangi read-only **`atmos_transaction`** (obyekt yoki `null`) | yo'q |
| `GET orders/<id>/` | «Loyiha» qatori uchun maydon yo'q edi | yangi read-only **`project`** (`{id, name, status}` yoki `null`), har bir `items[]` da ham **`project`** | yo'q |
| `PATCH orders/<id>/`, `POST orders/` | `payment_status` istalgan qiymatga o'zgarardi | Atmos (karta) buyurtmasida **o'zgarmaydi** → `400` | faqat to'lov holati dropdown'i (uni faqat o'qish uchun qiling) |
| `PATCH orders/<id>/` | `ofd_url` yozilardi | **read-only** (yuborilsa e'tiborga olinmaydi, xato bermaydi) | yo'q |
| `GET orders/<id>/` → `comments` | faqat izohlar va menejer o'zgarishi | to'lov holatining har o'zgarishi shu yerda **tizim izohi** bo'lib chiqadi | yo'q |

## 1. To'lov usuli — `payment_kind`

| Qiymat | Ma'nosi | Panelda yozuv (taklif) |
| --- | --- | --- |
| `atmos` | onlayn karta orqali Atmos. Mijoz to'lamagan bo'lsa ham shu: sayt / ilova hozir faqat shu usulni beradi | «Onlayn · karta (Atmos)» |
| `on_delivery` | qabul qilganda to'lash — faqat eski buyurtmalarda (25.11 dan beri yangi buyurtmada yo'q) | «Qabulda · naqd / karta» (`payment_method` `cash` / `card`) |

Qoida: buyurtmada `hold_id` bo'lsa → `atmos`; aks holda `payment_type = 4` → `on_delivery`; qolgan hamma holat → `atmos`.
Yozuvni **faqat `payment_kind` dan** chiqaring. `payment_type` raqamlari (0 / 1 / 2 / 3) eski Click / Payme / Uzum kodlari, ilova karta uchun 0 yoki 1 yuboradi — ularga qarab «Click», «Payme» deb yozmang. Staff Telegram guruhidagi yangi buyurtma xabari ham shu qoidaga o'tdi.

`payment_kind` ro'yxatda (`GET orders/`) ham bor.

## 2. To'lov holati — `payment_status`

`0` Kutilmoqda, `1` Muzlatilgan (Hold), `2` To'langan, `3` Qaytarilgan (bekor qilingan).

- **`payment_kind = atmos`**: holatni faqat Atmos javobi o'zgartiradi: mijoz to'laganda `0 → 1` (pul muzlatildi), operator buyurtmani tasdiqlaganda `1 → 2` (pul yechildi), muzlatilgan buyurtma bekor qilinganda `1 → 3` (pul qaytdi). Panel boshqa qiymat yuborsa:

```json
HTTP 400
{"payment_status": ["Set by Atmos only."]}
```

Formani to'liq qaytarib yuborsangiz, **hozirgi** qiymat bilan yuborilgan `payment_status` xato bermaydi. Dropdown o'rniga holatni oddiy yozuv qilib ko'rsating.
- **`payment_kind = on_delivery`** (eski buyurtmalar): holatni avvalgidek qo'lda o'zgartirish mumkin. Kim o'zgartirgani tarixda yoziladi (pastga qarang).
- Karta buyurtmasini xuddi shu so'rovda `payment_type: 4` ga o'tkazib holatni o'zgartirib bo'lmaydi: tekshiruv buyurtmaning so'rovdan **oldingi** usuliga qaraydi → `400`.
- `POST orders/` (paneldan yangi buyurtma): `payment_type: 4` bo'lmasa, `payment_status` faqat `0` bo'lishi mumkin.
- `ofd_url` (soliq cheki havolasi) endi read-only — uni ham faqat Atmos beradi.

## 3. Atmos tranzaksiyasi — `atmos_transaction`

Faqat buyurtma detalida. Pul yechilgandan keyin to'ladi, undan oldin `null`.

```json
"hold_id": 77,
"atmos_transaction": {
  "trans_id": 5,
  "success_trans_id": 6,
  "amount": 200000,
  "confirmed": true,
  "ofd_url": "https://ofd2.atmos.uz/api/ofd/...",
  "created_at": "2026-11-27T11:34:55"
}
```

| Maydon | Ma'nosi |
| --- | --- |
| `trans_id` | Atmos tranzaksiya ID — panelda «Tranzaksiya ID» deb shuni ko'rsating |
| `success_trans_id` | bankdagi muvaffaqiyatli tranzaksiya ID |
| `amount` | yechilgan summa, **tiyinda** (so'm × 100) |
| `confirmed` | Atmos tasdiqlaganmi |
| `ofd_url` | chek havolasi (buyurtmaning `ofd_url` i bilan bir xil) |
| `created_at` | yechilgan vaqt (Toshkent) |

Pul hali muzlatilgan bo'lsa (`payment_status = 1`), Atmos ID'si = buyurtmaning `hold_id` maydoni. Atmos ba'zan javobda bo'sh maydonlarni yubormaydi, shunda `trans_id` / `success_trans_id` `0` bo'lishi mumkin.

## 4. Loyiha — `project`

PRO mijozi buyurtma tovarlarini o'z loyihasiga bog'laydi (loyiha buyurtmaga emas, har bir tovar qatoriga bog'lanadi).

```json
"project": {"id": 12, "name": "Chilonzor uy", "status": "active"},
"items": [
  {"id": 501, "product": {...}, "quantity": 2, "unit_price": 1000.0, "ikpu_code": "...",
   "project": {"id": 12, "name": "Chilonzor uy", "status": "active"}}
]
```

- `project` = bog'langan birinchi tovar qatorining loyihasi; hech bir qator bog'lanmagan bo'lsa `null` («Loyiha» qatorida «—» yozing, «Backend kutilmoqda» olib tashlansin).
- Mijoz bitta buyurtma tovarlarini bir nechta loyihaga bo'lib bog'lashi mumkin (kam uchraydi) — aniq holat `items[].project` da.
- `status`: `active` / `archived` (loyiha arxivga olingan).
- Faqat o'qish uchun: bog'lashni mijoz ilovada qiladi.

## 5. To'lov tarixi — `comments`

To'lov holatining har o'zgarishi buyurtmaning `comments` ro'yxatiga **tizim izohi** (`is_system: true`) bo'lib yoziladi (`GET orders/<id>/` → `comments`, yoki `GET order-comments/?order=<id>&is_system=true`):

```json
{"id": 91, "author": null, "text": "To'lov holati: Muzlatilgan → To'langan (Atmos)", "is_system": true,
 "created_at": "2026-11-27T11:34:55"}
```

- Atmos o'zgarishlari: `author: null`, matn oxirida `(Atmos)`.
- Eski buyurtmada qo'lda o'zgartirilgan: `author` = o'zgartirgan admin, `(Atmos)` yo'q.
- Ro'yxat yangisi birinchi. Tarix shu deploydan boshlanadi, avvalgi o'zgarishlar yozilmagan.

## Frontda qilinadigan ishlar (BLD-551)

1. To'lov usuli yozuvini `payment_kind` dan chiqaring: `atmos` → «Onlayn · karta (Atmos)», `on_delivery` → «Qabulda · naqd / karta» (`payment_method` bo'yicha).
2. `payment_kind = atmos` da to'lov holati dropdown'ini olib tashlang — oddiy yozuv. `on_delivery` da dropdown qolishi mumkin.
3. To'lov blokiga «Tranzaksiya ID» = `atmos_transaction.trans_id` (yo'q bo'lsa va `hold_id` bo'lsa — `hold_id`, ikkalasi ham yo'q bo'lsa «—»), chek havolasi = `ofd_url`.
4. «Loyiha» qatori: `project.name` (+ ID), `null` bo'lsa «—». Vaqtinchalik «Backend kutilmoqda» yozuvini olib tashlang.
5. `ofd_url` ni formadan yubormang (yuborilsa ham e'tiborga olinmaydi).
6. To'lov tarixini izohlar ichida ko'rsating yoki `is_system` izohlarni alohida «Tarix» blokida chiqaring.
