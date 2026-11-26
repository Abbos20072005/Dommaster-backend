# Filtr sahifalari — o'zgarishlar (brend × kategoriya sahifalari)

To'liq hujjat: [`filter_pages.md`](filter_pages.md). Nima o'zgardi:

1. **Yangi turdagi sahifa — brend × kategoriya / subkategoriya** ("Knauf quruq aralashmalar"). Obyektda yangi
   maydonlar: `level` (faqat o'qish uchun: `item_category` / `sub_category` / `category`), `category`,
   `sub_category` (`{"id"}` yoki id). Eski sahifalarning hammasi `item_category`.
2. `item_category` endi majburiy emas: uchta darajadan **aynan bittasi** yuboriladi. PATCH'da birortasi
   yuborilsa, sahifa shu darajaga o'tadi (qolganlari `null` bo'ladi).
3. `sub_category` / `category` sahifasida brend majburiy (`400`, `brand` kalitida), filtrlar yo'q
   (`filters: {}`; bo'lsa `400`).
4. Ro'yxatda yangi filtrlar: `level`, `category`, `sub_category`.
5. Formada: avval darajani tanlash (predmet kategoriya / subkategoriya / kategoriya), keyin shu kategoriya;
   filtrlar bloki faqat predmet kategoriyada ko'rinadi.
