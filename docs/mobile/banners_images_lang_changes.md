# Bannerlar: har til uchun alohida rasm — mobile / sayt uchun o'zgarishlar

Banner rasmlarida matn bor, shuning uchun admin panelda har til uchun alohida rasm yuklanadi (desktop 16:5 va mobil 1:1, `uz` / `ru`).

**Javob formati o'zgarmagan**: `desktop_image` va `mobile_image` avvalgidek keladi, faqat endi **`Accept-Language` tilida**:

- `Accept-Language: uz` → o'zbekcha rasmlar; o'zbekcha rasm yuklanmagan bo'lsa — shu formatdagi ruscha rasm.
- `ru` (yoki boshqa til) → ruscha rasmlar.
- `mobile_image` avvalgidek `null` bo'lishi mumkin — unda `desktop_image` ni ishlating.

Qayerlarga tegishli: `GET base/banner/`, `GET main/` (pastki bannerlar), `GET home/` (slider / banner bloklari).

## Nima qilish kerak

- Banner so'rovlarida `Accept-Language` yuborilayotganini tekshiring (boshqa so'rovlardagidek).
- Ilova tili almashganda bannerlarni (va keshlangan bosh sahifani) qayta so'rang — eski tildagi rasm qolib ketmasin.
