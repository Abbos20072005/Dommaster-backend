# Bannerlar: yuqori slayder bitta joylashuv — mobile / sayt uchun o'zgarishlar

Base URL: `{{host}}/api/v1/`

Bosh sahifa yuqorisidagi slayder uchun ikkita joylashuv bor edi: `site_home` (sayt) va `app_home` (ilova). Endi ular **bitta**: **`home_top`**. Sayt va ilova bitta ro'yxatdan oladi; qaysi banner qaysi platformada chiqishini `platform` parametri ajratadi.

## Nima o'zgardi

| Joy | Oldin | Hozir |
| --- | --- | --- |
| `GET base/banner/?placement=` | `site_home`, `app_home`, `home_bottom`, `catalog` | `home_top`, `home_bottom`, `catalog` |
| `GET base/banner/` (parametrsiz) | `site_home` + `app_home` bannerlari | `home_top` bannerlari — **o'sha ro'yxat, o'sha tartib** |
| Banner obyekti → `placement` | `site_home` yoki `app_home` | `home_top` |
| `GET home/` → `slider` blokidagi bannerlar → `placement` | `site_home` yoki `app_home` | `home_top` |
| `GET main/` | pastki bannerlar har reklama blokidan keyin bittadan: `{"type": "banner", "data": {...}}` | har reklama blokidan keyin ro'yxat: `{"type": "banners", "data": [...]}` — pastga qarang |

Banner obyektining qolgan maydonlari (`link_type`, `link`, `page`, `content_type_info`, rasmlar) o'zgarmagan.

## Eski versiya buziladimi

Yo'q:

- Parametrsiz `base/banner/` avvalgidek yuqori slayder bannerlarini qaytaradi.
- `?placement=site_home` va `?placement=app_home` **qabul qilinadi** — ikkalasi ham `home_top` degani. Lekin endi ikkalasi **bir xil ro'yxatni** qaytaradi, shuning uchun `platform` yuborilmasa boshqa platforma uchun kiritilgan banner ham kelishi mumkin.
- Javobdagi `placement` qiymati `home_top` keladi. Ilovada `placement == "app_home"` kabi shart bo'lsa — olib tashlang.

## Yangi versiyada qilish kerak

```
GET base/banner/?placement=home_top&platform=ios        → ilova (iOS)
GET base/banner/?placement=home_top&platform=android    → ilova (Android)
GET base/banner/?placement=home_top&platform=site       → sayt
```

1. `placement=app_home` / `site_home` o'rniga `placement=home_top` yuborish.
2. **`platform` ni har doim yuborish** — endi sayt va ilova bannerlarini faqat shu ajratadi.
3. `placement` qiymatiga bog'liq shartlar bo'lsa, `home_top` ga moslash.

## `GET main/` — pastki bannerlar ro'yxat bo'lib keladi

```json
[
  { "type": "addsbrands", "data": { ... } },
  { "type": "banners",    "data": [ { "id": 17, ... }, { "id": 18, ... } ] },
  { "type": "addsbrands", "data": { ... } },
  { "type": "banners",    "data": [ { "id": 19, ... } ] }
]
```

- Har bir reklama blokidan **keyin** bitta `type: "banners"` elementi keladi: `data` **ro'yxat**. Pastki (`home_bottom`) bannerlar bloklar orasida **teng bo'linadi**, admin paneldagi tartibda; qoldiq birinchi ro'yxatlarga tushadi.
- Misol: 2 ta blok — 5 ta banner → `[1, 2, 3]` va `[4, 5]`; 3 ta banner → `[1, 2]` va `[3]`; 1 ta banner → faqat birinchi blokdan keyin `[1]`.
- Banner bloklardan kam bo'lsa, oxirgi bloklardan keyin element **kelmaydi** (bo'sh ro'yxat yuborilmaydi). Hech bir banner tushib qolmaydi.
- Ro'yxatdagi har bir element — `base/banner/` dagi banner obyekti.
- Eski `type: "banner"` (`data` — bitta obyekt) endi **kelmaydi**. Eski ilova versiyasida pastki bannerlar ko'rinmaydi (u `banners` turini bilmaydi) — noma'lum `type` da yiqilmasligini eski versiyada bir tekshirib ko'ring.
- `main/` da `platform` yo'q: platforma bo'yicha aniq ro'yxat kerak bo'lsa — `base/banner/?placement=home_bottom&platform=...` (xuddi shu ro'yxat, kanal bo'yicha filtrlangan).

To'liq hujjat: `docs/mobile/banners.md`.
