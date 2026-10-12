# Bannerlar — mobile / sayt uchun

Base URL: `{{host}}/api/v1/`
Token kerak emas. Til: `Accept-Language: uz | ru | en` (default `ru`) — faqat `title` ga ta'sir qiladi.

Bannerlar **3 xil joyda** chiqadi. Qaysi banner qayerda turishini admin panelda `placement` (joylashuv) belgilaydi:

| Qayerda | `placement` | Qayerdan olinadi |
| --- | --- | --- |
| Bosh sahifa **yuqorisi** (slayder) | `home_top` — sayt va ilova uchun bitta | `GET base/banner/?placement=home_top` |
| Bosh sahifa **pasti** (reklama bloklari orasida) | `home_bottom` | `GET main/` ichida, yoki `GET base/banner/?placement=home_bottom` |
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

Reklama bloklari (mahsulotlar bo'limlari) va ular orasidagi **pastki bannerlar** bitta ro'yxatda, ko'rsatish tartibida:

```json
{
  "result": [
    { "type": "addsbrands", "data": { "id": 1, "name": "Yozgi chegirmalar", "brand": 12, "products": [ ... ] } },
    { "type": "banner",     "data": { "id": 17, "title": "...", "desktop_image": "...", "mobile_image": null,
                                      "placement": "home_bottom", "link_type": "url", "link": "https://...",
                                      "page": "", "content_type_info": null } },
    { "type": "addsbrands", "data": { "id": 3, "name": "Knauf", "brand": 4, "products": [ ... ] } }
  ],
  "ok": true
}
```

- `type: "banner"` — `data` yuqoridagi banner obyekti bilan bir xil. Bu yerda **faqat `home_bottom`** bannerlar keladi.
- Banner har bir reklama blokidan **keyin** bittadan qo'yiladi. Bannerlar bloklardan ko'p bo'lsa, ortiqchasi kelmaydi; kam bo'lsa, oxirgi bloklar bannersiz keladi.
- `type` bo'yicha render qiling; noma'lum `type` ni o'tkazib yuboring.
- Javob ~17 daqiqa keshlanadi — admin panelda qo'shilgan banner darhol ko'rinmaydi.
- `main/` da `platform` parametri yo'q: platforma bo'yicha aniq ro'yxat kerak bo'lsa, `base/banner/?placement=home_bottom&platform=...` dan oling.

---

## Nima o'zgardi (eski versiyadan farqi)

| Oldin | Hozir |
| --- | --- |
| `base/banner/` parametrsiz **hamma** faol bannerlarni qaytarardi | parametrsiz faqat **yuqoridagilar** (`home_top`). Eski ilova o'zgarishsiz ishlayveradi — unga pastki va kategoriya bannerlari tushmaydi |
| `main/` dagi `type: "banner"` — hamma faol bannerlar (yuqoridagilar takrorlanardi) | faqat `home_bottom` bannerlar. Admin shu turdagi banner qo'shmaguncha `main/` da banner bo'lmaydi |
| Kategoriya sahifasi uchun alohida banner yo'q edi | `base/banner/?placement=catalog` |
| Yuqori slayder ikkita joylashuv edi: `site_home` (sayt), `app_home` (ilova) | bitta `home_top`. Javobdagi `placement` ham `home_top` keladi; so'rovda eski nomlar ishlayveradi, lekin ikkalasi ham bir xil ro'yxatni qaytaradi — shuning uchun `platform` yuborish shart |

Yangi versiyada qilish kerak:

1. Bosh ekran yuqorisi: `base/banner/` ga `placement=home_top` va `platform` qo'shish.
2. Bosh ekran pasti: `main/` dagi `type: "banner"` elementlarini ko'rsatish (oldin ko'rsatilmagan bo'lsa).
3. Kategoriya sahifasi: `base/banner/?placement=catalog&platform=...` — ro'yxat bo'sh bo'lsa hech narsa ko'rsatmaslik.

---

## Eslatmalar

- Kategoriya bannerlari **aniq bir kategoriyaga bog'lanmagan**: hamma kategoriya sahifalari uchun bitta ro'yxat. `content_type_info` — bosilganda qayerga olib borishi, qaysi sahifada ko'rinishi emas.
- Yangi bosh sahifa (`GET home/`, `docs/mobile/home_page.md`) ishlatilsa, bannerlar `slider` / `banner` bloklari ichida keladi — obyekt shakli shu hujjatdagi bilan bir xil.
- Rasm manzillari to'liq (`https://...`), o'lchami serverda o'zgartirilmaydi.
