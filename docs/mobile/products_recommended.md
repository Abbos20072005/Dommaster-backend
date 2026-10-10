# Products list (personal feed)

`GET /api/v1/products/recommended/` — the home feed for this visitor. Same request and response as
[`products/`](products_list.md), with a few extra fields. No auth required.

What comes in the feed: products of the item categories the visitor is interested in (what they bought, put
into the cart, added to favourites, searched for and viewed), mixed with popular products; after that the rest
of the catalog in random order, so the feed does not end early.

## Headers

| Header | |
|---|---|
| `Authorization` | optional; a logged-in customer gets the feed by their own history |
| `X-Device-Id` | the device id, the same value the app sends as `device_id` in `phone_auth`. The only identity of a visitor who is not logged in |
| cookies `cart_token`, `favourite_token` | as everywhere: cart / favourite flags, and the cart and favourites of a visitor who is not logged in count as signals |

**Send `X-Device-Id` with every request, not only this one.** The views and searches of a visitor who is not
logged in are collected from `GET products/<id>/` (product card opened) and `POST product/filter/` with `q`
(search). Without the header there is nothing to build their feed from and they get popular products.

## Query params

| Param | Type | Default | |
|---|---|---|---|
| `page` | int ≥ 1 | 1 | |
| `page_size` | int 1 … 100 | 10 | |
| `seed` | int (0 … 2147483647) | generated | fixes the feed |

Paging is the same as in `products/`: the first request goes without `seed`, take `result.seed` from the
response and send it with every next page. With the same `seed` pages neither repeat nor skip products, also
when the visitor adds something to the cart in between. Pull-to-refresh / a new session = a request without
`seed` (a new order of products).

## Response

```json
{
  "result": {
    "totalElements": 6912,
    "totalPages": 692,
    "size": 10,
    "number": 1,
    "numberOfElements": 10,
    "first": true,
    "last": false,
    "empty": false,
    "content": [
      { "id": 10149, "...": "same product object as in products/", "rec_source": "personal" }
    ],
    "seed": 1939760476,
    "feed_request_id": "0b9d6f6e-6f0f-5c5e-9d0a-3f1f0e3c7a11",
    "personalized": true
  },
  "ok": true
}
```

| Field | |
|---|---|
| `result.seed` | send it back with the next pages |
| `result.feed_request_id` | id of this feed: the same on all pages of one `seed`. Nothing to do with it yet — keep it with the shown products, it will be sent with clicks / add-to-cart later |
| `result.personalized` | `true` — the feed has products picked for this visitor; `false` — popular / random products only |
| `content[].rec_source` | where the product comes from, see below |

`rec_source`:

| Value | |
|---|---|
| `personal` | from the visitor's interest categories (and their sibling categories) |
| `cross_sell` | reserved: products linked by hand to what the visitor viewed / bought. Not sent yet |
| `popular` | most ordered products |
| `fallback` | the rest of the catalog in random order |

New values may be added: treat an unknown `rec_source` as a usual product, not as an error.

## What to rely on

- The response is never an error or an empty list because of the feed: a new visitor, a visitor without
  `X-Device-Id`, a switched-off feed or an internal failure all return products (`personalized=false`).
- **A page may be shorter than `page_size`** (a product was deactivated after the feed was built). The end of
  the feed is `result.last`, not a short page.
- The feed shows only products that are active, have a price, a picture and are in stock; products that are
  in the cart, or were bought in the last 14 days, are left out.
- A part of the visitors (a control group, 10% by default) always gets the random feed with
  `personalized=false` — this is how the effect of the feed is measured. A test account that never becomes
  personalized is probably in that group: ask the backend to set the group to 0 for the check.
- Invalid `seed` / `page` / `page_size` → 400, `error_code` validation failed.
