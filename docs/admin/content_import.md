# Kontent bulk import / eksport (XLSX) — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET products/content-export/` | mahsulotlar kontentini XLSX qilib yuklab olish (shablon ham shu) |
| `POST content-imports/` | to'ldirilgan XLSX ni yuklash (multipart) → fonda tekshiriladi |
| `GET content-imports/` | importlar jurnali (audit log, paginatsiyali) |
| `GET content-imports/{id}/` | bitta import: holati + tekshiruv hisoboti (xatolar bilan) |
| `GET content-imports/{id}/changes/` | import o'zgartiradigan / o'zgartirgan har bir maydon (paginatsiyali) |
| `POST content-imports/{id}/apply/` | tekshiruvdan o'tgan importni qo'llash (fonda, hammasi yoki hech nima) |
| `DELETE content-imports/{id}/` | qo'llanmagan importni o'chirish |

Swagger: `/swagger/admin/` → **products** (`content-export`), **content-imports**.

Jarayon:

1. **Eksport** — `GET products/content-export/?...` → `.xlsx` fayl. Mavjud kontent + bo'sh maydonlar sariq bilan belgilangan.
2. Kontent jamoasi faylni Excelda to'ldiradi (faqat yashil sarlavhali ustunlar).
3. **Yuklash** — `POST content-imports/` (`file`) → `201`, `status: "validating"`.
4. Front `GET content-imports/{id}/` ni har 2–3 soniyada so'raydi, `status` `validating` dan chiqquncha.
5. `ready` → hisobotni ko'rsatish: nechta qator o'zgaradi (`rows_changed`), nechta o'zgarishsiz, nechta maydon (`changes_count`); tafsilot — `changes/`. `invalid` → xatolar ro'yxati (`errors`, `error`), qo'llab bo'lmaydi — faylni tuzatib qayta yuklash kerak.
6. **Qo'llash** — `POST content-imports/{id}/apply/` → `202`, `status: "applying"`; yana polling → `applied` yoki `failed`.

---

## Eksport — `GET products/content-export/`

Javob — fayl (`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `Content-Disposition: attachment; filename="products_content_20261022_1530.xlsx"`), JSON emas. Frontda `blob` qilib yuklab olinadi.

Query parametrlari — **`products/` ro'yxatining hamma filtrlari** (`category`, `sub_category`, `product_item_category`, `brand`, `is_active`, `publish_status`, `badge`, `in_stock`, `search`, ...) ishlaydi, shular ustiga:

| Parametr | Izoh |
| --- | --- |
| `languages` | `uz`, `ru` yoki `uz,ru` (default — ikkalasi). Faqat shu tilning matn ustunlari chiqadi. Boshqa qiymat → `400` |
| `incomplete` | `true` → faqat kamida bitta tahrirlanadigan maydoni bo'sh mahsulotlar (tanlangan tillar bo'yicha) |

Pagination yo'q — filtrga tushgan hamma mahsulot bitta faylga chiqadi (butun katalog, ~8 ming mahsulot, ~6 soniya). Odatda kategoriya / brend bo'yicha filtrlab olish tavsiya qilinadi.

### Fayl tuzilishi

1-varaq **«Контент»**: 1-qator — ustun kalitlari, 2-qatordan — bitta qator = bitta mahsulot (`id` bo'yicha tartiblangan).

Faqat o'qiladigan ustunlar (kulrang; import ularni **o'qimaydi**, o'zgartirilsa ham e'tiborga olinmaydi va hisobotda `ignored_columns` ga tushadi):

| Ustun | Izoh |
| --- | --- |
| `id` | mahsulot ID — qator kaliti, o'zgartirilmasin |
| `product_code [1C]`, `articul_code [1C]`, `barcode [1C]` | 1C kodlari |
| `brand [1C]` | brend nomi |
| `item_category [1C]` | `Kategoriya / Subkategoriya / Predmet kategoriya` |
| `price [1C]`, `quantity [1C]`, `is_active [1C]` | narx, qoldiq, faollik (`да` / `нет`) |
| `publish_status` | `draft` / `review` / `published` (moderatsiya orqali o'zgaradi) |
| `missing` | shu qatordagi bo'sh tahrirlanadigan ustunlar ro'yxati (Excel filtri uchun qulay) |

`[1C]` belgisi — bu maydonlarning egasi 1C: ularni faqat 1C o'zgartiradi, import orqali **umuman** o'zgarmaydi.

Tahrirlanadigan ustunlar (yashil sarlavha; bo'sh katak sariq — Excel'da to'ldirilgach sariq o'zi yo'qoladi):

| Ustun | Izoh / cheklov |
| --- | --- |
| `name_uz`, `name_ru` | nomi, 500 belgigacha |
| `short_description_uz`, `short_description_ru` | qisqa tavsif — HTML yoki oddiy matn |
| `description_uz`, `description_ru` | tavsif — HTML yoki oddiy matn |
| `meta_title_uz`, `meta_title_ru` | 255 belgigacha |
| `meta_description_uz`, `meta_description_ru` | cheklovsiz |
| `slug_uz`, `slug_ru` | faqat lotin kichik harf, raqam, defis (`drel-bosch-123`); katta harf kichikka aylantiriladi; boshqa mahsulotniki bilan bir xil bo'lmasin |
| `weight` (kg), `length`, `width`, `height` (m) | manfiy bo'lmagan son, 3 xonagacha kasr, vergul ham qabul qilinadi (`2,25`) |

Til bo'yicha (`languages=uz`) olingan faylda faqat `*_uz` ustunlar bo'ladi (+ o'lchamlar). Import ham **faylda bor ustunlarni** o'zgartiradi — keraksiz ustunni (masalan, butun `ru` tilini) o'chirib yuborsa bo'ladi, u maydonlar tegilmaydi.

2-varaq **«Инструкция»**: qoidalar va har bir ustun — nima ekani, tahrirlanadimi, nechta mahsulotda bo'sh.

### Qoidalar

- **Bo'sh katak = maydon o'zgarmaydi.** Import hech narsani tozalamaydi; maydonni bo'shatish — mahsulot kartasida.
- Tavsifga oddiy matn yozilsa (tegsiz), abzaslar `<p>` / `<br>` ga o'giriladi. HTML yozilsa — o'zgarishsiz saqlanadi.
- Fayldan qiymat bazadagi bilan bir xil bo'lsa — o'zgarish hisoblanmaydi (Excel'ning qator oxiri, chetdagi bo'sh joylar farq hisoblanmaydi). Ya'ni o'zgartirilmagan eksport faylini qayta yuklasa — `changes_count: 0`.
- Mahsulot yaratilmaydi va o'chirilmaydi — faqat mavjud `id` lar yangilanadi.
- Rasmlar, atributlar (xarakteristikalar), brend / kategoriya bu import orqali o'zgarmaydi.

---

## Import obyekti

```json
{
  "id": 12,
  "file_name": "products_content_20261022_1530.xlsx",
  "status": "ready",
  "created_by": { "id": 4, "username": "dilnoza", "full_name": "Dilnoza Karimova" },
  "created_at": "2026-10-22T15:41:07.120331",
  "applied_by": null,
  "applied_at": null,
  "languages": ["uz"],
  "rows_total": 420,
  "rows_changed": 137,
  "rows_unchanged": 283,
  "rows_error": 0,
  "changes_count": 291,
  "file": "https://api.buildex.uz/media/content_imports/products_content_20261022_1530.xlsx",
  "columns": ["name_uz", "description_uz", "meta_title_uz"],
  "ignored_columns": ["product_code [1C]", "price [1C]", "missing"],
  "errors": [],
  "error": ""
}
```

| Maydon | Izoh |
| --- | --- |
| `file` * | yuklashda — `.xlsx` fayl (multipart), 20 MB gacha, 50 000 qatorgacha; o'qishda — fayl URL |
| `status` | `validating` (tekshirilmoqda) → `ready` (qo'llash mumkin) / `invalid` (xato bor); `applying` (qo'llanmoqda) → `applied` / `failed` |
| `created_by` / `created_at` | kim, qachon yukladi |
| `applied_by` / `applied_at` | kim qo'llashni bosdi / qachon qo'llandi |
| `languages` | fayldagi tahrirlanadigan ustunlar qaysi tillarga tegishli |
| `columns` | fayldagi tahrirlanadigan ustunlar (shular yangilanadi) |
| `ignored_columns` | faylda bor, lekin import o'qimaydigan ustunlar (1C, xizmat, noma'lum) |
| `rows_total` | fayldagi bo'sh bo'lmagan qatorlar |
| `rows_changed` / `rows_unchanged` | o'zgarishi bor / yo'q qatorlar (xatosiz qatorlar ichida) |
| `rows_error` | xatosi bor qatorlar soni |
| `changes_count` | o'zgaradigan maydonlar soni (`changes/` dagi yozuvlar); `invalid` da `0` |
| `errors` | `[{"row", "product", "column", "message"}]` — `row` = Excel qator raqami, `product` = id (yoki `null`), `message` ruscha; birinchi 500 tasi. `failed` da — qo'llash vaqtidagi konfliktlar |
| `error` | butun faylga tegishli xato (`invalid`: fayl ochilmadi, `id` ustuni yo'q, ...) yoki qo'llash xatosi (`failed`) |

Ro'yxatda (`GET content-imports/`) `file`, `columns`, `ignored_columns`, `errors`, `error` yo'q.

Hammasi faqat o'qiladi, faqat `file` yoziladi.

### Yuklash — `POST content-imports/` (multipart)

```
file=<products_content.xlsx>
```

→ `201` + obyekt (`status: "validating"`). Tekshiruv fonda ketadi (bir necha soniya; 8 ming qator ~5 s).

Xatolar: `.xlsx` emas yoki 20 MB dan katta → `400 {"file": ["..."]}`.

### Tekshiruv xatolari (`errors[].message`)

| Holat | `column` |
| --- | --- |
| `Нет id продукта` — `id` bo'sh / son emas | `id` |
| `Продукт не найден` | `id` |
| `Продукт уже есть в строке N` — bitta mahsulot ikki qatorda | `id` |
| `Ожидается число` / `Ожидается неотрицательное число` / `Слишком большое число` | o'lcham ustuni |
| `Длиннее N символов` | `name_*`, `meta_title_*` |
| `Slug: только латиница, цифры и дефис` | `slug_*` |
| `Такой же slug в строке N` / `Slug занят продуктом N` | `slug_*` |

Fayl darajasidagi xatolar (`error`): `Файл не открывается как XLSX`, `Нет колонки id`, `Нет ни одной редактируемой колонки`, `Колонка повторяется`, `Больше 50000 строк`.

**Bitta xato ham bo'lsa — import `invalid`, hech narsa qo'llanmaydi.** Xatoli qatorni tuzatib (yoki o'chirib) faylni qayta yuklash kerak.

### Qo'llash — `POST content-imports/{id}/apply/` (body yo'q)

→ `202` + obyekt (`status: "applying"`, `applied_by` = siz). Fonda, **bitta tranzaksiyada**: yo hamma o'zgarish yoziladi (`applied`), yo birortasi ham (`failed`). Yarim qo'llangan import bo'lmaydi.

`failed` sabablari (`error` + `errors`):
- tekshiruvdan keyin kimdir shu maydonni panelda o'zgartirgan yoki mahsulot o'chirilgan — `Данные изменились после проверки — загрузите файл заново` (`errors` da qaysi qator / maydon) — yangi eksport olib, qayta yuklash kerak;
- kutilmagan xato — `Не удалось применить: ...`.

`400` xatolar: status `ready` emas (`Import is invalid, only a ready one can be applied.`), o'zgarish yo'q (`Nothing to change.`), allaqachon qo'llanmoqda.

### O'zgarishlar — `GET content-imports/{id}/changes/`

Paginatsiyali (`count, next, previous, next_page, previous_page, results`; `?page=&page_size=`, default 20, max 100), qator raqami bo'yicha tartiblangan. Filtrlar: `product` (id), `field` (masalan `description_uz`).

```json
{
  "count": 291,
  "next": "...",
  "previous": null,
  "next_page": 2,
  "previous_page": null,
  "results": [
    {
      "id": 5501,
      "row": 4,
      "product": { "id": 812, "name": "Дрель Bosch GSB 13 RE", "product_code": "00-00012345" },
      "field": "description_uz",
      "old_value": "",
      "new_value": "<p>Zarbali drel...</p>"
    }
  ]
}
```

`ready` da — nima o'zgarishi (oldindan ko'rish), `applied` da — nima o'zgargani (audit). `product` mahsulot o'chirilgan bo'lsa `null`. `invalid` importda ro'yxat bo'sh.

### O'chirish — `DELETE content-imports/{id}/`

`204`. Faqat `ready`, `invalid`, `failed` importlar (fayli ham o'chadi). `applied`, `validating`, `applying` → `400` — qo'llangan import jurnalda qoladi.

---

## Ro'yxat (audit log) — `GET content-imports/`

Paginatsiya: `count, next, previous, next_page, previous_page, results` (`?page=&page_size=`, default 20, max 100). Default tartib — eng yangisi birinchi.

| Filtr | Izoh |
| --- | --- |
| `status` | `validating`, `ready`, `invalid`, `applying`, `applied`, `failed` |
| `created_by`, `applied_by` | xodim (admin user) id |
| `from_created`, `to_created` | yuklangan sana oralig'i (`YYYY-MM-DD`) |
| `search` | fayl nomi bo'yicha |
| `ordering` | `id`, `created_at`, `applied_at` (`-` bilan teskari) |

Bitta import = jurnaldagi bitta partiya: kim yukladi, kim qo'lladi, qachon, qaysi fayl, va `changes/` da har bir maydonning eski / yangi qiymati.

---

## Frontda qilinadigan ishlar

1. Mahsulotlar sahifasida «Eksport» tugmasi — joriy filtrlar + til tanlovi (`languages`) + «faqat to'ldirilmaganlar» (`incomplete=true`) bilan `products/content-export/` ni yuklab olish.
2. «Import» sahifasi: fayl yuklash → `status` ni polling qilish → hisobot (`rows_*`, `changes_count`, `ignored_columns`, `errors` jadvali, `changes/` jadvali) → «Qo'llash» tugmasi faqat `ready` va `changes_count > 0` da → yana polling → natija.
3. Importlar jurnali — `content-imports/` ro'yxati filtrlar bilan.
