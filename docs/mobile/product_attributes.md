# Mahsulot atributlari — mobile / web uchun

Base URL: `{{host}}/api/v1/`
Token shart emas.

Mahsulot detalida yangi `attributes` maydoni keladi — admin panelda mahsulotga kiritilgan xususiyatlar (quvvat, material, boshqaruv turi va h.k.):

```
GET products/{id}/
```

- Yangi endpoint yo'q, mavjud javobga maydon qo'shildi. Qolgan maydonlar (jumladan `characteristics`) o'zgarmagan.
- Til `Accept-Language` headeridan olinadi (`uz`, `ru`, `en`; default `ru`).
- Swagger'dagi "Product detail" javob sxemasida bu maydon ko'rinmaydi — shu hujjatga tayaning.

---

## Javob

```json
{
  "ok": true,
  "result": {
    "id": 154,
    "name": "...",
    "characteristics": [],
    "attributes": [
      { "id": 25, "name": "Kafolat", "value_type": "boolean", "unit": "", "value": "Ha" },
      { "id": 23, "name": "Boshqaruv", "value_type": "list", "unit": "", "value": "Pult" },
      { "id": 22, "name": "Quvvat", "value_type": "number", "unit": "kVt", "value": "2.5" },
      { "id": 24, "name": "Material", "value_type": "text", "unit": "", "value": "Po'lat" }
    ]
  }
}
```

| Maydon | Izoh |
| --- | --- |
| `id` | atribut ID'si (bitta mahsulot ichida takrorlanmaydi — ro'yxat `key` i sifatida ishlatsa bo'ladi) |
| `name` | atribut nomi, so'ralgan tilda |
| `value_type` | `number`, `list`, `text`, `boolean` |
| `unit` | o'lchov birligi; faqat `number` da to'ladi, qolganlarida `""` |
| `value` | ko'rsatishga tayyor qiymat, **har doim string** |

Ko'rsatish: `name` — `value` `unit` (masalan "Quvvat — 2.5 kVt"). `characteristics` bilan bir xil komponentda chizsa bo'ladi.

| `value_type` | `value` |
| --- | --- |
| `number` | son, string ko'rinishida: `"2.5"` |
| `list` | tanlangan variant matni, so'ralgan tilda |
| `text` | matn, so'ralgan tilda |
| `boolean` | tayyor matn: `Ha` / `Yo'q`, `Да` / `Нет`, `Yes` / `No` |

---

## Eslatmalar

- Mahsulotda atribut kiritilmagan bo'lsa — `"attributes": []` (maydon har doim bor, `null` bo'lmaydi).
- Tartib — admin kategoriyada belgilagan tartib; frontendda saralash kerak emas.
- Admin o'chirib qo'ygan (nofaol) atributlar kelmaydi.
- So'ralgan tilda tarjima bo'lmasa, ruscha qiymat qaytadi (hozircha `en` da nom va matnli qiymatlar ko'pincha ruscha keladi).
- `attributes` faqat detalda. Mahsulotlar ro'yxatida va filtrlarda hozircha yo'q.
