# Menejerlar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET managers/` | menejerlar ro'yxati (paginatsiyali) |
| `POST managers/` | menejer yaratish (JSON) |
| `GET / PATCH / PUT / DELETE managers/{id}/` | bitta menejer |

Swagger: `/swagger/admin/` → **managers**.

> Menejer — buyurtmaga biriktiriladigan xodimlar ro'yxati (buyurtma sahifasidagi "Menejer" dropdown'i). Admin akkaunti (login) bilan **bog'lanmagan**: menejer tizimga kira olmaydi, parol / telefon / rol maydonlari yo'q. Buyurtmaga biriktirish va ichki izohlar — [order_manager_comments.md](order_manager_comments.md).

---

## Obyekt

```json
{
  "id": 1,
  "full_name": "M. Xolmatova",
  "monthly_plan": "50000000.00",
  "is_active": true,
  "created_at": "2026-10-02T09:41:45.688434",
  "updated_at": "2026-10-02T09:41:45.688434"
}
```

| Maydon | Izoh |
| --- | --- |
| `full_name` * | F.I.Sh., majburiy, 255 belgigacha; unikal emas — bir xil ism ikki marta kiritilishi mumkin |
| `monthly_plan` | oylik savdo rejasi, so'mda (yakunlangan buyurtmalar tushumi bo'yicha). **String** (decimal) qaytadi, son yoki string qabul qiladi; default `"0.00"` = reja yo'q; `>= 0`. Dashboard'dagi "Menejerlar rejasi" vidjeti shundan hisoblanadi — [dashboard.md](dashboard.md) |
| `is_active` | default `true`; `false` = ishlamayapti (dropdown'da ko'rsatilmaydi) |

Faqat o'qiladi: `id`, `created_at`, `updated_at`.

Yaratish (`POST managers/` → `201` + obyekt):

```json
{ "full_name": "M. Xolmatova", "monthly_plan": 50000000 }
```

O'zgartirish (`PATCH managers/{id}/` — faqat kerakli maydon → `200` + obyekt):

```json
{ "is_active": false }
```

O'chirish: `DELETE managers/{id}/` → `204`, body yo'q.

> Menejer o'chirilsa, unga biriktirilgan buyurtmalar "Biriktirilmagan" (`manager: null`) holatiga o'tadi va bu haqda buyurtmaga tizim izohi **yozilmaydi**. Ishdan ketgan menejerni o'chirish o'rniga `is_active: false` qilish tavsiya etiladi — eski buyurtmalarda ismi saqlanib qoladi.

---

## Ro'yxat

`GET managers/?page=&page_size=` (default 20, max 100)

```json
{
  "count": 6,
  "next": null,
  "previous": null,
  "next_page": null,
  "previous_page": null,
  "results": [
    { "id": 1, "full_name": "M. Xolmatova", "monthly_plan": "50000000.00", "is_active": true, "created_at": "...", "updated_at": "..." }
  ]
}
```

- Qidiruv: `?search=` (`full_name`)
- Filtr: `is_active` (`true` / `false`)
- Tartib: `?ordering=` `id`, `full_name`, `monthly_plan`, `created_at` (teskari: `-created_at`); default — alifbo bo'yicha (`full_name`)

Dropdown uchun: `GET managers/?is_active=true&page_size=100`.

---

## Buyurtmalar bilan bog'liqligi

| Nima | Qayerda |
| --- | --- |
| Buyurtmaga biriktirish / olib tashlash | `PATCH orders/{id}/` — `{"manager": 1}` yoki `{"manager": {"id": 1}}`, olib tashlash `{"manager": null}` |
| Menejerning buyurtmalari | `GET orders/?manager={id}` |
| Menejerning buyurtmalar soni / tushumi | `GET orders/stats/?manager={id}` |
| Biriktirilmagan buyurtmalar | `GET orders/?has_manager=false` |

Buyurtma javoblarida menejer qisqa ko'rinishda keladi: `"manager": {"id": 1, "full_name": "M. Xolmatova", "is_active": true}` yoki `null`.

---

## Xatolar

Oddiy DRF formatida (klient API'dagi `{"ok", "error_code"}` o'rami yo'q). Xabar matnlari tilga bog'liq (default — ruscha), shuning uchun matnga emas, HTTP status va maydon nomiga tayaning.

| Holat | HTTP | Body |
| --- | --- | --- |
| Token yo'q yoki yaroqsiz | 401 | `{"detail": "..."}` |
| `full_name` yuborilmadi | 400 | `{"full_name": ["Обязательное поле."]}` |
| `full_name` bo'sh yoki 255 belgidan uzun | 400 | `{"full_name": ["..."]}` |
| `monthly_plan` manfiy yoki son emas | 400 | `{"monthly_plan": ["..."]}` |
| Mavjud bo'lmagan `id` | 404 | `{"detail": "..."}` |

---

## Eslatmalar

- Menejer obyektida buyurtmalar soni (`orders_count`) **yo'q** — kerak bo'lsa `orders/stats/?manager={id}` dan olinadi.
- Faol bo'lmagan (`is_active: false`) menejerni ham buyurtmaga biriktirish mumkin — backend cheklamaydi. Dropdown'da `?is_active=true` bilan filtrlang; buyurtmada allaqachon turgan nofaol menejerni buyurtma javobidagi `manager` obyektidan ko'rsating.
- Menejerlar faqat admin API'da — mijoz (sayt / ilova) API'larida bu ma'lumot umuman yo'q.
