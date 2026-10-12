# Bannerlar — mobile / sayt uchun

Base URL: `{{host}}/api/v1/`
Token kerak emas. Til: `Accept-Language: uz | ru | en` (default `ru`) — faqat `title` ga ta'sir qiladi.

Bannerlar **3 xil joyda** chiqadi. Qaysi banner qayerda turishini admin panelda `placement` (joylashuv) belgilaydi:

| Qayerda | `placement` | Qayerdan olinadi |
| --- | --- | --- |
| Bosh sahifa **yuqorisi** (slayder) | `home_top` — sayt va ilova uchun bitta | `GET base/banner/?placement=home_top` |
| Bosh sahifa **pasti** (reklama bloklari orasida, ro'yxat bo'lib) | `home_bottom` | `GET main/` ichida, yoki `GET base/banner/?placement=home_bottom` |
| **Kategoriya sahifasi** | `catalog` | `GET base/banner/?placement=catalog` |

Swagger: `/swagger/` → **Base** → "Banner", **Main** → "Main page informations".

---

## `GET base/banner/`

Hozir ko'rsatilishi kerak bo'lgan bannerlar (arxivda emas, muddati boshlangan va tugamagan), admin paneldagi tartibda.

| Parametr | Qiymatlar | Izoh |
| --- | --- | --- |
| `placement` | `home_top`, `home_bottom`, `catalog` | qaysi joy uchun. **Yuborilmasa — `home_top`**. Eski `site_home` / `app_home` nomlari ham qabul qilinadi (= `home_top`) |
| `platform` | `site`, `ios`, `android` | faqat shu platformada ko'rsatishga ruxsat berilgan bannerlar. **Har doim yuboring** |

Ilova uchun so'rovlar:

```
GET base/banner/?placement=home_top&platform=ios        → bosh ekran, yuqori slayder
GET base/banner/?placement=home_bottom&platform=ios     → bosh ekran, pastki bannerlar
GET base/banner/?placement=catalog&platform=ios         → kategoriya sahifasi
```

Sayt uchun xuddi shu so'rovlar, `platform=site`. Yuqori slayder sayt va ilova uchun **bitta ro'yxat** — qaysi banner qayerda chiqishini faqat `platform` ajratadi.

Javob — `200`:

```json
{
  "result": [
    {
      "id": 412,
      "title": "Knauf kuzgi aksiya",
      "desktop_image": "https://.../media/banner/desktop/knauf.png",
      "mobile_image": "https://.../media/banner/mobile/knauf.png",
      "placement": "catalog",
      "link_type": "category",
      "link": "",
      "page": "",
      "content_type_info": { "model": "productitemcategory", "id": 31 }
    }
  ],
  "ok": true
}
```

| Maydon | Izoh |
| --- | --- |
| `title` | ichki nom (admin uchun) — bannerda matn sifatida ko'rsatish shart emas, `alt` / accessibility uchun |
| `desktop_image` | keng rasm (16:5), har doim bor |
| `mobile_image` | kvadrat rasm (1:1), **`null` bo'lishi mumkin** — unda `desktop_image` ni ishlating |
| `placement` | banner qaysi joy uchun |
| `link_type`, `link`, `page`, `content_type_info` | bosilganda qayerga olib borishi — pastga qarang |

- Ro'yxat bo'sh (`[]`) bo'lishi mumkin — unda banner joyini **umuman ko'rsatmang** (bo'sh joy qoldirmang).
- Noma'lum `placement` yuborilsa xato emas, bo'sh ro'yxat qaytadi.
- Tartib — admin paneldagi tartib, o'zgartirmang.

### Bosilganda qayerga o'tadi

| `link_type` | Qaysi maydon | Nima qilish kerak |
| --- | --- | --- |
| `category` | `content_type_info` | kategoriyani ochish. `model`: `productcategory` (1-daraja), `productsubcategory` (2-daraja), `productitemcategory` (3-daraja); `id` — o'sha kategoriya. Mahsulotlari: `POST product/filter/` — `category` / `sub_category` / `item_category` |
| `product` | `content_type_info` (`model: "product"`) | mahsulot sahifasi: `GET products/<id>/` |
| `brand` | `content_type_info` (`model: "brand"`) | brend mahsulotlari: `POST product/filter/` — `brand` |
| `badge` | `content_type_info` (`model: "productbadge"`) | teg (badge) mahsulotlari. Mijoz API'da teg bo'yicha ro'yxat **hozircha yo'q** — banner bosilmaydigan bo'lib tursin |
| `page` | `page` | ilova / sayt ichidagi sahifa, yo'l `/` bilan boshlanadi (masalan `/pro`, `/delivery`) |
| `url` | `link` | tashqi havola — brauzerda ochiladi |

- `content_type_info` `null` yoki kerakli maydon bo'sh (`link: ""`, `page: ""`) bo'lsa — banner **bosilmaydi** (eski bannerlarda shunday bo'lishi mumkin).
- Noma'lum `link_type` (keyin qo'shilishi mumkin) — bosilmaydigan banner sifatida ko'rsating, ilova yiqilmasin.

---

## `GET main/` — bosh sahifa pasti

Reklama bloklari (mahsulotlar bo'limlari) va ular orasidagi **pastki bannerlar ro'yxatlari**, ko'rsatish tartibida:

```json
{
  "result": [
    { "type": "addsbrands", "data": { "id": 1, "name": "Yozgi chegirmalar", "brand": 12, "products": [ ... ] } },
    { "type": "banners",    "data": [
        { "id": 17, "title": "...", "desktop_image": "...", "mobile_image": null, "placement": "home_bottom",
          "link_type": "url", "link": "https://...", "page": "", "content_type_info": null },
        { "id": 18, "title": "...", "desktop_image": "...", "mobile_image": "...", "placement": "home_bottom",
          "link_type": "page", "link": "", "page": "/pro", "content_type_info": null }
    ] },
    { "type": "addsbrands", "data": { "id": 3, "name": "Knauf", "brand": 4, "products": [ ... ] } },
    { "type": "banners",    "data": [ { "id": 19, ... } ] }
  ],
  "ok": true
}
```

- Har bir reklama blokidan **keyin** bitta `type: "banners"` elementi keladi: `data` **ro'yxat**. Pastki (`home_bottom`) bannerlar bloklar orasida **teng bo'linadi**, admin paneldagi tartibda; qoldiq birinchi ro'yxatlarga tushadi.
- Misol: 2 ta blok — 5 ta banner → `[1, 2, 3]` va `[4, 5]`; 3 ta banner → `[1, 2]` va `[3]`; 1 ta banner → faqat birinchi blokdan keyin `[1]`.
- Banner bloklardan kam bo'lsa, oxirgi bloklardan keyin element **kelmaydi** (bo'sh ro'yxat yuborilmaydi). Hech bir banner tushib qolmaydi.
- Ro'yxatdagi har bir element — `base/banner/` dagi banner obyekti.
- Eski `type: "banner"` (`data` — bitta obyekt, har blokdan keyin bittadan) endi **kelmaydi**.
- `type` bo'yicha render qiling; noma'lum `type` ni o'tkazib yuboring.
- Javob ~17 daqiqa keshlanadi — admin panelda qo'shilgan banner darhol ko'rinmaydi.
- `main/` da `platform` parametri yo'q: platforma bo'yicha aniq ro'yxat kerak bo'lsa, `base/banner/?placement=home_bottom&platform=...` dan oling.

---

## Nima o'zgardi (eski versiyadan farqi)

| Oldin | Hozir |
| --- | --- |
| `base/banner/` parametrsiz **hamma** faol bannerlarni qaytarardi | parametrsiz faqat **yuqoridagilar** (`home_top`). Eski ilova o'zgarishsiz ishlayveradi — unga pastki va kategoriya bannerlari tushmaydi |
| `main/` dagi `type: "banner"` — hamma faol bannerlar (yuqoridagilar takrorlanardi) | `type: "banners"` — har reklama blokidan keyin `home_bottom` bannerlarning **ro'yxati** (bloklar orasida teng bo'lingan). Admin shu turdagi banner qo'shmaguncha `main/` da banner bo'lmaydi |
| Kategoriya sahifasi uchun alohida banner yo'q edi | `base/banner/?placement=catalog` |
| Yuqori slayder ikkita joylashuv edi: `site_home` (sayt), `app_home` (ilova) | bitta `home_top`. Javobdagi `placement` ham `home_top` keladi; so'rovda eski nomlar ishlayveradi, lekin ikkalasi ham bir xil ro'yxatni qaytaradi — shuning uchun `platform` yuborish shart |

Yangi versiyada qilish kerak:

1. Bosh ekran yuqorisi: `base/banner/` ga `placement=home_top` va `platform` qo'shish.
2. Bosh ekran pasti: `main/` dagi `type: "banners"` elementlarini ko'rsatish — har birida `data` ro'yxat (karusel / ro'yxat). `type: "banner"` ni o'qiydigan kod kerak emas.
3. Kategoriya sahifasi: `base/banner/?placement=catalog&platform=...` — ro'yxat bo'sh bo'lsa hech narsa ko'rsatmaslik.

---

## Eslatmalar

- Kategoriya bannerlari **aniq bir kategoriyaga bog'lanmagan**: hamma kategoriya sahifalari uchun bitta ro'yxat. `content_type_info` — bosilganda qayerga olib borishi, qaysi sahifada ko'rinishi emas.
- Yangi bosh sahifa (`GET home/`, `docs/mobile/home_page.md`) ishlatilsa, bannerlar `slider` / `banner` bloklari ichida keladi — obyekt shakli shu hujjatdagi bilan bir xil.
- Rasm manzillari to'liq (`https://...`), o'lchami serverda o'zgartirilmaydi.
