# Buyurtma qatorida narx — `items[].unit_price`

## Muammo

Buyurtma sahifasidagi «Narx» va qator «Jami» ustunlari `items[].product.price` dan — mahsulotning **hozirgi** narxidan olinardi. Narx buyurtmadan keyin o'zgarsa (masalan, narxlar 100 so'mgacha yaxlitlangani), qatorlar yig'indisi «Mahsulotlar» summasiga to'g'ri kelmaydi.

Misol, buyurtma 406: 3 × 12 600 = 37 800 ko'rsatilgan, lekin buyurtma paytida narx 12 558 bo'lgan → «Mahsulotlar» 37 674.

## O'zgarish

`GET orders/{id}/` (va `POST` / `PATCH` javobi) → `items[]` ga `unit_price` qo'shildi (faqat o'qish uchun):

```json
"items": [
  {
    "id": 812,
    "product": {"id": 5120, "name": "Лампа светодиодная Dusel Mr16, 7 Вт, 4000 К", "product_code": "00-00031245",
                "price": 12600.0, "discount_price": null},
    "quantity": 3,
    "unit_price": "12558.00",
    "ikpu_code": ""
  }
]
```

| Maydon | Tur | Ma'nosi |
|---|---|---|
| `unit_price` | string (decimal) \| null | buyurtma paytidagi **1 dona** narxi, mahsulot chegirmasidan keyin (savat shuni olgan). `null` = maydon paydo bo'lishidan oldingi eski qator |

`items[].product.price` / `discount_price` — avvalgidek mahsulotning hozirgi narxi.

## Panel nima qilishi kerak

- Qatordagi «Narx» = `unit_price`; `null` bo'lsa → `product.discount_price ?? product.price`.
- Qator «Jami» = shu narx × `quantity`.
- «Mahsulotlar», «Yetkazish», «Jami» — avvalgidek buyurtmaning `products_total_price`, `delivery_price`, `total_price` maydonlaridan.

Eslatma: `PATCH orders/{id}/` da `items` qayta yuborilsa, qatorlar qayta yaratiladi va **har bir qator `unit_price` ni mahsulotning hozirgi narxidan oladi** (buyurtma summalari ham qayta hisoblanadi) — shuning uchun ular yana bir-biriga mos keladi.
