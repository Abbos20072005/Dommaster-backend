# Mahsulot qisqa tavsifi (uz / ru) — admin panel va mobil uchun

Mahsulotning qisqa tavsifi (`short_description`) endi **ikki tilda**: o'zbekcha va ruscha.
Hozirgi matnlar ruscha deb olindi va `short_description_ru` ga ko'chirildi; o'zbekchasi bo'sh.

---

## Admin panel

Base URL: `{{host}}/api/v1/admin/`

`GET / POST / PATCH products/{id}/` — mahsulot formasida bitta `short_description` o'rniga **ikkita** maydon:

```json
{
  "id": 1520,
  "name_uz": "Sement M400",
  "name_ru": "Цемент М400",
  "short_description_uz": "<p>Qurilish uchun universal sement.</p>",
  "short_description_ru": "<p>Универсальный цемент для строительства.</p>",
  "description_uz": "...",
  "description_ru": "...",
  "...": "..."
}
```

| Maydon | Izoh |
| --- | --- |
| `short_description_uz` | qisqa tavsif, o'zbekcha; HTML (rich text), majburiy emas, `null` / `""` bo'lishi mumkin |
| `short_description_ru` | qisqa tavsif, ruscha; HTML (rich text), majburiy emas, `null` / `""` bo'lishi mumkin |

- **Eski `short_description` kaliti endi kelmaydi va yuborilsa e'tiborga olinmaydi** — formani shu ikki maydonga o'tkazing.
- Ingliz tili loyihada umuman yo'q (`en` so'ralsa — ruscha).
- Mahsulotlar ro'yxatida (`GET products/`) qisqa tavsif avvalgidek yo'q.

---

## Mobil / sayt (client API)

O'zgarish **yo'q**: `short_description` kaliti joyida, endi `Accept-Language` bo'yicha keladi.

| `Accept-Language` | Nima qaytadi |
| --- | --- |
| `uz` | o'zbekcha matn; bo'sh bo'lsa — ruscha |
| `ru` | ruscha matn |
| `en` yoki boshqa til | ruscha matn (ingliz tili qo'llanmaydi) |

Ikkala til ham bo'sh bo'lsa — `null` yoki `""`.
