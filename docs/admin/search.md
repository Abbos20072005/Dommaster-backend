# Qidiruv: sinonimlar, natijasiz so'rovlar, arizalar — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET / POST search/synonyms/` | sinonimlar lug'ati (ro'yxat / yaratish) |
| `GET / PATCH / PUT / DELETE search/synonyms/{id}/` | bitta sinonim guruhi |
| `GET search/not-found/` | hech narsa topilmagan qidiruvlar (so'rov bo'yicha guruhlangan) |
| `GET search/not-found/export/` | xuddi shu ro'yxat XLSX faylda |
| `GET search/requests/` | "Не нашли — оставьте заявку" arizalari |
| `GET / PATCH / DELETE search/requests/{id}/` | bitta ariza (menejer statusni / izohni o'zgartiradi) |
| `GET search/requests/stats/` | arizalar soni statuslar bo'yicha |

Swagger: `/swagger/admin/` → **search**.

## Qidiruv qanday ishlaydi (kontekst)

Sayt / ilovadagi katalog qidiruvi (`product/filter/` `q`, `search/` takliflar) endi:

- **lotin ↔ kirill**: "podshipnik 6203" va "подшипник 6203" bir xil natija beradi;
- **so'z tartibi, tire, katta-kichik harf ahamiyatsiz**: "6203 2rs", "6203-2RS", "2rs 6203" — bir xil;
- **o'xshash harflar**: kirill "М6х20" = lotin "M6x20"; "3×2,5" = "3x2.5";
- **xatolarga chidamli**: 4+ harfli so'zdagi kichik xato ("подшипнек", "perforatr") ham topiladi; raqamlar va qisqa kodlar ("6203", "m6") faqat aniq;
- nom (uz / ru), brend nomi va **artikul** bo'yicha qidiradi;
- **sinonimlar** — quyidagi lug'atdan.

---

## 1. Sinonimlar — `search/synonyms/`

Bitta guruh = bir-biriga teng atamalar. So'rovda ulardan biri bo'lsa (alohida so'z(lar) sifatida), qolganlari ham qidiriladi: "подшипник 180203" → "подшипник 6203 2rs" ham qidiriladi.

```json
{
  "id": 4,
  "terms": ["6203 2RS", "6203-2RS", "180203"],
  "is_active": true,
  "created_at": "2026-11-11T16:04:30.146000",
  "updated_at": "2026-11-11T16:04:30.146000"
}
```

| Maydon | Izoh |
| --- | --- |
| `terms` * | atamalar ro'yxati, kamida 2 ta har xil, ko'pi bilan 20 ta, har biri 100 belgigacha. Katta-kichik harf, bo'sh joy va tire farq qilmaydi — "6203-2rs" va "6203 2RS" bitta atama hisoblanadi, takrori saqlanmaydi (birinchisi qoladi) |
| `is_active` | default `true`; `false` = guruh qidiruvda ishlatilmaydi |

Faqat o'qiladi: `id`, `created_at`, `updated_at`.

Yaratish (`POST search/synonyms/` → `201`):

```json
{ "terms": ["6203 2RS", "6203-2RS", "180203"] }
```

O'zgartirish: `PATCH search/synonyms/{id}/` (`terms` yuborilsa — butun ro'yxat almashadi). O'chirish: `DELETE` → `204`. O'zgarish qidiruvga darhol ta'sir qiladi.

Xato (`400`): `{"terms": ["At least two different terms."]}`, `{"terms": ["A term must not be empty."]}`.

Ro'yxat: paginatsiya (`?page=&page_size=`, default 20, max 100; javob `count, next, previous, next_page, previous_page, results`), filter `is_active`, `?search=` (atamalar ichidan), `?ordering=` `id` / `created_at` / `updated_at` (default `-id`).

> Maslahat: `search/not-found/` dagi so'rovlarni ko'rib, mahsulot boshqa nom / kod bilan bor bo'lsa — shu yerga sinonim qo'shing.

---

## 2. Natijasiz so'rovlar — `search/not-found/`

Sayt / ilovada qidiruv hech narsa topmagan har safar yoziladi: faqat `q` bilan, **boshqa filtrsiz** (kategoriya, narx, brend filtri bo'lsa — sababi filtr bo'lishi mumkin, yozilmaydi), birinchi sahifa. Harfma-harf yozilgan so'rov (bir qurilma, 30 s ichida "gidroizol" → "gidroizolyatsiya") bitta qator bo'lib qoladi. AI yordamchi qidiruvlari yozilmaydi.

Javob — bitta qator = bitta so'rov (kichik harf, so'zlar bitta bo'sh joy bilan):

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "next_page": null,
  "previous_page": null,
  "results": [
    {
      "query": "gidroizolyatsiya",
      "searches": 3,
      "viewers": 2,
      "languages": ["ru", "uz"],
      "first_searched_at": "2026-11-09T10:12:00",
      "last_searched_at": "2026-11-11T15:40:00"
    }
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `query` | so'rov (normallashtirilgan) |
| `searches` | davrda necha marta qidirilgan |
| `viewers` | nechta har xil mijoz / qurilma qidirgan (identifikatorsiz mehmonlar hisoblanmaydi) |
| `languages` | qaysi tillarda (`uz` / `ru`) |
| `first_searched_at`, `last_searched_at` | davr ichidagi birinchi / oxirgi qidiruv |

Query parametrlar:

| Parametr | Izoh |
| --- | --- |
| `days` | oxirgi N kun, bugun bilan (default 30, 1–365) |
| `date_from` + `date_to` | `days` o'rniga aniq davr (`YYYY-MM-DD`, ikkalasi birga) |
| `language` | `uz` / `ru` |
| `platform` | `site` / `ios` / `android` (klient yubormagan qidiruvlar faqat filtrsiz ro'yxatda) |
| `search` | so'rov matni ichidan qidirish |
| `ordering` | `searches`, `viewers`, `first_searched_at`, `last_searched_at`, `normalized` (= so'rov matni bo'yicha alifbo); default `-searches,-last_searched_at,normalized` |

Eksport: `GET search/not-found/export/` — xuddi shu filtrlar / tartib, paginatsiyasiz, XLSX (`search_not_found_YYYYMMDD_HHMM.xlsx`); `export_language=ru|uz` (default `ru`) — ustun sarlavhalari tili.

Xato: `400` — `{"date_to": ["date_from and date_to are sent together."]}` va h.k.

---

## 3. Arizalar — `search/requests/`

Mijoz qidiruvda topmagan tovar uchun qoldirgan ariza ("Не нашли — оставьте заявку"). Yangi ariza darhol **xodimlar Telegram guruhiga** (umumiy topic) ham yuboriladi: nima qidirgani, telefon, kompaniya, mijoz (bo'lsa), vaqt, til.

```json
{
  "id": 12,
  "query": "Подшипник 180203",
  "phone_number": "+998901234567",
  "company": "Stroy LLC",
  "customer": { "id": 5, "full_name": "Ali Valiyev", "phone_number": "+998901112233" },
  "language": "ru",
  "platform": "site",
  "status": "new",
  "manager_comment": "",
  "created_at": "2026-11-11T16:04:32",
  "updated_at": "2026-11-11T16:04:32"
}
```

| Maydon | Izoh |
| --- | --- |
| `query`, `phone_number`, `company` | mijoz yozgani (faqat o'qiladi). Telefon to'liq ko'rinadi — menejer qo'ng'iroq qiladi |
| `customer` | ilovaga / saytga kirgan mijoz bo'lsa, aks holda `null` (faqat o'qiladi) |
| `language`, `platform` | so'rov tili, `site` / `ios` / `android` / `""` (faqat o'qiladi) |
| `status` | `new` (yangi) / `in_progress` (ishda) / `done` (bajarildi) / `rejected` (rad etildi); default `new` |
| `manager_comment` | menejer izohi, ixtiyoriy |

O'zgartirish: `PATCH search/requests/{id}/` — faqat `status` va `manager_comment` (boshqa maydonlar e'tiborsiz qoldiriladi):

```json
{ "status": "done", "manager_comment": "Qo'ng'iroq qilindi, buyurtma berildi" }
```

`DELETE search/requests/{id}/` → `204`. `POST` yo'q (arizani faqat mijoz yaratadi).

Ro'yxat: paginatsiya, filterlar `status`, `language`, `platform`, `customer` (id), `has_customer` (`true`/`false`), `from_created` / `to_created` (`YYYY-MM-DD`); `?search=` — `query`, `phone_number`, `company`; `?ordering=` `id` / `status` / `created_at` / `updated_at` (default `-id`).

`GET search/requests/stats/`:

```json
{ "total": 14, "new": 5, "in_progress": 2, "done": 6, "rejected": 1 }
```
