# Qo'llab-quvvatlash chati — admin panel uchun

Base URL: `{{host}}/api/v1/admin/`
Token kerak: `Authorization: Bearer <admin_access_token>` (`auth/login/` dan olinadi; tokensiz → `401`).

| Endpoint | Nima uchun |
| --- | --- |
| `GET chats/` | chatlar ro'yxati (paginatsiyali, oxirgi faollik bo'yicha) |
| `GET chats/stats/` | kartochkalar: jami / javobsiz / mehmon chatlari |
| `GET chats/{id}/` | bitta chat (oxirgi xabari bilan) |
| `POST chats/` | mijozga chat yaratish |
| `DELETE chats/{id}/` | chatni o'chirish |
| `GET messages/?chat={id}` | chatdagi xabarlar |
| `POST messages/` | **javob yozish** (JSON yoki multipart) |
| `GET / PATCH / PUT / DELETE messages/{id}/` | bitta xabar |

Swagger: `/swagger/admin/` → **chats**, **messages**.

> Chat — mijozning qo'llab-quvvatlash yozishmasi. Mijoz ilova / saytdan yozadi (`POST /api/v1/base/chat/` — [mobile hujjati](../mobile/chat.md)) va uning har xabari **xodimlar Telegram guruhiga** tushadi. Admin panelning vazifasi — o'sha yozishmalarni ko'rish va javob berish: javob = `POST messages/`. Chatning o'zida tahrirlanadigan maydon yo'q, shuning uchun `PATCH chats/{id}/` yo'q.

---

## Chat obyekti

```json
{
  "id": 14,
  "customer": { "id": 51, "full_name": "Olim Karimov", "phone_number": "+998901234567" },
  "last_message": {
    "id": 902,
    "message": "Buyurtmam qachon keladi?",
    "image": null,
    "is_answer": false,
    "created_at": "2026-10-22T11:12:03.114820"
  },
  "messages_count": 7,
  "created_at": "2026-10-19T08:00:11.004120",
  "updated_at": "2026-10-19T08:00:11.004120"
}
```

| Maydon | Izoh |
| --- | --- |
| `customer` | mijoz qisqa ko'rinishda; **`null` = mehmon chati** (brauzerdagi `chat_token` cookie bilan aniqlanadi, tokenning o'zi API'da ko'rsatilmaydi) |
| `last_message` | oxirgi xabar (`is_answer: false` = mijozdan, `true` = operator javobi); xabar yo'q chatda `null` |
| `messages_count` | chatdagi xabarlar soni |

Hammasi faqat o'qiladi (`customer` dan boshqasi) — chatda o'zgartiriladigan narsa yo'q.

---

## Ro'yxat

`GET chats/?page=&page_size=` (default 20, max 100)

Default tartib — **oxirgi faollik bo'yicha** (`-last_activity_at`, so'ng `-id`): yangi xabar kelgan chat tepada. `last_activity_at` = oxirgi xabar vaqti, xabar bo'lmasa chat yaratilgan vaqt.

| Filtr | Qiymat | Nima qiladi |
| --- | --- | --- |
| `unanswered` | `true` / `false` | `true` = oxirgi xabar **mijozdan** (javob kutilmoqda) |
| `is_guest` | `true` / `false` | `true` = mijozga bog'lanmagan (mehmon) chatlar |
| `customer` | mijoz id | bitta mijozning chati |
| `from_activity`, `to_activity` | `YYYY-MM-DD` | oxirgi faollik sanasi bo'yicha |

- Qidiruv: `?search=` — mijozning ismi va telefon raqami bo'yicha
- Tartib: `?ordering=` `id`, `created_at`, `last_activity_at`, `messages_count` (teskari: `-messages_count`)

Ishchi navbat uchun: `GET chats/?unanswered=true` (eng kutib qolgani oxirida — `?ordering=last_activity_at`).

> Xabari umuman yo'q chat **javobsiz hisoblanmaydi** (`unanswered=true` ga tushmaydi): javob kutayotgan mijoz yo'q.

---

## Kartochkalar

`GET chats/stats/` — paginatsiyasiz, **ro'yxatning o'sha filtrlari bilan** ishlaydi (masalan `chats/stats/?is_guest=true`).

```json
{ "total": 128, "unanswered": 6, "guests": 41 }
```

| Maydon | Izoh |
| --- | --- |
| `total` | chatlar soni |
| `unanswered` | oxirgi xabari mijozdan bo'lganlari |
| `guests` | mijozga bog'lanmagan (mehmon) chatlar |

---

## Chat yaratish va o'chirish

`POST chats/` — mijozga bo'sh chat ochadi (`201` + obyekt):

```json
{ "customer": 51 }
```

`{"customer": {"id": 51}}` ko'rinishi ham qabul qilinadi.

- `customer` **majburiy** — admin paneldan mehmon chati yaratib bo'lmaydi (mehmon chatini faqat brauzerning o'zi `chat_token` bilan ochadi).
- Bitta mijozga **bitta chat**: mijozda chat bo'lsa → `400`, `{"customer": ["This customer already has a chat."]}`. Sababi: client API mijozning chatini `.first()` bilan o'qiydi, ikkinchi chat ko'rinmay qolardi.
- Amalda chat yaratish kerak bo'lmaydi: mijoz yozgan zahoti chat o'zi paydo bo'ladi. Bu endpoint operator suhbatni birinchi boshlashi uchun.

`DELETE chats/{id}/` → `204`, body yo'q. Chat bilan birga **uning hamma xabari** o'chadi (CASCADE), lekin xabarlarga biriktirilgan **rasm fayllari diskda qoladi** — faylni o'chirish faqat `DELETE messages/{id}/` da bor.

---

## Xabarlar

`GET messages/?chat={id}` — default tartib `-created_at` (yangisi birinchi). Suhbat ko'rinishi uchun `?ordering=created_at`.

```json
{
  "id": 902,
  "chat": { "id": 14 },
  "message": "Buyurtmam qachon keladi?",
  "image": null,
  "is_answer": false,
  "created_at": "2026-10-22T11:12:03.114820",
  "updated_at": "2026-10-22T11:12:03.114820"
}
```

| Maydon | Izoh |
| --- | --- |
| `chat` * | qaysi chat (`{"id": 14}` yoki `14`); yaratilgandan keyin **o'zgartirilmaydi** |
| `message` | matn |
| `image` | rasm (`POST` / `PATCH` da multipart) |
| `is_answer` | faqat o'qiladi: `true` = operator javobi, `false` = mijozning xabari |

| Filtr | Qiymat |
| --- | --- |
| `chat` | chat id |
| `is_answer` | `true` = javoblar, `false` = mijoz xabarlari |
| `from_created`, `to_created` | `YYYY-MM-DD` |

Qidiruv: `?search=` (`message` matni bo'yicha) — hamma chatlar ichidan xabar izlash uchun.

### Javob yozish

`POST messages/` → `201` + obyekt:

```json
{ "chat": 14, "message": "Ertaga kuryer bog'lanadi." }
```

- `is_answer` **avtomatik `true`** bo'ladi — bu endpoint orqali faqat operator javobi yoziladi, yuborilgan `is_answer` e'tiborga olinmaydi.
- `message` yoki `image` dan **kamida bittasi** bo'lishi shart (ikkisi ham bo'sh → `400`).
- Rasm bilan: `multipart/form-data`, `chat=14` + `image=<fayl>` (+ `message=`).

### Tahrirlash va o'chirish

- `PATCH messages/{id}/` — **faqat operator javobini** tahrirlash mumkin; mijozning xabariga → `400` (`{"detail": "Customer messages can't be edited."}`). `chat` ni o'zgartirishga ham `400`.
- `DELETE messages/{id}/` → `204`; biriktirilgan rasm fayli ham diskdan o'chadi.

---

## Boshqa sahifalar bilan bog'liqligi

| Nima | Qayerda |
| --- | --- |
| "Javobsiz chatlar" kartochkasi | `GET dashboard/` → `unanswered_chats` ([dashboard.md](dashboard.md)) |
| "Bugungi ishlar" diqqat qatori | `GET today/` → `unanswered_chats`, havolasi `chats/?unanswered=true` ([today.md](today.md)) |
| Mijoz akkaunti o'chirilganda | chat ham o'chadi ([mobile/delete_account.md](../mobile/delete_account.md)) |

---

## Xatolar

Oddiy DRF formatida (klient API'dagi `{"ok", "error_code"}` o'rami yo'q). Xabar matnlari tilga bog'liq, shuning uchun matnga emas, HTTP status va maydon nomiga tayaning.

| Holat | HTTP | Body |
| --- | --- | --- |
| Token yo'q yoki yaroqsiz | 401 | `{"detail": "..."}` |
| `POST chats/` — `customer` yuborilmadi | 400 | `{"customer": [...]}` |
| `POST chats/` — mijozda chat bor | 400 | `{"customer": ["This customer already has a chat."]}` |
| `POST messages/` — matn ham, rasm ham yo'q | 400 | `{"message": ["Send a message text or an image."]}` |
| Mijozning xabarini tahrirlash | 400 | `{"detail": "Customer messages can't be edited."}` |
| Xabarning chatini o'zgartirish | 400 | `{"chat": ["Can't be changed after creation."]}` |
| Mavjud bo'lmagan `id` | 404 | `{"detail": "..."}` |
| `PATCH chats/{id}/` | 405 | chatda tahrirlanadigan maydon yo'q |

---

## Eslatmalar

- **Operator javob berganda mijozga xabar bormaydi**: na FCM push, na Telegram. Mijoz ilovani o'zi ochib ko'radi. (Teskari tomoni bor: mijozning xabari Telegram guruhiga tushadi.)
- **O'qilgan / o'qilmagan holati yo'q** — modelda bunday maydon yo'q. "Javob kutilmoqda" ni faqat `unanswered` filtri bildiradi.
- **Realtime yo'q** (websocket yo'q): panel ro'yxatni o'zi qayta so'rab turishi kerak.
- **Mehmon chati mijozga ulanmaydi**: mehmon keyin tizimga kirsa, eski (cookie'li) chati alohida qolib ketadi — panelda ikki chat ko'rinadi, biri `customer: null`.
- Chat `customer` ga `SET_NULL` bilan bog'langan: mijoz o'chirilsa chat qolib, mehmon chatiga aylanadi.
