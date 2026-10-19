# PRO customers and their projects

## PRO status

PRO = the old **prorab**: `Customer.role` `prorab` (PRO) / `user` (not PRO) — no new field, existing prorab customers
are PRO as they are.

- Customers list / detail (`/api/v1/admin/customers/`) show `role` as before; filter `?role=prorab`;
  `customers/stats/` → `b2b` = PRO count. `role` is **read-only** in the CRUD now (`POST` / `PATCH customers/`
  ignore it) — it changes only through the endpoint below, so every change is in the history.
- `POST /api/v1/admin/customers/<id>/role/` — give / take away PRO:

  ```json
  { "role": "user", "reason": "Shartnoma tugadi" }
  ```

  `reason` is required when PRO is taken away (`prorab` → `user`), optional when given. The same role as now → 400.
  Answer = the customer detail. Any staff account can do it.
- `GET /api/v1/admin/customers/<id>/role-history/` — every change, newest first, paginated:
  `id, old_value, new_value, changed_by {id, username, full_name}, reason, created_at`. Changes made before this
  endpoint (registration, profile edits) are not in it.

Taking PRO away keeps the customer's projects and links — the app just hides them; giving it back shows them again.
Every order keeps the role it was placed with (`Order.role_at_order`, null for older orders).

## Projects (read-only)

`GET /api/v1/admin/pro-projects/` — projects of every customer (also of the ones that are no longer PRO).
Filters `customer`, `status` (`active` / `archived`), `has_items`; search by project name, address, customer name /
phone; ordering `id`, `name`, `created_at`, `updated_at`, `items_count`.

```json
{
  "id": 7, "customer": { "id": 15, "full_name": "Ali", "phone_number": "+998901234567", "role": "prorab" },
  "name": "Chilonzor uy", "address": "Chilonzor 9", "comment": "", "status": "active", "archived_at": null,
  "items_count": 12, "orders_count": 3, "created_at": "...", "updated_at": "..."
}
```

`GET /api/v1/admin/pro-projects/<id>/` adds `expenses` (`goods`, `delivery`, `total`, `orders_count`,
`items_count`, all time) and `categories` (`id`, `name`, `goods`) — the numbers the customer sees
(rules: [docs/mobile/pro_projects.md](../mobile/pro_projects.md#expenses)).

Editing an order's items in `orders/` keeps the project link of the products that stay in the order.
