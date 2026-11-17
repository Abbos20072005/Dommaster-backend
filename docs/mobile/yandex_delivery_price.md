# Yetkazib berish narxi (Yandex Dostavka) — mobile / sayt uchun

Kuryer orqali yetkazish narxini (`delivery_type = 0`) Yandex Dostavka hisoblab beradi. Front Yandexga o'zi murojaat qilmaydi, backend endpointini chaqiradi. Backend esa mijozga **eng yaqin filialni** o'zi topib, narxni o'sha filialdan hisoblaydi.

| Metod | URL | Auth |
|---|---|---|
| `POST` | `{{host}}/api/v1/integration/yandex/check-price/` | kerak emas (public) |

Swagger: `/swagger/` → `Yandex Delivery`.

## Qachon chaqiriladi

Checkout'da mijoz kuryer orqali yetkazishni (`delivery_type = 0`) va manzilni tanlagandan keyin chaqiriladi. Savat yoki manzil o'zgarsa, qayta chaqiring.

1. `GET cart/` — belgilangan (`is_checked`) mahsulotlar.
2. `GET auth/customer/addresses/` — manzil va uning koordinatasi.
3. **`POST integration/yandex/check-price/`** — narx.
4. `POST order/` — javobdagi `price` ni `delivery_price` sifatida yuboring.

Pickup'da (`delivery_type = 1`) bu endpoint chaqirilmaydi: yetkazish narxi `0`.

## Ombor qanday tanlanadi

- Backend mijozning nuqtasini oladi, ya'ni `route_points` dagi **oxirgi** nuqtaning `coordinates` qiymatini.
- Shu nuqtaga eng yaqin filial tanlanadi. Filial quyidagi shartlarga mos bo'lishi kerak:
  - faol (`is_active`);
  - turi do'kon (Market) yoki ombor (Warehouse) — showroom olinmaydi;
  - koordinatasi kiritilgan.
- Masofa to'g'ri chiziq bo'yicha hisoblanadi.
- Filial bitta bo'lsa narx o'sha filialdan hisoblanadi. Bir nechta bo'lsa, eng yaqinidan hisoblanadi.
- Tanlangan filial `route_points` dagi **birinchi nuqtaning o'rniga** qo'yiladi. Front birinchi nuqtaga nima yuborsa ham, u almashtiriladi.
- Mos filial topilmasa (koordinatali faol filial yo'q bo'lsa), frontning birinchi nuqtasi o'zgarishsiz ishlatiladi va javobda `branch_id = null` bo'ladi.
- Tovarning qaysi omborda borligi hozircha hisobga olinmaydi.

## Request

```json
{
  "items": [
    {"product_id": 123, "quantity": 2},
    {"product_id": 456, "quantity": 1}
  ],
  "route_points": [
    {"coordinates": [69.247052, 41.35597]},
    {
      "coordinates": [69.279737, 41.311151],
      "fullname": "Toshkent, Yunusobod 4-kvartal, 12-uy",
      "porch": "2",
      "sfloor": "5",
      "sflat": "34"
    }
  ],
  "requirements": {"taxi_class": "cargo", "cargo_type": "lcv_m"}
}
```

**Hozir `route_points` da kamida 2 ta nuqta bo'lishi shart.** Birinchi nuqta — olib ketish nuqtasi. Backend uni eng yaqin filial bilan almashtiradi, shuning uchun unga istalgan do'kon koordinatasini qo'yish mumkin: u faqat validatsiyadan o'tish uchun kerak. Ikkinchi (oxirgi) nuqta — mijozning manzili.

### `items[]`

| Maydon | Turi | Majburiy | Izoh |
|---|---|---|---|
| `product_id` | int | yo'q (tavsiya etiladi) | mahsulot ID. Berilsa, og'irlik va o'lcham mahsulot kartasidan olinadi |
| `quantity` | int ≥ 1 | **ha** | soni |
| `weight` | number | yo'q | kg. Berilsa, mahsulotdagi og'irlik o'rniga ishlatiladi |
| `size` | object | yo'q | `{"length", "width", "height"}`, metrda. Berilsa, mahsulotdagi o'lcham o'rniga ishlatiladi |
| `pickup_point` / `dropoff_point` | int | yo'q | nuqta `id` si. Odatda yuborilmaydi: birinchi va oxirgi nuqta olinadi |
| `age_restricted` | bool | yo'q | yosh cheklovli tovar |

`items` bo'sh bo'lmasligi kerak.

### `route_points[]`

| Maydon | Turi | Majburiy | Izoh |
|---|---|---|---|
| `coordinates` | `[longitude, latitude]` | mijoz nuqtasida **ha** | **tartibi: avval uzunlik, keyin kenglik** (Toshkent ≈ `[69.x, 41.x]`). Teskari yuborilsa, Yandex xato qaytaradi |
| `id` | int | yo'q | nuqta raqami (default: 1, 2, …) |
| `fullname` | string | yo'q | manzil matni |
| `country`, `city`, `street`, `building` | string | yo'q | manzil qismlari |
| `porch`, `sfloor`, `sflat` | string | yo'q | podyezd, qavat, xonadon |

Mijoz nuqtasida `coordinates` bo'lmasa, eng yaqin filial tanlanmaydi va frontning birinchi nuqtasi ishlatiladi.

### `requirements` (ixtiyoriy)

| Maydon | Qiymatlar | Izoh |
|---|---|---|
| `taxi_class` | `courier`, `express`, `cargo` | tarif. Yuborilmasa, Yandex o'zi tanlaydi |
| `cargo_type` | `van`, `lcv_m`, `lcv_l`, `lcv_xl` | faqat `cargo` da. Yuborilmasa, `lcv_l` limiti bilan tekshiriladi |
| `cargo_loaders` | 0–2 | yuk ko'taruvchilar soni |
| `cargo_options` | `auto_courier`, `thermobag` | |
| `pro_courier` | bool | |
| `same_day_data` | `{"delivery_interval": {"from", "to"}}` | ISO datetime |

`taxi_class` berilsa, tovar o'lchami tarif limitidan oshmasligi tekshiriladi (metrda, uzunlik × kenglik × balandlik):

| Tarif | Limit |
|---|---|
| `courier` | 0.8 × 0.5 × 0.5 |
| `express` | 1.0 × 0.6 × 0.5 |
| `cargo` + `van` | 1.7 × 0.96 × 0.9 |
| `cargo` + `lcv_m` | 2.6 × 1.3 × 1.5 |
| `cargo` + `lcv_l` / `lcv_xl` | tekshirilmaydi |

### Boshqa maydonlar (ixtiyoriy)

| Maydon | Default | Izoh |
|---|---|---|
| `skip_door_to_door` | `false` | `true` = eshikkacha emas, kirishgacha yetkaziladi |
| `accept_language` | `ru` | Yandex xabarlarining tili: `ru` yoki `en`. Ilova tiliga bog'liq emas |

## Javob

```json
{
  "result": {
    "price": "45000.0000",
    "currency_rules": {"...": "Yandex qaytargan obyekt, o'zgarishsiz"},
    "requirements": {"taxi_class": "cargo", "cargo_type": "lcv_m"},
    "distance_meters": 8200,
    "eta": 35,
    "zone_id": "tashkent",
    "branch_id": 1,
    "branch_name": "Чукурсай"
  },
  "ok": true
}
```

| Maydon | Izoh |
|---|---|
| `price` | yetkazish narxi, so'mda (string). Uni `POST order/` ga `delivery_price` sifatida o'zgartirmasdan yuboring |
| `currency_rules` | Yandex qaytargan valyuta qoidalari |
| `requirements` | Yandex tanlagan yoki tasdiqlagan tarif |
| `distance_meters` | marshrut uzunligi, metrda (bo'lmasligi mumkin) |
| `eta` | taxminiy vaqt, daqiqada (bo'lmasligi mumkin) |
| `zone_id` | Yandex yetkazish zonasi |
| `branch_id`, `branch_name` | narx qaysi filialdan hisoblangani. Filial topilmasa `null` bo'ladi. Ko'rsatish majburiy emas |

## Xatolar

Hammasi `400` statusi bilan qaytadi:

```json
{"detail": "Не удалось построить маршрут — проверьте адреса и координаты.", "ok": false, "result": "", "error_code": 28}
```

| `error_code` | Qachon | `detail` |
|---|---|---|
| `5` | validatsiya | maydonlar bo'yicha xatolar, masalan `{"route_points": ["Нужно минимум две точки маршрута: забор и доставка"]}`, `{"items": ["Должен быть хотя бы один товар"]}`, yoki tarif limitidan katta o'lcham |
| `28` | Yandex xatosi | ruscha matn. Masalan: koordinata teskari (`swapped_coordinates`), marshrut qurilmadi, zona yo'q, mos mashina topilmadi, tovar juda katta / og'ir, Yandex bilan aloqa yo'q, noto'g'ri narx |

`28` qaytsa, mijozga "yetkazish narxini hisoblab bo'lmadi" degan xabar ko'rsating. Buyurtmani `delivery_price` siz yubormang: narxni qayta so'rang yoki boshqa manzil tanlashni taklif qiling.

## Frontda qilinadigan ishlar

1. Har bir belgilangan mahsulot uchun `product_id` va `quantity` yuboring. Og'irlik va o'lchamni backend o'zi oladi.
2. Mijoz nuqtasini **oxirgi** nuqta qilib, `coordinates: [longitude, latitude]` tartibida yuboring.
3. Hozircha `route_points` ning boshiga yana bitta nuqta qo'shing (istalgan do'kon koordinatasi). Backend uni eng yaqin filial bilan almashtiradi.
4. Javobdagi `price` ni ko'rsating va `POST order/` da `delivery_price` sifatida yuboring.
5. Savat yoki manzil o'zgarsa, narxni qayta so'rang.
