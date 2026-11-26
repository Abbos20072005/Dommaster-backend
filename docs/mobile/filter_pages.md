# Filter landing pages (SEO)

Separate pages for the filter combinations people search for: brand + product type ("перфоратор Makita"),
a size ("кабель ВВГ 3×2.5"), a pack ("цемент М400 50 кг"), and **brand × category** ("сухие смеси Knauf" —
a brand inside a whole category or sub category). The list is agreed by the SEO / content team and
kept in the admin panel; any other filter combination has no page and **stays closed to search engines**.

Three endpoints, no auth required (`Accept-Language: uz | ru`, default ru):

| Endpoint | Where |
|---|---|
| `GET /api/v1/filter-pages/` | sitemap; links on a category page (`?category=` / `?sub_category=` / `?item_category=<id>`) |
| `GET /api/v1/filter-pages/<slug>/` | the page itself |
| `POST /api/v1/filter-pages/resolve/` | a filtered listing: is there a page for exactly these filters? |

A page is **open** while it is active in the admin panel and has **at least 3 active products** (counted every
hour); a closed page is missing from the list and its detail returns 404. The slug is ASCII, unique, the same
in both languages.

**Level** (`level`) — every page belongs to exactly one catalog level:

| `level` | What | Filters |
|---|---|---|
| `item_category` | brand and / or attribute filters inside an item category ("перфоратор Makita", "кабель ВВГ 3×2.5") | yes |
| `sub_category` | a brand in a whole sub category ("сухие смеси Knauf") | no, brand always set |
| `category` | a brand in a whole top category | no, brand always set |

**URL on the site** (the site's choice; recommended): `/catalog/<breadcrumb slugs>/<slug>` — the page sits under
its level in the catalog tree, e.g. `/catalog/instrumenty/elektroinstrument/perforatory/perforator-makita`,
`/catalog/stroitelnye-materialy/suhie-smesi/suhie-smesi-knauf`. A page slug stands where a child category slug
may stand, so resolve the last segment as a child category first, then as a filter page (`filter-pages/<slug>/`).
The list carries the slug and the breadcrumb slugs, nothing else is needed to build the sitemap.

## List (sitemap)

`GET /api/v1/filter-pages/` — every open page, most searched first, not paginated (≤ 400).
`?item_category=<id>`, `?sub_category=<id>`, `?category=<id>` — only the pages of exactly that level and id
("Popular selections" links on its page; `?sub_category=` does not bring the item category pages below it).

```json
{
  "result": [
    {
      "slug": "perforator-makita",
      "title": "Перфораторы Makita",
      "level": "item_category",
      "item_category": { "id": 452, "slug": "perforatorlar" },
      "breadcrumbs": [
        { "id": 5, "name": "Инструменты", "slug": "asboblar", "level": "product_category" },
        { "id": 155, "name": "Электроинструмент", "slug": "elektr-asboblar", "level": "product_sub_category" },
        { "id": 452, "name": "Перфораторы", "slug": "perforatorlar", "level": "product_item_category" }
      ],
      "brand": 24,
      "products_count": 18,
      "updated_at": "2026-10-16T13:27:18"
    }
  ],
  "ok": true
}
```

`updated_at` = `<lastmod>` of the sitemap. `item_category` is `null` on a `category` / `sub_category` page;
`breadcrumbs` = category → … → the page's level (2 rows on a sub category page, 1 on a category page).

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
    "level": "item_category",
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
| `level` | `item_category` / `sub_category` / `category` |
| `item_category` | `null` on a `category` / `sub_category` page |
| `brand` | `null` when the page is not about a brand (only on an `item_category` page) |
| `breadcrumbs` | category → … → the page's level |
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

A sub category / category page carries its own level key and empty `filters`:

```json
{ "sub_category": 155, "brand": 31, "filters": {}, "page": 1, "page_size": 20 }
```

## Filtered listing → page

When the customer picks filters (or a brand) on a category page of any level, ask whether this exact combination
has a page:

`POST /api/v1/filter-pages/resolve/`

```json
{ "item_category": 452, "brand": 24, "filters": { "3334": ["SDS-plus"] } }
```

```json
{ "result": { "slug": "perforator-makita" }, "ok": true }
```

- `slug` → the listing has a page: link to it / use it as the canonical URL.
- `null` → no page: the filtered URL gets `noindex` (only the agreed list is open to search engines).

Send the listing's level — `item_category`, `sub_category` or `category` (several may be sent, the most specific
one counts) — plus `brand` and `filters`; at least one level is required (400 otherwise). A sub category listing
with only a brand picked: `{ "sub_category": 155, "brand": 31 }`.

The match is exact: the same level and id, the same brand (or none) and the same set of filters — the order of
keys and values does not matter. One more filter (a price range too) → another combination → `null`; filters on
a sub category / category listing never have a page. Send no `page`, `sort_by`, `q`; a search query (`q`) never
has a page.
