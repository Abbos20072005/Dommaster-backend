# Qidiruv va "Не нашли — оставьте заявку" — mobile / sayt uchun

| Endpoint | Nima uchun | O'zgarish |
| --- | --- | --- |
| `POST /api/v1/product/filter/` (`q`) | katalog qidiruvi | kontrakt o'sha; qidiruv aqlliroq + yangi ixtiyoriy `platform` |
| `GET /api/v1/search/?q=` | qidiruv takliflari (mahsulot nomlari, kategoriyalar, brendlar) | kontrakt o'sha; mahsulot nomlari yangi qidiruvdan |
| `POST /api/v1/search/requests/` | **yangi**: topilmagan tovar uchun ariza | yangi |

Eski ilova / sayt hech narsa o'zgartirmasa ham buzilmaydi — qidiruv shunchaki ko'proq topadi.

## 1. Qidiruv nimani topadi

Backendda, frontda hech narsa qilish shart emas:

- lotin ↔ kirill: "podshipnik 6203" = "подшипник 6203", "kabel" = "кабель";
- so'z tartibi, tire, katta-kichik harf: "6203 2rs" = "6203-2RS" = "2RS 6203";
- o'xshash harflar va o'lchamlar: "М6" (kirill) = "M6" (lotin), "3х2,5" = "3x2.5" = "3×2,5";
- kichik xatolar 4+ harfli so'zlarda ("подшипнек", "perforatr"); raqamlar va kodlar ("6203", "M6") faqat aniq;
- nom (uz / ru), brend va artikul bo'yicha; admin panelda kiritilgan sinonimlar ("180203" = "6203-2RS").

Natijalar tartibi: so'rovning hamma so'zlari aniq topilganlar birinchi, keyin xato bilan topilganlar.

## 2. `product/filter/` — yangi `platform`

Body'ga ixtiyoriy `platform` qo'shing: `"site"` / `"ios"` / `"android"`. Qidiruv hech narsa topmasa, so'rov admin panelga (natijasiz so'rovlar ro'yxati) shu platforma bilan yoziladi.

```json
{ "q": "podshipnik 6203", "page": 1, "page_size": 20, "platform": "ios" }
```

Yoziladi faqat: `q` bor, **boshqa filtr yo'q** (kategoriya, brend, narx, `filters`, `sale_id`), `page=1`, natija 0. Mehmon `X-Device-Id` header yuborsa, harfma-harf yozilgan so'rov bitta qator bo'lib qoladi.

## 3. "Не нашли — оставьте заявку" — `POST /api/v1/search/requests/`

Qachon ko'rsatish: `product/filter/` `q` bilan `totalElements: 0` qaytarganda (yoki natijalar ostida "kerakli tovar yo'qmi?" tugmasi). Token ixtiyoriy — mijoz kirgan bo'lsa `Authorization: Bearer <token>` yuboring, ariza unga bog'lanadi.

So'rov:

```json
{
  "query": "Подшипник 180203",
  "phone_number": "+998 90 123-45-67",
  "company": "Stroy LLC",
  "platform": "site"
}
```

| Maydon | Izoh |
| --- | --- |
| `query` * | nima qidirildi: qidiruv matni (oldindan to'ldiring) yoki mijoz yozgani, 500 belgigacha, bo'sh bo'lmasin |
| `phone_number` * | O'zbekiston raqami `998XXXXXXXXX` (12 raqam; `+`, bo'sh joy, `-`, qavslar mumkin) — `+998XXXXXXXXX` ko'rinishida saqlanadi. Kirgan mijoz uchun uning raqamini oldindan qo'ying |
| `company` | kompaniya nomi, ixtiyoriy, 255 belgigacha |
| `platform` | `site` / `ios` / `android`, ixtiyoriy |

Javob (`200`):

```json
{
  "result": {
    "id": 12,
    "query": "Подшипник 180203",
    "phone_number": "+998901234567",
    "company": "Stroy LLC",
    "created_at": "2026-11-11T16:04:32"
  },
  "ok": true
}
```

Ariza menejerlarga darhol yetib boradi (xodimlar Telegram guruhi + admin panel). Javobdan keyin "Arizangiz qabul qilindi, menejer siz bilan bog'lanadi" kabi xabar ko'rsating.

Xatolar (`{"detail", "ok": false, "result": "", "error_code"}`):

| Status | `error_code` | Qachon |
| --- | --- | --- |
| `400` | `5` (validation) | `detail` = maydon → xato: `query` bo'sh, `phone_number` noto'g'ri format |
| `429` | `45` | bitta IP'dan 1 soatda 5 tadan ortiq ariza |

Til: `Accept-Language` (`uz` / `ru`) — ariza shu til bilan saqlanadi (menejer qaysi tilda gaplashishni biladi).

## Frontda qilinadigan ishlar

1. `product/filter/` body'ga `platform` qo'shing (`site` / `ios` / `android`).
2. Mehmonlar uchun `X-Device-Id` header'ini (ilova allaqachon yuboradi) qidiruvda ham yuboring.
3. Qidiruv 0 natija qaytarsa — "Не нашли — оставьте заявку" blokini ko'rsating: `query` (qidiruv matni bilan to'ldirilgan, tahrirlanadi), telefon (kirgan mijozniki oldindan), kompaniya (ixtiyoriy) → `POST search/requests/`.
4. `429` (`error_code` 45) bo'lsa — "Keyinroq urinib ko'ring" xabari.
