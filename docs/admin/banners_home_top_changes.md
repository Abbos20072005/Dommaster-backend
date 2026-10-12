# Bannerlar: yuqori slayder bitta joylashuv — admin panel uchun o'zgarishlar

Base URL: `{{host}}/api/v1/admin/`

Bosh sahifa yuqorisidagi slayder uchun ikkita joylashuv bor edi: `site_home` (Sayt · bosh slayder) va `app_home` (Ilova · bosh ekran). Endi ular **bitta**: **`home_top` — Bosh sahifa · yuqori slayder**.

Banner saytda yoki ilovada chiqishini endi faqat kanallar belgilaydi: `show_on_site`, `show_on_ios`, `show_on_android`.

## Nima o'zgardi

| Endpoint | Oldin | Hozir | Eski front buziladimi |
| --- | --- | --- | --- |
| `GET banners/?placement=` | `site_home`, `app_home`, `home_bottom`, `catalog` | `home_top`, `home_bottom`, `catalog` | **ha** — `site_home` / `app_home` → `400` |
| `GET banners/stats/` | `site_home`, `app_home` maydonlari | bitta `home_top` maydoni | **ha** — eski ikkala maydon yo'q |
| `POST / PATCH banners/` → `placement` | 4 ta qiymat, default `site_home` | 3 ta qiymat, default `home_top` | **ha** — `site_home` / `app_home` → `400` |
| Banner obyekti → `placement` | `site_home` yoki `app_home` | `home_top` | qiymat bo'yicha shart bo'lsa — ha |
| `POST banners/reorder/` | bitta tab'dagi bannerlar | o'zgarmagan (endi `home_top` tab'i bitta ro'yxat) | yo'q |
| "Bosh sahifa" → `home-blocks/` | `banner_placement`: `site_home`, `app_home`, `home_bottom`, `catalog` | **o'zgarmagan** | yo'q |

Qolgan maydonlar, validatsiya, `link_type` / `target`, `status` — o'zgarmagan.

## Frontda qilinadigan ishlar

1. **Tab'lar** — "Sayt · bosh slayder" va "Ilova · bosh ekran" o'rniga bitta tab:

   | Tab | So'rov | Son (`banners/stats/`) |
   | --- | --- | --- |
   | Bosh sahifa · yuqori slayder | `banners/?placement=home_top&is_visible=true` | `home_top` |
   | Bosh sahifa · pastda | `banners/?placement=home_bottom&is_visible=true` | `home_bottom` |
   | Katalog ichida | `banners/?placement=catalog&is_visible=true` | `catalog` |
   | Arxiv | `banners/?is_visible=false` | `archived` |

2. **Banner formasi → "Joylashuv"** — tanlovda 3 ta qiymat: `home_top`, `home_bottom`, `catalog`.
3. **Kanallar** (`show_on_site`, `show_on_ios`, `show_on_android`) — formada bo'lishi shart: "faqat ilovada" yoki "faqat saytda" degan banner endi shu orqali qilinadi.
4. **"Bosh sahifa" sahifasi** (`home-blocks/`) — hech narsa qilinmaydi. `slider` blokining `banner_placement` qiymatlari avvalgidek; `site_home` va `app_home` ikkalasi ham endi bitta ro'yxatni — `home_top` bannerlarini ko'rsatadi.

## `banners/stats/` — yangi javob

```json
{
  "active": 10,
  "scheduled": 4,
  "expired": 2,
  "archived": 2,
  "external": 1,
  "home_top": 9,
  "home_bottom": 2,
  "catalog": 3
}
```

## Mavjud bannerlar

- Hamma `site_home` va `app_home` bannerlari avtomatik `home_top` ga o'tkazilgan.
- Ikkala ro'yxat `position` bo'yicha qo'shilib, 1 dan qayta raqamlangan. Tartib yoqmasa — tab ichida drag & drop (`banners/reorder/`).
- Kanallar **o'zgartirilmagan**. Eski "Ilova · bosh ekran" bannerida `show_on_site=true` turgan bo'lsa, u endi saytning yuqori slayderida ham chiqadi (va aksincha). Deploy'dan keyin yuqori slayderdagi bannerlarning kanallarini bir marta ko'zdan kechirish kerak.

To'liq kontrakt: `docs/admin/banners.md`.
