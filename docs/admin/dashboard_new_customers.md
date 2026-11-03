# Har oy yangi foydalanuvchilar — admin panel uchun

Dashboard'dagi oyma-oy o'sish grafigi uchun: har oy ro'yxatdan o'tgan yangi foydalanuvchilar soni, mobil ilova va sayt bo'yicha bo'lingan.

Base URL: `{{host}}/api/v1/admin/`. Token: `Authorization: Bearer <admin access token>` (faqat admin; tokensiz → `401`).

| Metod | URL | Nima |
| --- | --- | --- |
| GET | `dashboard/new-customers/` | har oy yangi foydalanuvchilar: jami, ilova, sayt |

Swagger: `/swagger/admin/` → **dashboard**.

---

```
GET dashboard/new-customers/
GET dashboard/new-customers/?period=6_months
GET dashboard/new-customers/?period=all_time
```

| Parametr | Qiymatlar | Default | Izoh |
| --- | --- | --- | --- |
| `period` | `6_months` / `12_months` / `all_time` | `12_months` | oxirgi 6 / 12 kalendar oy (joriy oy ham kiradi, 1-sanadan bugungacha) / birinchi foydalanuvchi ro'yxatdan o'tgan oydan joriy oygacha |

Boshqa qiymat → `400`.

```json
{
  "period": "12_months",
  "date_from": "2025-12-01",
  "date_to": "2026-11-20",
  "total": 7,
  "app": 4,
  "site": 3,
  "months": [
    {"month": "2025-12-01", "total": 0, "app": 0, "site": 0},
    "...",
    {"month": "2026-10-01", "total": 1, "app": 0, "site": 1},
    {"month": "2026-11-01", "total": 5, "app": 3, "site": 2}
  ]
}
```

| Maydon | Izoh |
| --- | --- |
| `period` | qaysi davr hisoblandi |
| `date_from` | birinchi oyning 1-sanasi; `all_time` da — birinchi foydalanuvchi oyining 1-sanasi (hech kim bo'lmasa joriy oy) |
| `date_to` | bugun |
| `total`, `app`, `site` | butun davr bo'yicha yig'indi; `total = app + site` |
| `months` | **har bir oy**, eskisidan yangisiga; foydalanuvchi bo'lmagan oy `0` (bu haqiqiy qiymat, "ma'lumot yo'q" emas) |
| `month` | oyning 1-sanasi (`YYYY-MM-DD`); oy nomini panel o'zi qo'yadi |

### Qoidalar

- **Ro'yxatdan o'tgan** = OTP'ni tasdiqlagan foydalanuvchi (`verified = true`). Telefon raqam kiritib, kodni tasdiqlamaganlar kirmaydi. Oy — akkaunt yaratilgan sana (`created_at`, Toshkent vaqti); kod odatda shu daqiqalarda tasdiqlanadi.
- **O'chirilgan** akkauntlar kirmaydi (foydalanuvchilar ro'yxatidagidek).
- **Ilova / sayt** — foydalanuvchi qayerda ro'yxatdan o'tgani (`registration_channel`): `ios` / `android` → ilova, `site` → sayt. Kanal noma'lum bo'lsa (kanal saqlanishidan oldingi eski akkauntlar, `platform` yubormaydigan eski ilova versiyalari) — dashboard'dagi `registrations` blokidagi qoida: push token'i (ilova qurilmasi) bor → ilova, yo'q → sayt.
- Test / xodim akkauntlari: foydalanuvchida bunday belgi yo'q; xodimlar alohida (`staff/`), ular bu songa kirmaydi.

**Ro'yxat bilan mosligi:** oydagi `total` = `customers/?from_created=<oy 1-sanasi>&to_created=<oy oxirgi kuni>&verified=true` ning `count`. Kanal bo'yicha filtr (`registration_channel=`) faqat kanali ma'lum bo'lganlarni ko'rsatadi, shuning uchun `app` / `site` eski akkauntlar sababli undan ko'p bo'lishi mumkin.

> Dashboard'ning asosiy `dashboard/` dagi `registrations` bloki (kunlar bo'yicha) o'zgarmadi: u hamma akkauntlarni (tasdiqlanmagan va o'chirilganlarni ham) sanaydi va ilova / saytni faqat push token bo'yicha ajratadi, shuning uchun sonlar farq qilishi mumkin.
