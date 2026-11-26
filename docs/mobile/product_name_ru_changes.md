# Tovarning ruscha nomi (`name_ru`) va `purchase` eventi — sayt uchun

**Kimga:** sayt (frontend). Ilovada (mobile) hech narsa o'zgarmaydi — yangi maydonni e'tiborsiz qoldirsa bo'ladi.

## Nima uchun

Menejer orqali (saytdan tashqari) qilingan sotuvlar PM Expert CRM'ga ham kiritiladi. Ular tovarni bizning
katalog faylimizdan tanlaydi. Bu fayl kuniga 1 marta yangilanadi va undagi tovar nomlari **ruscha**.

PM Expert skripti saytdagi xaridni `purchase` eventidan oladi, lekin faqat **nom / soni / narx** bilan — tovar
id'si yo'q. Shuning uchun sayt xaridi bilan katalog fayli **nom bo'yicha** solishtiriladi. Buning uchun eventdagi
`item_name` fayldagi nom bilan harfma-harf bir xil bo'lishi kerak.

Hozir uz tilidagi sahifada `name` o'zbekcha keladi — `item_name` ham o'zbekcha ketadi va CRM'da tovar topilmaydi.

## O'zgarish

| Endpoint | Oldin | Hozir | Eski front buziladimi |
| --- | --- | --- | --- |
| Tovar obyekti (pastdagi barcha joylarda) | `name` — so'rov tilida (`Accept-Language`) | `name` o'zgarmagan + yangi **`name_ru`** — so'rov tilidan qat'i nazar har doim ruscha nom | Yo'q, faqat yangi maydon qo'shildi |

`name_ru` qaytadigan joylar — tovar obyekti bor har bir javob:

- `GET cart/` → `result.cart_items[].product.name_ru`
- `GET order/<id>/` → `result.order_items[].product.name_ru`
- `GET products/<id>/` → `result.name_ru` (tovar kartasi)
- `GET products/`, `GET products/recommended/`, `POST product/filter/`, sevimlilar, `products/<id>/links/`,
  `cart/cross-sell/`, home bloklari tovarlari → `content[].name_ru` / tovar obyektining `name_ru`

Qiymat: tovarning ruscha nomi. U bo'sh bo'lsa, asosiy nom olinadi — katalog faylidagi `Наименование` ustunida
ham aynan shu qiymat turadi. Har doim string, `null` bo'lmaydi.

```json
{
  "id": 571,
  "name": "Bir klavishli o'chirgich Schneider Electric Asfora 10 A, antrasit",
  "name_ru": "Выключатель 1-клавишный Schneider Electric Asfora 10 А, антрацит",
  "price": 28600.0,
  "...": "..."
}
```

`Accept-Language: ru` bo'lganda `name` va `name_ru` bir xil keladi.

## Frontda qilinadigan ishlar

1. **`purchase` eventida** har bir tovarning `item_name` maydoniga sahifa tilidan qat'i nazar
   **`product.name_ru`** yozilsin. Uz sahifada ham, ru sahifada ham.
2. Tovar ma'lumoti eventni yuboradigan joyda qayerdan olinsa, `name_ru` ham o'sha yerdan olinadi. Buyurtma
   berishdan oldingi `GET cart/` javobida ham, keyingi `GET order/<id>/` javobida ham bor.
3. Ekranda ko'rsatiladigan nom o'zgarmaydi — u avvalgidek `name` (sahifa tilida).
4. Tavsiya: `view_item`, `add_to_cart`, `begin_checkout` eventlarida ham `item_name = name_ru` qo'yilsin, shunda
   analitikada bitta tovar bitta nom bilan ko'rinadi. CRM uchun shart faqat `purchase`.
5. `item_id` (tovar `id`) avvalgidek yuborilaversin — PM Expert hozir uni o'qimaydi, lekin keyin kerak bo'lishi
   mumkin.

## Tekshirish

Uz tilidagi sahifada savatga tovar qo'shib, buyurtma bering. GTM Preview yoki brauzer konsolida `dataLayer`'dagi
`purchase` eventining `items[].item_name` qiymati ruscha bo'lishi va `GET cart/` (yoki `GET order/<id>/`)
javobidagi `product.name_ru` bilan bir xil chiqishi kerak.
