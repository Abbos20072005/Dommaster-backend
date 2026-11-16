# Sahifalar uchun Last-Modified / 304 — sayt (BLD-451)

Maqsad: Yandex va Google tovar, kategoriya va brend sahifasini har safar to'liq yuklab olmasin. O'zgarmagan
sahifaga `If-Modified-Since` so'rovi kelsa, sayt **304** qaytarsin. Narx yoki qoldiq o'zgargan bo'lsa,
albatta **200** qaytarsin.

Hozir (16.11) sayt sahifalarida `ETag` ham, `Last-Modified` ham yo'q, `Cache-Control: private, no-cache,
no-store`, shuning uchun 304 hech qachon qaytmaydi. HTML'ni Next.js beradi, demak sarlavhalarni ham sayt
qo'yadi. Backend'da yangi endpoint yo'q, mavjud `updated_at` maydonidan foydalaniladi.

## Qaysi vaqt

| Sahifa | Endpoint | `Last-Modified` |
| --- | --- | --- |
| Tovar `/product/<slug>` | `products/{id}/` | tovarning `updated_at` |
| Kategoriya (3 daraja) | kategoriya detali + `product/filter/` | kategoriyaning `updated_at` va sahifadagi tovarlarning `updated_at` qiymatlaridan eng kattasi |
| Brend `/brand/<slug>` | `brands/{id}/` + tovarlar ro'yxati | brendning `updated_at` va sahifadagi tovarlarning `updated_at` qiymatlaridan eng kattasi |

`updated_at` tovarning ro'yxat va detal javoblarida, brend va kategoriyaning barcha javoblarida bor.

Tovarning `updated_at` maydoni quyidagi hollarda yangilanadi:
- 1C narx yuborganda (`price`, `discount_price`, `discount`);
- 1C tovar kartasini qayta yuborganda (nom, qoldiq `quantity`, `is_active` va h.k.);
- buyurtma qoldiqni olganda (Tayyorlash statusi) yoki qaytarganda (Bekor qilindi);
- admin panelda tovar saqlanganda.

Rasm, xususiyat (atribut), sharh yoki savol o'zgarishi tovarning `updated_at` maydonini yangilamaydi.

## Vaqt formati

`updated_at` **Toshkent vaqtida, zonasiz** keladi: `"2026-10-30T14:13:08.489201"`. HTTP sarlavhasi uchun uni
`+05:00` deb o'qib, GMT'ga o'tkazing va soniyagacha yaxlitlang:

```
updated_at  2026-10-30T14:13:08.489201   (Toshkent)
Last-Modified: Fri, 30 Oct 2026 09:13:08 GMT
```

## Javob

1. Sahifa javobiga `Last-Modified` sarlavhasini qo'ying.
2. So'rovda `If-Modified-Since` bo'lsa va u `Last-Modified` qiymatiga teng yoki undan keyin bo'lsa,
   tanasiz **304** qaytaring. Aks holda odatdagi 200 qaytaring.
3. `Cache-Control: no-store` o'rniga `no-cache` (yoki `private, no-cache`) qo'ying. `no-cache` brauzer va
   botga sahifani saqlashga ruxsat beradi, lekin har safar so'rab tekshirishni talab qiladi. Shuning uchun
   eski narx ko'rsatilmaydi.

304'ni Next.js o'zi qaytarishi mumkin, yoki faqat `Last-Modified` sarlavhasini beradi va 304'ni nginx
qaytaradi. Qaysi biri ishlashini prodda `curl` bilan tekshiring.

## Tekshirish

```bash
curl -s -o /dev/null -D - https://buildex.uz/product/<slug> | grep -i last-modified
curl -s -o /dev/null -w "%{http_code}\n" -H "If-Modified-Since: <yuqoridagi qiymat>" https://buildex.uz/product/<slug>
```

Ikkinchi buyruq `304` chiqarishi kerak. Admin panelda tovar narxini o'zgartirgandan keyin o'sha buyruq `200`
chiqarishi kerak.
