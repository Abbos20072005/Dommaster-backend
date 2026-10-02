# Buyurtma menejeri va ichki izohlar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

Buyurtma sahifasidagi ikkita blok uchun:

- **Menejer** — buyurtmaga menejer biriktirish (dropdown, "Biriktirilmagan" = `null`).
- **Ichki izoh** — buyurtma bo'yicha xodimlar yozadigan izohlar. Mijozga ko'rinmaydi: mobil/web klient API'sida bu ma'lumotlar umuman yo'q.

| Endpoint | Nima uchun |
| --- | --- |
| `GET managers/` | dropdown uchun menejerlar ro'yxati |
| `POST / PATCH / DELETE managers/{id}/` | menejerlarni boshqarish (CRUD) |
| `PATCH orders/{id}/` | buyurtmaga menejer biriktirish / olib tashlash |
| `GET orders/{id}/` | buyurtma detali — `manager` va `comments` shu yerda keladi |
| `POST order-comments/` | izoh qo'shish |
| `GET order-comments/?order={id}` | izohlar ro'yxati (pagination bilan) |

Swagger: `/swagger/admin/` → **managers**, **orders**, **order-comments**.

---

## 1. Menejerlar

### Obyekt

```json
{
  "id": 1,
  "full_name": "M. Xolmatova",
  "is_active": true,
  "created_at": "2026-10-02T09:41:45.688434",
  "updated_at": "2026-10-02T09:41:45.688434"
}
```

| Maydon | Turi | Izoh |
| --- | --- | --- |
| `full_name` | string, majburiy | maks. 255 belgi |
| `is_active` | bool | default `true` |

### Ro'yxat — `GET managers/`

| Query | Misol | Izoh |
| --- | --- | --- |
| `is_active` | `?is_active=true` | dropdown uchun faqat faollarni olish |
| `search` | `?search=Xol` | `full_name` bo'yicha qidiruv |
| `ordering` | `?ordering=-created_at` | `id`, `full_name`, `created_at`; default `full_name` |
| `page`, `page_size` | `?page=1&page_size=100` | default 20, maksimum 100 |

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "next_page": null,
  "previous_page": null,
  "results": [
    { "id": 1, "full_name": "M. Xolmatova", "is_active": true, "created_at": "...", "updated_at": "..." }
  ]
}
```

### Yaratish / o'zgartirish / o'chirish

```bash
curl -X POST {{host}}/api/v1/admin/managers/ \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "M. Xolmatova"}'
```

| Amal | So'rov | Javob |
| --- | --- | --- |
| Yaratish | `POST managers/` | `201` + obyekt |
| Bitta menejer | `GET managers/{id}/` | `200` + obyekt |
| O'zgartirish | `PATCH managers/{id}/` (`{"is_active": false}`) | `200` + obyekt |
| O'chirish | `DELETE managers/{id}/` | `204`, body yo'q |

> Menejer o'chirilsa, unga biriktirilgan buyurtmalar "Biriktirilmagan" holatiga o'tadi va bu haqda tizim izohi **yozilmaydi**. Ishdan ketgan menejerni o'chirish o'rniga `is_active: false` qilish tavsiya etiladi — eski buyurtmalarda ismi saqlanib qoladi.

---

## 2. Buyurtmaga menejer biriktirish

Alohida endpoint yo'q — buyurtmani yangilash API'si orqali:

```
PATCH orders/{id}/
```

| Amal | Body |
| --- | --- |
| Biriktirish / almashtirish | `{"manager": {"id": 1}}` yoki `{"manager": 1}` |
| Olib tashlash ("Biriktirilmagan") | `{"manager": null}` |
| Menejerga tegmaslik | `manager` maydonini yubormaslik |

```bash
curl -X PATCH {{host}}/api/v1/admin/orders/14/ \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"manager": {"id": 1}}'
```

Javob — `200 OK` + to'liq buyurtma obyekti (detal bilan bir xil). Kerakli qismi:

```json
{
  "id": 14,
  "manager": { "id": 1, "full_name": "M. Xolmatova", "is_active": true },
  "comments": [
    {
      "id": 4,
      "author": null,
      "text": "Menejer o'zgartirildi: M. Xolmatova",
      "is_system": true,
      "created_at": "2026-10-02T09:54:59.193707"
    }
  ]
}
```

- Menejer haqiqatan o'zgarganda backend avtomatik **tizim izohi** yozadi: `Menejer o'zgartirildi: <ism>`, olib tashlanganda — `Menejer olib tashlandi`. Yangi izoh shu `PATCH` javobining `comments` ichida darhol keladi — qayta so'rov shart emas.
- Avvalgi menejerning o'zi qayta yuborilsa, izoh yozilmaydi.
- Menejer biriktirilmagan buyurtmada `manager` = `null`.
- Buyurtma yaratishda (`POST orders/`) ham `manager` yuborish mumkin (ixtiyoriy); bunda tizim izohi yozilmaydi.

### Buyurtmalar ro'yxatida

`GET orders/` har bir elementda `manager` obyektini (yoki `null`) qaytaradi. `comments` ro'yxatda **yo'q** — faqat detalda.

| Query | Izoh |
| --- | --- |
| `?manager=1` | shu menejerning buyurtmalari |
| `?has_manager=false` | biriktirilmagan buyurtmalar |
| `?has_manager=true` | menejeri bor buyurtmalar |

Shu filtrlar `GET orders/stats/` da ham ishlaydi.

---

## 3. Ichki izohlar

### Izoh obyekti

Buyurtma detalidagi (`GET orders/{id}/`) `comments` massivi — yangisi tepada, pagination'siz:

```json
"comments": [
  {
    "id": 5,
    "author": { "id": 3, "username": "xolmatova", "first_name": "Madina", "last_name": "Xolmatova" },
    "text": "Mijoz qo'ng'iroq qildi, ertalabki oraliqda yetkazishni so'radi.",
    "is_system": false,
    "created_at": "2026-10-02T09:54:59.282632"
  },
  {
    "id": 4,
    "author": null,
    "text": "Menejer o'zgartirildi: M. Xolmatova",
    "is_system": true,
    "created_at": "2026-10-02T09:54:59.193707"
  }
]
```

| Maydon | Izoh |
| --- | --- |
| `author` | izoh yozgan admin (login qilgan foydalanuvchi). Tizim izohlarida `null` |
| `is_system` | `true` — backend o'zi yozgan izoh, UI'da muallif sifatida "Tizim" ko'rsatiladi |
| `text` | izoh matni |
| `created_at` | server vaqti (Asia/Tashkent), timezone qo'shimchasisiz |

> Muallif ismi uchun `first_name` + `last_name` dan foydalaning; ikkalasi ham bo'sh bo'lishi mumkin — unda `username` ni ko'rsating. "Tizim"ni aniqlashda `is_system` ga tayaning, `author == null` ga emas (admin akkaunti o'chirilsa, uning izohlarida ham `author` `null` bo'lib qoladi).

### Izoh qo'shish — `POST order-comments/`

```bash
curl -X POST {{host}}/api/v1/admin/order-comments/ \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"order": 14, "text": "Mijoz qo'\''ng'\''iroq qildi"}'
```

| Maydon | Turi | Izoh |
| --- | --- | --- |
| `order` | majburiy | `14` yoki `{"id": 14}` |
| `text` | string, majburiy | bo'sh bo'lmasligi kerak |

`author` va `is_system` yuborilmaydi — muallif tokendan olinadi, `is_system` har doim `false`.

Javob — `201 Created`:

```json
{
  "id": 5,
  "order": { "id": 14 },
  "author": { "id": 3, "username": "xolmatova", "first_name": "Madina", "last_name": "Xolmatova" },
  "text": "Mijoz qo'ng'iroq qildi",
  "is_system": false,
  "created_at": "2026-10-02T09:54:59.282632"
}
```

Qo'shilgandan keyin javobdagi obyektni ro'yxat boshiga qo'shish kifoya (maydonlari detaldagi izoh bilan bir xil, faqat `order` ortiqcha).

### Izohlar ro'yxati — `GET order-comments/`

Detaldagi `comments` yetarli bo'lsa, bu endpoint kerak emas. Izohlar ko'p bo'lsa yoki alohida yangilash kerak bo'lsa ishlatiladi.

| Query | Misol | Izoh |
| --- | --- | --- |
| `order` | `?order=14` | bitta buyurtmaning izohlari |
| `is_system` | `?is_system=false` | faqat xodimlar yozgan izohlar |
| `search` | `?search=qo'ng'iroq` | matn bo'yicha qidiruv |
| `ordering` | `?ordering=created_at` | `id`, `created_at`; default `-created_at` (yangisi tepada) |
| `page`, `page_size` | | default 20, maksimum 100 |

Javob — standart admin pagination (`count, next, previous, next_page, previous_page, results`), `results` ichida yuqoridagi `POST` javobidagi kabi obyektlar.

> Izohni **tahrirlash va o'chirish yo'q** — `PATCH` / `PUT` / `DELETE` → `405`. Xato yozilgan izoh ustidan yangi izoh yoziladi.

---

## Xatolar

Admin API'da xatolar oddiy DRF formatida (klient API'dagi `{"ok", "error_code"}` o'rami yo'q). Xabar matnlari tilga bog'liq (default — ruscha), shuning uchun matnga emas, HTTP status va maydon nomiga tayaning.

| Holat | HTTP | Body |
| --- | --- | --- |
| Token yo'q yoki yaroqsiz | 401 | `{"detail": "..."}` |
| Mavjud bo'lmagan menejer biriktirildi | 400 | `{"manager": {"id": "Object with id=999999 does not exist."}}` |
| Izoh matni bo'sh | 400 | `{"text": ["Это поле не может быть пустым."]}` |
| `order` yuborilmadi | 400 | `{"order": ["Обязательное поле."]}` |
| Mavjud bo'lmagan buyurtmaga izoh | 400 | `{"order": {"id": "Object with id=999999 does not exist."}}` |
| `full_name` siz menejer yaratish | 400 | `{"full_name": ["Обязательное поле."]}` |
| Mavjud bo'lmagan `id` | 404 | `{"detail": "..."}` |
| Izohni o'zgartirish / o'chirish | 405 | `{"detail": "..."}` |

---

## Eslatmalar

- Hozircha tizim izohi faqat **menejer o'zgarganda** yoziladi. Maketdagi "1C xatosi: ..." kabi izohlar hali yozilmaydi (1C'ga buyurtma yuborish hozircha yo'q) — qo'shilganda xuddi shu formatda (`is_system: true`, `author: null`) keladi, frontendda o'zgartirish kerak bo'lmaydi.
- Menejer admin akkaunti (login) bilan bog'lanmagan: `managers` — alohida ro'yxat, izoh muallifi esa login qilgan admin. Ya'ni izoh muallifining ismi admin akkauntidagi `first_name` / `last_name` dan olinadi, menejer `full_name` idan emas.
- Faol bo'lmagan (`is_active: false`) menejerni ham buyurtmaga biriktirish mumkin — backend cheklamaydi. Dropdown'da `?is_active=true` bilan filtrlang; buyurtmada allaqachon turgan nofaol menejerni `orders/{id}/` javobidagi `manager` obyektidan ko'rsating.
