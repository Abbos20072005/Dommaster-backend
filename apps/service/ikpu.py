"""IKPU (MXIK) codes for the fiscal receipt.

The code lives on the product card (`Product.ikpu_code`, plus the optional `package_code`) and is copied to the
order item when the item is created. While the order is pending a manager may set / change an item's code; the
product card takes the new code too, and so do the items of the other pending orders that still carry the old
one - an order that left Pending keeps its codes. An order leaves Pending (for anything but Canceled) only when
every item has a code. Every change is logged in `ProductCodeChange`."""
from .models import Order, OrderItem, ProductCodeChange

CODE_FIELDS = (ProductCodeChange.IKPU, ProductCodeChange.PACKAGE)


def is_confirmation(old_status, new_status):
    """Leaving Pending for Confirmed, or for a later status when Confirmed is skipped."""
    return old_status == Order.PENDING and new_status not in (Order.PENDING, Order.CANCELED)


def missing_items(order):
    """Items of the order without an IKPU code, oldest first."""
    return list(OrderItem.objects.filter(order=order, ikpu_code="").select_related("product").order_by("id"))


def _save_product(product, changes, exclude_order_id=None):
    old_ikpu = product.ikpu_code
    for field, value in changes.items():
        setattr(product, field, value)
    product.save(update_fields=list(changes))
    if ProductCodeChange.IKPU in changes:
        items = OrderItem.objects.filter(product=product, order__status=Order.PENDING, ikpu_code=old_ikpu)
        if exclude_order_id:
            items = items.exclude(order_id=exclude_order_id)
        items.update(ikpu_code=changes[ProductCodeChange.IKPU])


def set_product_codes(product, codes, user=None):
    """Product card: `codes` = {field of CODE_FIELDS: value, "" = no code}; only the changed ones are saved."""
    changes = {field: value for field, value in codes.items() if getattr(product, field) != value}
    if not changes:
        return
    ProductCodeChange.objects.bulk_create(
        ProductCodeChange(product=product, field=field, old_value=getattr(product, field), new_value=value,
                          source=ProductCodeChange.SOURCE_PRODUCT, changed_by=user)
        for field, value in changes.items()
    )
    _save_product(product, changes)


def set_item_codes(order, codes, user=None):
    """Order items of a pending order: `codes` = {OrderItem: IKPU code}. A changed item code goes to the product
    card as well."""
    for item, code in codes.items():
        if item.ikpu_code == code:
            continue
        ProductCodeChange.objects.create(
            product=item.product, order=order, field=ProductCodeChange.IKPU, old_value=item.ikpu_code,
            new_value=code, source=ProductCodeChange.SOURCE_ORDER, changed_by=user,
        )
        item.ikpu_code = code
        item.save(update_fields=["ikpu_code"])
        if item.product.ikpu_code != code:
            _save_product(item.product, {ProductCodeChange.IKPU: code}, exclude_order_id=order.pk)
