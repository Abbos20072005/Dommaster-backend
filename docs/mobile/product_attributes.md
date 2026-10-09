# Mahsulot atributlari — mobile / web uchun

Base URL: `{{host}}/api/v1/`
Token shart emas.

Mahsulot detalida `attributes` maydoni keladi — mahsulotning xususiyatlari (quvvat, material, boshqaruv turi va h.k.):

```
GET products/{id}/
```

- Mahsulotning **barcha** xususiyatlari shu yerda. Eski `characteristics` maydoni ham qolgan, lekin endi u `attributes` ning nusxasi (pastda) — yangi kodda `attributes` ni ishlating.
- Til `Accept-Language` headeridan olinadi (`uz`, `ru`, `en`; default `ru`).
- Filtrlar ham shu atributlardan quriladi — `docs/mobile/product_filters.md`.

---

## Javob

```json
{
  "ok": true,
  "result": {
    "id": 154,
    "name": "...",
    "characteristics": [
      { "id": 25, "name": "Kafolat", "unit": "", "value": "Ha" },
      { "id": 23, "name": "Boshqaruv", "unit": "", "value": "Pult" },
      { "id": 22, "name": "Quvvat", "unit": "kVt", "value": "2.5" },
      { "id": 24, "name": "Material", "unit": "", "value": "Po'lat" }
    ],
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

Ko'rsatish: `name` — `value` `unit` (masalan "Quvvat — 2.5 kVt").

### `characteristics` (eskirgan)

Eski ilova versiyalari uchun qoldirilgan: `attributes` dagi qatorlarning o'zi, o'sha tartibda, `value_type` siz (`id`, `name`, `unit`, `value`). `id` endi atribut ID'si. Ikkalasini birga chizmang — bir xil ma'lumot ikki marta chiqadi. Mahsulotlar ro'yxatidagi (`product/filter/` va boshqalar) `characteristics` ham shu ko'rinishda.

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
- So'ralgan tilda tarjima bo'lmasa, ruscha qiymat qaytadi. 1C dan kelgan xususiyatlar hozircha faqat ruscha — `uz` va `en` da ham ruscha matn keladi.
- `attributes` faqat detalda; ro'yxatlarda faqat `characteristics` bor.
