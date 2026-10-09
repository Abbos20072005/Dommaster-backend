# Home page blocks (site / app)

The home page is assembled in the admin panel ("Bosh sahifa"): which blocks, in what order, on which platform.
The client asks for the published layout and renders the blocks top to bottom.

| Endpoint | |
|---|---|
| `GET /api/v1/home/` | published blocks, in page order |
| `GET /api/v1/home/blocks/{id}/products/` | products of a product block, paginated |

No auth required. Language: `Accept-Language: uz | ru | en` (default `ru`; an empty translation falls back to `ru`).

## `GET /api/v1/home/`

| Param | Values | |
|---|---|---|
| `platform` | `site`, `ios`, `android` | blocks (and banners) of this platform only; without it — all |

Only the blocks that have something to show are returned. A block is left out when it is hidden in the admin panel,
turned off for the platform, its source is empty (no active banners, no brands marked "on the home page", ...)
or it has fewer products than the minimum set in the admin panel. So: **render what you get, never an empty block**.

```json
{
  "result": [
    {
      "id": 1,
      "type": "slider",
      "title": "Asosiy slayder",
      "banners": [
        {
          "id": 2,
          "title": "Knauf kuzgi aksiya",
          "desktop_image": "https://.../media/banner/desktop/b1.webp",
          "mobile_image": "https://.../media/banner/mobile/b1.webp",
          "placement": "site_home",
          "link_type": "url",
          "link": "https://dommaster.uz/ru",
          "page": "",
          "content_type_info": null
        }
      ],
      "banner": null,
      "categories": null,
      "brands": null,
      "pages": null,
      "badge": null,
      "sale": null,
      "days": null,
      "products_count": null
    },
    {
      "id": 9,
      "type": "badge_products",
      "title": "Podborka \"Hit\"",
      "banners": null,
      "banner": null,
      "categories": null,
      "brands": null,
      "pages": null,
      "badge": { "id": 7, "name": "Xit", "color": "#2563EB" },
      "sale": null,
      "days": null,
      "products_count": 90
    }
  ],
  "ok": true
}
```

Every block has the same keys; the ones its `type` does not use are `null`.

| `type` | What to render | Data |
|---|---|---|
| `slider` | banner carousel | `banners` — same objects as `GET /api/v1/base/banner/` |
| `banner` | one banner | `banner` — same object |
| `categories` | top-level categories | `categories`: `[{id, name, icon, image}]`, already ordered |
| `brands` | brands | `brands`: `[{id, name, image}]` |
| `pages` | links to pages (delivery, payment, ...) | `pages`: `[{title, path}]`, `path` is an internal path (`/delivery`) |
| `badge_products` | products of a tag | `badge`: `{id, name, color}`, `products_count`; products — see below |
| `sale_products` | products of a sale | `sale`: `{id, name, discount_from, discount_to, image}`, `products_count`; products — see below |
| `new_products` | recently added products | `days`, `products_count`; products — see below |
| `bestsellers` | most sold products | `products_count`; products — see below |
| `all_products` | all products feed | `products_count`; products — see below |
| `content` | articles / videos | nothing embedded: `GET /api/v1/base/articles/`, `GET /api/v1/base/video/` |
| `adds_brands` | ad blocks ("Asosiy bo'limlar") | nothing embedded: `GET /api/v1/adds/brands/` |

`title` is the block heading (for `sale_products` show it instead of the sale name).
An unknown `type` (added later) should be skipped, not crash the page.

The response is cached for up to 5 minutes; a "publish" in the admin panel resets it at once. A banner / category
edited in the admin panel may therefore show up with a delay of a few minutes.

## `GET /api/v1/home/blocks/{id}/products/`

Products of a product block (`badge_products`, `sale_products`, `new_products`, `bestsellers`, `all_products`).
Products hidden by the admin rules (out of stock) are already excluded. With a token / `cart_token` /
`favourite_token` cookie the cart and favourite flags are filled.

| Param | Type | Default | |
|---|---|---|---|
| `page` | int | 1 | |
| `page_size` | int | 10 | |
| `seed` | int (0 … 2147483647) | generated | `all_products` only: fixes the random order |

```json
{
  "result": {
    "totalElements": 90,
    "totalPages": 9,
    "size": 10,
    "number": 1,
    "numberOfElements": 10,
    "first": true,
    "last": false,
    "empty": false,
    "content": [ { "id": 672, "name": "...", "price": 125000.0 } ],
    "seed": null
  },
  "ok": true
}
```

`content` — the same product objects as in `GET /api/v1/products/`.

Order: `bestsellers` — by units sold, `new_products` — newest first, `badge_products` / `sale_products` — newest first.
`all_products` — random order, paged exactly like [`products/`](products_list.md): the first request goes without
`seed`, take `result.seed` from the response and send it with the next pages. For the other blocks `seed` is `null`.

`404` (`error_code: 4`) — the block is not published, is hidden, is not a product block, or has nothing to show.

## Notes

- The old endpoints (`main/`, `most/sold/`, `sales/main/`, `brands/`, ...) keep working unchanged, old app
  versions are not affected.
- Until brands are marked "on the home page" in the admin panel, the `brands` block is not returned.
