# Products list

`GET /api/v1/products/` — active products, paginated. No auth required
(with a token / `cart_token` / `favourite_token` cookie the cart and favourite flags are filled).

**Order is stable by default** (`-created_at, -id`, newest first) — the same request repeated,
or the next page, never repeats or skips a product. Random order is opt-in (`random=true`), for a
shuffled catalog view; it still needs the `seed` round-trip described below (BLD launch audit A-14 —
a client paginating the old always-random order without carrying `seed` saw products repeat and others
never show up).

## Query params

| Param | Type | Default | |
|---|---|---|---|
| `page` | int | 1 | |
| `page_size` | int | 10 | |
| `random` | bool | false | `true` = random order (first page only; generates a seed) |
| `seed` | int (0 … 2147483647) | — | continues a random order from an earlier `random=true`/`seed` response; sending it implies random order |

## How to page

- **Stable (default)**: just page — `GET /api/v1/products/?page=1&page_size=20`, then `?page=2&page_size=20`, … `result.seed` is `null`.
- **Random**: first request with `random=true`: `GET /api/v1/products/?page=1&page_size=20&random=true`.
  Take `result.seed` from the response and send it with every next page: `?page=2&page_size=20&seed=1939760476`.
  With the same `seed` the order is the same, so pages don't repeat or skip products.
  A new shuffled order (pull-to-refresh, new session) = a request with `random=true` and no `seed`.

## Response

```json
{
  "result": {
    "totalElements": 7530,
    "totalPages": 377,
    "size": 20,
    "number": 1,
    "numberOfElements": 20,
    "first": true,
    "last": false,
    "empty": false,
    "content": [ { "id": 10149, "...": "same product object as in product/filter/" } ],
    "seed": null
  },
  "ok": true
}
```

Invalid `seed` → 400, `error_code` validation failed.
