# PRO: projects and expenses

A PRO customer splits what they buy between their projects (a house, an office, a client's flat) and sees what
each project cost. PRO is given by the staff in the admin panel — the customer can't turn it on.

All endpoints need `Authorization: Bearer <access token>` (no token → 401). A customer who is not PRO gets
**403**, `error_code` 34, on every `/api/v1/pro/` endpoint — use it to hide the PRO section.

## Is the customer PRO?

PRO = the old prorab: `GET /api/v1/auth/auth/me/` → `result.role` = `prorab` (`user` = not PRO), the same field as
before. It is read-only now: sending `role` to `PATCH /api/v1/auth/customer/update/` changes nothing — only the staff
set it.

When PRO is taken away the projects are kept, just hidden (403); when it is given back they come back as they were.

## Projects

| Endpoint | |
|---|---|
| `GET /api/v1/pro/projects/?status=active\|archived` | all projects, newest first (no `status` = both) |
| `POST /api/v1/pro/projects/` | create: `name` (required), `address`, `comment` → 201 |
| `GET /api/v1/pro/projects/<id>/` | one project |
| `PATCH /api/v1/pro/projects/<id>/` | change `name`, `address`, `comment` |
| `POST /api/v1/pro/projects/<id>/archive/` | to the archive |
| `POST /api/v1/pro/projects/<id>/restore/` | back from the archive |
| `DELETE /api/v1/pro/projects/<id>/` | delete → 204; only a project with no linked items, else **409** `error_code` 36 — offer "archive" instead |

```json
{
  "id": 7, "name": "Chilonzor uy", "address": "Chilonzor 9", "comment": "", "status": "active",
  "archived_at": null, "items_count": 12, "orders_count": 3,
  "created_at": "2026-10-19T12:00:00", "updated_at": "2026-10-19T12:00:00"
}
```

- `items_count` / `orders_count` count, like the expenses, only items of **paid, not canceled** orders — an item
  linked to an unpaid order shows up (in the counts, the summary and `items/`) once the order is paid. Delete still
  looks at every linked item: a project whose items are all unpaid has `items_count` 0 but answers 409.
- `name`: 3–100 characters (extra spaces are dropped). Two **active** projects can't have the same name
  (case does not matter) → 400, `error_code` 35. Archived projects don't count, so restoring one whose name is taken
  meanwhile → 400 (35) as well: rename one of them first.
- An archived project keeps its items and keeps counting in the expenses; nothing new can be linked to it.
- Someone else's project id → 404.

## Linking order items

`POST /api/v1/pro/orders/<order_id>/link/`

```json
{ "project_id": 7, "item_ids": [101, 102], "force": false }
```

- no `item_ids` = every item of the order. Item ids = `order_items[].id` of `GET /api/v1/order/<id>/`.
- an item already linked to **another** project → **409**, `error_code` 37, nothing changed:
  `detail.conflicting_item_ids` = those items. Ask the customer, then send the same request with `"force": true` —
  they are moved. Items already in this project are left as they are.
- canceled order → 400 (39), archived project → 400 (38), someone else's order or project → 404.
- 200 → `result` = `{ "id": <order id>, "order_items": [{ "id", "product_id", "quantity", "project": {"id", "name"} | null }] }`.

`POST /api/v1/pro/orders/<order_id>/unlink/` with `{ "item_ids": [...] }` (or `{}` for the whole order) removes
the project — same answer.

Orders placed before the customer became PRO (prorab) can be linked as well (temporary rule).

**Order detail** `GET /api/v1/order/<id>/`: every `order_items[]` has `project` — `{"id", "name"}` or `null`
(not linked, or the customer is not PRO).

**Not linked yet**: `GET /api/v1/pro/orders/unlinked/?page=&page_size=` — orders (not canceled) with at least one
item without a project, newest first, the usual page (`totalElements`, `content`, ...); a row:
`id, status, payment_status, total_price, created_at, items_count, unlinked_items_count`.

## Expenses

Counted: **paid** (`payment_status` = 2) and **not canceled** orders, by the order date. Every endpoint takes
`?from=YYYY-MM-DD&to=YYYY-MM-DD` (both optional, inclusive).

- `goods` of an item = price after the product discount at the time of the order × quantity, less the item's
  share of the promocode discount;
- `delivery` = the item's share of the order's delivery (pickup = 0);
- the promocode discount and the delivery are split between all items of the order in proportion to the item
  sums, so an order split between two projects is divided exactly — the projects add up to what was paid.

Money comes as strings with 2 decimals (`"241666.67"`).

`GET /api/v1/pro/dashboard/`

```json
{
  "totals": { "goods": "490000.00", "delivery": "25000.00", "total": "515000.00", "orders_count": 2, "items_count": 4 },
  "projects": [
    { "id": 7, "name": "Uy", "status": "active", "goods": "241666.67", "delivery": "20833.33", "total": "262500.00", "orders_count": 1, "items_count": 2 }
  ],
  "categories": [
    { "id": 3, "name": "Santexnika", "goods": "316000.00" },
    { "id": 5, "name": "Elektr", "goods": "174000.00" }
  ]
}
```

`projects` = every project (active and archived, zeros too). `categories` = top-level catalog category of the
product at the time it was linked, biggest first; they add up to `totals.goods`; `id: null` = product without a
category.

`GET /api/v1/pro/projects/<id>/summary/` → `{ "project": {...}, "totals": {...}, "categories": [...] }` — the same
for one project.

`GET /api/v1/pro/projects/<id>/items/?from=&to=&page=&page_size=` (default 20, max 100) — the linked items,
newest order first:

```json
{
  "id": 101, "order_id": 55, "order_created_at": "2026-10-01T10:00:00",
  "product": { "id": 578, "name": "...", "image": "https://..." },
  "category": { "id": 3, "name": "Santexnika" },
  "quantity": 2, "unit_price": "90000.00", "amount": "180000.00", "discount": "6000.00",
  "goods": "174000.00", "delivery": "15000.00", "total": "189000.00"
}
```
