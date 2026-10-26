# PRO: loyihalar va xarajatlar — mobil ilova / sayt uchun o'zgarishlar

Base URL: `{{host}}/api/v1/`

Admin mijozga **PRO** maqomini beradi. PRO mijoz o'z loyihalarini (uy, ofis, obyekt) yaratadi, buyurtmadagi
tovarlarni loyihalarga bog'laydi va har bir loyiha qancha turganini ko'radi. To'liq tavsif:
[pro_projects.md](pro_projects.md).

## Mavjud endpointlarda nima o'zgardi

| Endpoint | Oldin | Hozir | Eski front buziladimi |
| --- | --- | --- | --- |
| `GET auth/auth/me/` | `role`: `user` / `prorab` | o'zgarmagan; `prorab` = PRO | yo'q |
| `PATCH auth/customer/update/` → `role` | mijoz o'zi o'zgartira olardi | **faqat o'qiladi** (yuborilsa e'tiborga olinmaydi) | rol tanlash ekrani bo'lsa — u ishlamay qoladi |
| `GET order/<id>/` → `order_items[]` | `id, quantity, product` | `+ project`: `{"id", "name"}` yoki `null` | yo'q |
| `POST order/` (checkout) | — | o'zgarmagan: so'rov, javob, narxlar avvalgidek | yo'q |

PRO = eski **prorab** (`role` = `prorab`). Yangi maydon yo'q. Rolni endi faqat admin o'zgartiradi (eski parolli
`auth/register/` hali `role` ni qabul qiladi — eski ilova versiyasi uchun tegilmagan).

`project` = `null` ikki holatda: qator bog'lanmagan, yoki mijoz hozir PRO emas.

## Yangi endpointlar (hammasi token bilan)

Mijoz PRO bo'lmasa, har bir `/pro/` endpoint **403** qaytaradi (`error_code` 34). PRO bo'limini shu bo'yicha
yashirish mumkin, lekin `auth/me/` dagi `role == "prorab"` bo'yicha yashirish yaxshiroq.

| Endpoint | Nima qiladi |
| --- | --- |
| `GET pro/projects/?status=active\|archived` | loyihalar ro'yxati |
| `POST pro/projects/` | yaratish: `name` (3–100 belgi), `address`, `comment` |
| `GET / PATCH / DELETE pro/projects/<id>/` | ko'rish / tahrirlash / o'chirish |
| `POST pro/projects/<id>/archive/`, `.../restore/` | arxivga / arxivdan |
| `POST pro/orders/<id>/link/` | buyurtmani yoki `item_ids` qatorlarini loyihaga bog'lash |
| `POST pro/orders/<id>/unlink/` | bog'lanishni olib tashlash |
| `GET pro/orders/unlinked/` | bog'lanmagan qatori bor buyurtmalar (sahifalangan) |
| `GET pro/dashboard/?from=&to=` | jami + har bir loyiha + kategoriyalar |
| `GET pro/projects/<id>/summary/?from=&to=` | bitta loyiha xarajati |
| `GET pro/projects/<id>/items/?from=&to=&page=&page_size=` | loyihaga bog'langan tovarlar |

## Yangi xato kodlari

| `error_code` | HTTP | Qachon | Frontda |
| --- | --- | --- | --- |
| 34 | 403 | mijoz PRO emas | PRO bo'limini yashirish |
| 35 | 400 | shu nomli faol loyiha bor (yaratish, nomni o'zgartirish, arxivdan qaytarish) | "Bu nom band" |
| 36 | 409 | tovar bog'langan loyihani o'chirish | "Arxivlash" ni taklif qilish |
| 37 | 409 | qatorlar boshqa loyihaga bog'langan; `detail.conflicting_item_ids` | so'rab, `"force": true` bilan qayta yuborish |
| 38 | 400 | arxivdagi loyihaga bog'lash | — |
| 39 | 400 | bekor qilingan buyurtmani bog'lash | — |

Boshqa mijozning loyihasi yoki buyurtmasi → 404.

## Bilish kerak

- Pul summalari xarajat endpointlarida **string** bo'lib keladi, 2 xona bilan: `"241666.67"`.
- Xarajatga faqat **to'langan** va bekor qilinmagan buyurtmalar kiradi (naqd to'lov — admin "to'landi" qilgandan
  keyin). Bog'lash esa har qanday bekor qilinmagan buyurtmaga mumkin.
- Loyihadagi `items_count` / `orders_count`, `summary/`, `dashboard/` va `items/` ro'yxati — hammasi bir xil qoida:
  faqat to'langan, bekor qilinmagan buyurtmalar. To'lanmagan buyurtmaga bog'langan tovar to'lov o'tgach chiqadi.
- Promokod chegirmasi va yetkazish narxi buyurtma qatorlariga summasiga qarab bo'linadi. Ikki loyihaga bo'lingan
  buyurtma ham to'lagan summaga teng chiqadi.
- PRO olib qo'yilsa loyihalar o'chmaydi, faqat yashiriladi. Qayta berilsa hammasi joyida.
- PRO bo'lishidan oldingi buyurtmalarni ham bog'lash mumkin (vaqtinchalik qoida).
