# Related products, alternatives, cart cross-sell

Two endpoints, no auth required:

| Endpoint | Where | |
|---|---|---|
| `GET /api/v1/products/<id>/links/` | product page | "Bought together" + "Alternatives" blocks |
| `GET /api/v1/cart/cross-sell/` | cart | "Don't forget" block |

The links are picked by the content team in the admin panel. Every list holds **at most 10** products and only
the ones that can be bought now: active, with a price, an image and stock. **An empty list = hide the block.**

Products have the same shape as in [`products/`](products_list.md) (`ProductSerializer`): `in_cart`,
`in_cart_quantity`, `is_favourite` work as there — send the `cart_token` / `favourite_token` cookies and
`Authorization` as usual.

## Product page

`GET /api/v1/products/<id>/links/` — call it together with `GET products/<id>/` (product card).

```json
{
  "result": {
    "related": [ { "id": 578, "name": "...", "price": 47610.0, "images": [ ... ], ... } ],
    "alternatives": [ { "id": 574, ... } ],
    "alternatives_source": "manual"
  },
  "ok": true
}
```

| Field | |
|---|---|
| `related` | bought together with the product (tile adhesive for a tile). Picked by hand only — most products have none: hide the block |
| `alternatives` | can be bought instead of the product |
| `alternatives_source` | `manual` — picked by hand; `category` — none picked (or none of them can be bought now), so these are popular products of the same category; `null` — `alternatives` is empty |

`alternatives_source` lets the app name the block: e.g. "Analoglar" for `manual`, "O'xshash mahsulotlar" for
`category`. Other variants of the same product (sizes, colours — `variant_groups` of the product card) never
come as alternatives.

Errors: an inactive / unknown product → `404` (as `products/<id>/`).

## Cart

`GET /api/v1/cart/cross-sell/` — call it when the cart screen opens and after the cart changes.

```json
{ "result": [ { "id": 577, ... }, { "id": 573, ... } ], "ok": true }
```

- The cart = the logged-in customer's one, otherwise the one of the `cart_token` cookie; no cart → `[]`.
- Order: the first pick of every cart product (the product added last goes first), then the second picks, and so
  on — so every cart product gets its best match near the start.
- Products already in the cart are left out, a product picked for two cart products comes once.
- After "add to cart" from this block, request it again: the added product leaves the list.
