# Filter pages — changes (brand × category pages)

The full contract: [`filter_pages.md`](filter_pages.md). What changed:

1. **New kind of page — brand × category / sub category** ("сухие смеси Knauf"). Every page now has
   `level` = `item_category` | `sub_category` | `category`. The old pages are all `item_category`.
2. `GET filter-pages/` and `GET filter-pages/<slug>/`:
   - new `level`;
   - `item_category` is **`null`** on a `sub_category` / `category` page (it was always set);
   - the list has `breadcrumbs` now (category → … → the page's level, `id` / `name` / `slug` / `level`) — enough
     to build the page URL for the sitemap; the detail's `breadcrumbs` end at the page's level (2 or 1 rows on
     the new pages).
3. `GET filter-pages/` also takes `?sub_category=<id>` and `?category=<id>` (pages of exactly that level).
4. `product_filter` of a new page: `{ "sub_category": 155, "brand": 31, "filters": {} }` (or `category`) — send
   it to `POST product/filter/` as before.
5. `POST filter-pages/resolve/`: `item_category` is no longer required — send the listing's level
   (`item_category`, `sub_category` or `category`; the most specific one counts) + `brand` + `filters`; no level
   → 400. A sub category listing with a brand picked can now get a `slug`.
6. Recommended URL: `/catalog/<breadcrumb slugs>/<slug>` for every level (see the main doc).
