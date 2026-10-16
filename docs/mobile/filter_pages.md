# Filter landing pages (SEO)

Separate pages for the filter combinations people search for: brand + product type ("перфоратор Makita"),
a size ("кабель ВВГ 3×2.5"), a pack ("цемент М400 50 кг"). The list is agreed by the SEO / content team and
kept in the admin panel; any other filter combination has no page and **stays closed to search engines**.

Three endpoints, no auth required (`Accept-Language: uz | ru`, default ru):

| Endpoint | Where |
|---|---|
| `GET /api/v1/filter-pages/` | sitemap; links on the item category page (`?item_category=<id>`) |
| `GET /api/v1/filter-pages/<slug>/` | the page itself |
| `POST /api/v1/filter-pages/resolve/` | a filtered listing: is there a page for exactly these filters? |

A page is **open** while it is active in the admin panel and has **at least 3 active products** (counted every
hour); a closed page is missing from the list and its detail returns 404. The slug is ASCII, unique, the same
in both languages; the URL of the page on the site (e.g. `/catalog/<item_category.slug>/<slug>`) is up to the
site.

## List (sitemap)

`GET /api/v1/filter-pages/` — every open page, most searched first, not paginated (≤ 400).
`?item_category=<id>` — only the pages of that item category ("Popular selections" links on its page).

```json
{
  "result": [
    {
      "slug": "perforator-makita",
      "title": "Перфораторы Makita",
      "item_category": { "id": 452, "slug": "perforatorlar" },
      "brand": 24,
      "products_count": 18,
      "updated_at": "2026-10-16T13:27:18"
    }
  ],
  "ok": true
}
```

`updated_at` = `<lastmod>` of the sitemap.

## Page

`GET /api/v1/filter-pages/<slug>/`

```json
{
  "result": {
    "id": 1,
    "slug": "perforator-makita",
    "title": "Перфораторы Makita",
    "meta_title": "Перфораторы Makita — купить в Ташкенте",
    "meta_description": "…",
    "text": "300–500 characters about the selection…",
    "item_category": { "id": 452, "name": "Перфораторы", "slug": "perforatorlar" },
    "brand": { "id": 24, "name": "Makita" },
    "breadcrumbs": [
      { "id": 5, "name": "Инструменты", "slug": "asboblar", "level": "product_category" },
      { "id": 155, "name": "Электроинструмент", "slug": "elektr-asboblar", "level": "product_sub_category" },
      { "id": 452, "name": "Перфораторы", "slug": "perforatorlar", "level": "product_item_category" }
    ],
    "product_filter": { "item_category": 452, "brand": 24, "filters": { "3334": ["SDS-plus"] } },
    "products_count": 18,
    "updated_at": "2026-10-16T13:27:18"
  },
  "ok": true
}
```

| Field | |
|---|---|
| `title` | H1 |
| `meta_title` | `<title>`; the H1 when the content team left it empty |
| `meta_description` | the start of `text` (≈160 characters) when left empty |
| `text` | plain text, may be empty (render nothing then) |
| `brand` | `null` when the page is not about a brand |
| `product_filter` | body for the products, see below |

404 (`error_code` 4) — no such slug, or the page is closed now (fewer than 3 products, switched off): show
the item category page or a 404, but do not index it.

### Products of the page

Same listing as the catalog: `POST /api/v1/product/filter/` with `product_filter` as the body, plus `page`,
`page_size`, `sort_by` as usual. The response brings `available_filters` / `quick_filters` too — the page's own
filters come back as picked (`filters` keys = attribute ids, values = `value` of the available filters).

```json
{ "item_category": 452, "brand": 24, "filters": { "3334": ["SDS-plus"] }, "page": 1, "page_size": 20 }
```

## Filtered listing → page

When the customer picks filters on an item category page, ask whether this exact combination has a page:

`POST /api/v1/filter-pages/resolve/`

```json
{ "item_category": 452, "brand": 24, "filters": { "3334": ["SDS-plus"] } }
```

```json
{ "result": { "slug": "perforator-makita" }, "ok": true }
```

- `slug` → the listing has a page: link to it / use it as the canonical URL.
- `null` → no page: the filtered URL gets `noindex` (only the agreed list is open to search engines).

The match is exact: the same item category, the same brand (or none) and the same set of filters — the order of
keys and values does not matter. One more filter (a price range too) → another combination → `null`. Send only
`item_category`, `brand`, `filters` (no `page`, `sort_by`, `q`); a search query (`q`) never has a page.
