# PRO customers and their projects

## PRO status

`Customer.account_type`: `customer` (default) or `pro`. Not related to `role` (`user` / `prorab`) — existing prorab
accounts were **not** made PRO.

- Customers list / detail (`/api/v1/admin/customers/`) show `account_type`; filter `?account_type=pro`;
  `customers/stats/` has `pro`. The field is read-only in the CRUD.
- `POST /api/v1/admin/customers/<id>/account-type/` — give / take away PRO:

  ```json
  { "account_type": "customer", "reason": "Shartnoma tugadi" }
  ```

  `reason` is required when PRO is taken away (optional when given). The same value as now → 400. Answer = the
  customer detail. Any staff account can do it.
- `GET /api/v1/admin/customers/<id>/account-type-history/` — every change, newest first, paginated:
  `id, old_value, new_value, changed_by {id, username, full_name}, reason, created_at`.

Taking PRO away keeps the customer's projects and links — the app just hides them; giving it back shows them again.
Every order keeps the account type it was placed with (`Order.account_type_at_order`, null for older orders).

## Projects (read-only)

`GET /api/v1/admin/pro-projects/` — projects of every customer (also of the ones that are no longer PRO).
Filters `customer`, `status` (`active` / `archived`), `has_items`; search by project name, address, customer name /
phone; ordering `id`, `name`, `created_at`, `updated_at`, `items_count`.

```json
{
  "id": 7, "customer": { "id": 15, "full_name": "Ali", "phone_number": "+998901234567", "account_type": "pro" },
  "name": "Chilonzor uy", "address": "Chilonzor 9", "comment": "", "status": "active", "archived_at": null,
  "items_count": 12, "orders_count": 3, "created_at": "...", "updated_at": "..."
}
```

`GET /api/v1/admin/pro-projects/<id>/` adds `expenses` (`goods`, `delivery`, `total`, `orders_count`,
`items_count`, all time) and `categories` (`id`, `name`, `goods`) — the numbers the customer sees
(rules: [docs/mobile/pro_projects.md](../mobile/pro_projects.md#expenses)).

Editing an order's items in `orders/` keeps the project link of the products that stay in the order.
