# Products list (random)

`GET /api/v1/products/` — active products in random order, paginated. No auth required
(with a token / `cart_token` / `favourite_token` cookie the cart and favourite flags are filled).

## Query params

| Param | Type | Default | |
|---|---|---|---|
| `page` | int | 1 | |
| `page_size` | int | 10 | |
| `seed` | int (0 … 2147483647) | generated | fixes the random order |

## How to page

1. First request **without** `seed`: `GET /api/v1/products/?page=1&page_size=20`.
2. Take `result.seed` from the response.
3. Send it with every next page: `?page=2&page_size=20&seed=1939760476`.

With the same `seed` the order is the same, so pages don't repeat or skip products.
A new order (pull-to-refresh, new session) = a request without `seed`.

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
    "seed": 1939760476
  },
  "ok": true
}
```

Invalid `seed` → 400, `error_code` validation failed.
