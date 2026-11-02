# Buyurtma statuslari o'zgardi — mobile / sayt uchun

**02.11.2026 dan** buyurtma `status` kodlari yangilandi: yangi **«Tasdiqlangan»** (`1` Confirmed) statusi qo'shildi va kodlar buyurtma yo'li tartibida qayta raqamlandi. Endpoint'lar va maydon nomlari o'zgarmadi — faqat `status` sonlarining ma'nosi o'zgardi.

## Yangi kodlar

| `status` | Backend nomi | Frontda | Oldingi kodi |
| --- | --- | --- | --- |
| `0` | Pending | Tushgan | `0` |
| `1` | Confirmed | **Tasdiqlangan** (yangi) | — |
| `2` | Collecting | Tayyorlash (yig'ilmoqda) | `1` |
| `3` | Delivering | Yetkazilmoqda (faqat yetkazib berishli buyurtma) | `2` |
| `4` | Ready for pickup | Olib ketishga tayyor (faqat olib ketishli buyurtma) | `5` |
| `5` | Completed | Yakunlandi | `3` |
| `6` | Canceled | Bekor qilingan | `4` |

Odatdagi yo'l:
- yetkazib berish: `0` → `1` → `2` → `3` → `5`;
- olib ketish: `0` → `1` → `2` → `4` → `5`;
- istalgan joydan `6` (bekor qilish).

`1` ni faqat admin panel qo'yadi. Online to'lov o'tganda (Click / Payme / Uzum / Atmos) va do'konda to'lanadigan olib ketishda buyurtma avvalgidek darhol `2` Collecting ga o'tadi, `1` siz. 1C ham `1` ni yubormaydi. Shuning uchun ilova `0` dan keyin `1` ni ham, to'g'ridan-to'g'ri `2` ni ham ko'rsata olishi kerak.

## Nima o'zgardi

| Joy | Oldin | Hozir | Eski front buziladimi |
| --- | --- | --- | --- |
| `GET order/active/`, `GET order/history/`, buyurtma detail / yaratish javobi — `status` | `0`–`5` (eski ma'no) | `0`–`6` (yangi ma'no, jadval yuqorida) | **ha** — nomlar noto'g'ri chiqadi (masalan, yakunlangan `5` eski frontda "Ready for pickup" bo'lib ko'rinadi) |
| `order/history/` | `3` va `4` | `5` va `6` (yakunlangan + bekor qilingan) | yo'q — server o'zi filtrlaydi |
| `POST order/<id>/cancel/` | `status` `0` yoki `1` da | `0`, `1` yoki `2` da | yo'q, lekin "Bekor qilish" tugmasini ko'rsatish shartini yangilang |
| To'lov turi `4` (qabul qilganda) bilan `POST order/payment/` | darhol `1` | darhol `2` | ha, agar ilova `1` ni tekshirsa |
| Buyurtma statusi push'i, `data.status` (string) | `"1"`–`"5"` | `"1"`–`"6"` (`"0"` yuborilmaydi) | **ha** — push matnidan emas, `data.status` dan nom olsa |
| Push `data.branch_id` / `pickup_deadline` | `status` `"5"` da | `status` `"4"` da | **ha** |

## Push matnlari (ru)

| `status` | `title` | `body` |
| --- | --- | --- |
| 1 | Заказ подтверждён | Ваш заказ №125 подтверждён. |
| 2 | Заказ в сборке | Ваш заказ №125 принят и передан в сборку. |
| 3 | Заказ в доставке | Ваш заказ №125 передан в доставку. |
| 4 | Заказ готов к выдаче | Ваш заказ №125 ждёт вас в магазине «Chilonzor». Заберите его до 24.10.2026 15:30. |
| 5 | Заказ выполнен | Ваш заказ №125 выполнен. Спасибо за покупку! |
| 6 | Заказ отменён | Ваш заказ №125 отменён. |

`data`: `type=order_status`, `order_id`, `status`, `deeplink=buildex://order/<id>` (hammasi string); `status` `"4"` da qo'shimcha `branch_id`, `pickup_deadline`.

## Frontda qilinadigan ishlar

1. Status nomlari / ranglari / ikonkalari xaritasini yangi jadval bo'yicha yangilang, `1` Tasdiqlangan qo'shing.
2. Buyurtma bosqichlari (stepper / timeline): yetkazib berishda `0 → 1 → 2 → 3 → 5`, olib ketishda `0 → 1 → 2 → 4 → 5`. `1` o'tkazib yuborilishi mumkin (to'lovdan keyin to'g'ridan-to'g'ri `2`).
3. "Bekor qilish" tugmasi: `status` `0`, `1` yoki `2` bo'lganda.
4. "Yakunlangan" / "Bekor qilingan" tekshiruvlari: `3` / `4` → `5` / `6`.
5. Olib ketish: "Olib ketishga tayyor" ekrani va muddat (`pickup_deadline`, `pickup_expired`) `5` emas, `4` da.
6. Push qabul qiluvchi: `data.status` bo'yicha nom va `branch_id` / `pickup_deadline` ni o'qish shartini yangilang (`"5"` → `"4"`).
7. Ilovaning eski versiyalari yangi kodlarni noto'g'ri ko'rsatadi — majburiy yangilash kerakmi, PM bilan kelishing.
