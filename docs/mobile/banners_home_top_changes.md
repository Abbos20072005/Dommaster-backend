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
| `GET main/` | — | o'zgarmagan (`home_bottom` bannerlar) |

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

To'liq hujjat: `docs/mobile/banners.md`.
