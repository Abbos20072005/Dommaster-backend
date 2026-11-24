# Bannerlar: har til uchun alohida rasm — admin panel uchun o'zgarishlar

Banner rasmlarida matn bor, shuning uchun endi har tilning o'z rasmlari bor: desktop (16:5) va mobil (1:1) — `uz` va `ru` uchun alohida. To'liq hujjat: `docs/admin/banners.md`.

## Nima o'zgardi

| Joy | Oldin | Endi |
| --- | --- | --- |
| Banner obyekti | `desktop_image`, `mobile_image` | + `desktop_image_uz`, `desktop_image_ru`, `mobile_image_uz`, `mobile_image_ru` |
| Majburiy rasm | `desktop_image` | `desktop_image_ru` (yo'q bo'lsa `400 {"desktop_image_ru": [...]}`) |
| `desktop_image`, `mobile_image` | rasm | **eskirgan**, hali ishlaydi: o'qilganda RU rasm, yuborilsa RU rasmga yoziladi |

Yuborish — avvalgidek `multipart/form-data`: `desktop_image_uz=<fayl>` va h.k.; bo'sh qiymat (`mobile_image_uz=`) rasmni o'chiradi (`desktop_image_ru` dan tashqari). Almashtirilgan / o'chirilgan rasmning eski fayli serverdan o'chiriladi.

O'zbekcha rasm bo'lmasa, o'zbekcha mijozga shu formatdagi ruscha rasm chiqadi — UZ rasmlar ixtiyoriy.

## Frontendda nima qilish kerak

1. **Banner formasi** — "Rasm 16:5" va "Rasm 1:1" o'rniga til bo'yicha 4 ta yuklash maydoni (UZ / RU tab yoki yonma-yon); RU desktop majburiy.
2. Yuborishda `desktop_image` / `mobile_image` o'rniga `desktop_image_ru` / `mobile_image_ru` (+ `_uz`) ishlating.
3. Ro'yxatdagi preview — `desktop_image_ru` (yoki eski `desktop_image`, qiymati bir xil).

Eski forma o'zgarmasa ham buzilmaydi — u RU rasmlarni yuklayveradi.
