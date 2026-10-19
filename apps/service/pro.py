"""PRO projects (BLD-291..293): a PRO customer links order items to own projects and sees what each project cost.

Money is Decimal, in 0.01. An item costs `unit_price` (price after the product discount, kept at order time) × quantity;
the order's promocode discount and delivery are split between all items of the order in proportion to these sums
(`allocate`: whole cents, the rounding rest goes to the biggest remainders), so a split order adds up exactly.
Only paid (payment_status Paid) and not canceled orders are counted."""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.utils import timezone

from apps.authorization.models import Customer
from apps.service.models import Order, OrderItem, OrderItemProjectChange, Project
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes

# ORDER_STATUS / PAYMENT_STATUS / DELIVERY_TYPE
CANCELED = 4
PAID = 2
DELIVERY = 0

# Temporary rule (BLD-292): orders placed before the customer got PRO can be linked too.
# False = only orders placed as PRO (`Order.account_type_at_order`).
LINK_PRE_PRO_ORDERS = True

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value):
    return Decimal(str(value or 0)).quantize(CENT, ROUND_HALF_UP)


# --- access ---------------------------------------------------------------------------------------------------------

def pro_customer(request):
    """The request's customer when it is PRO, else 403 (projects of a former PRO stay in the db, hidden)."""
    customer = Customer.objects.filter(id=request.user.id).first()
    if not customer or not customer.is_pro:
        raise CustomApiException(error_code=ErrorCodes.PRO_REQUIRED)
    return customer


def get_project(customer, project_id):
    """Customer's own project; someone else's id answers 404 like a missing one."""
    project = Project.objects.filter(id=project_id, customer=customer).first()
    if not project:
        raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Project not found")
    return project


# --- projects -------------------------------------------------------------------------------------------------------

def clean_name(name):
    return " ".join((name or "").split())


def check_name_free(project):
    """Two active projects of one customer can't share a name (case-insensitive)."""
    if project.status != Project.ACTIVE:
        return
    taken = Project.objects.filter(customer_id=project.customer_id, status=Project.ACTIVE,
                                   name__iexact=project.name).exclude(pk=project.pk).exists()
    if taken:
        raise CustomApiException(error_code=ErrorCodes.PROJECT_NAME_TAKEN)


def save_project(project):
    check_name_free(project)
    try:
        with transaction.atomic():
            project.save()
    except IntegrityError:  # a concurrent request took the name
        raise CustomApiException(error_code=ErrorCodes.PROJECT_NAME_TAKEN)
    return project


def archive_project(project):
    if project.status != Project.ARCHIVED:
        project.status = Project.ARCHIVED
        project.archived_at = timezone.now()
        save_project(project)
    return project


def restore_project(project):
    if project.status != Project.ACTIVE:
        project.status = Project.ACTIVE
        project.archived_at = None
        save_project(project)  # the name may have been taken by another active project meanwhile
    return project


def delete_project(project):
    """Only a project without linked items can be deleted; one with items is archived instead."""
    if project.order_items.exists():
        raise CustomApiException(error_code=ErrorCodes.PROJECT_HAS_ITEMS)
    project.delete()


def projects_with_counts(customer):
    return Project.objects.filter(customer=customer).annotate(
        items_count=Count("order_items", distinct=True),
        orders_count=Count("order_items__order", distinct=True),
    )


# --- linking order items --------------------------------------------------------------------------------------------

def category_root_id(product):
    item_category = product.product_item_category
    sub_category = item_category.product_sub_category if item_category else None
    return sub_category.product_category_id if sub_category else None


def _lock_order(customer, order_id):
    order = Order.objects.select_for_update().filter(id=order_id, customer=customer).first()
    if not order:
        raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Order not found")
    return order


def _order_items(order, item_ids):
    items = list(order.order_items.select_related(
        "product__product_item_category__product_sub_category").order_by("id"))
    if not item_ids:
        return items
    wanted = set(item_ids)
    missing = wanted - {item.id for item in items}
    if missing:
        raise CustomApiException(error_code=ErrorCodes.NOT_FOUND,
                                 message={"missing_item_ids": sorted(missing)})
    return [item for item in items if item.id in wanted]


@transaction.atomic
def link_items(customer, order_id, project_id, item_ids=None, force=False):
    """Links the whole order (no `item_ids`) or the given items of it to the project. Items linked to another project
    are a conflict: without `force` nothing changes and 409 lists them, with `force` they are moved.
    The order row is locked, so concurrent requests on one order run one after another."""
    project = get_project(customer, project_id)
    if project.status != Project.ACTIVE:
        raise CustomApiException(error_code=ErrorCodes.PROJECT_ARCHIVED)
    order = _lock_order(customer, order_id)
    if order.status == CANCELED:
        raise CustomApiException(error_code=ErrorCodes.ORDER_CANCELED)
    if not LINK_PRE_PRO_ORDERS and order.account_type_at_order != Customer.AccountType.PRO:
        raise CustomApiException(error_code=ErrorCodes.FORBIDDEN, message="Order was placed before PRO")

    items = _order_items(order, item_ids)
    conflicts = [item for item in items if item.project_id not in (None, project.id)]
    if conflicts and not force:
        raise CustomApiException(error_code=ErrorCodes.PROJECT_ITEMS_CONFLICT, message={
            "conflicting_item_ids": [item.id for item in conflicts],
        })

    changed, history = [], []
    for item in items:
        if item.project_id == project.id:
            continue
        history.append(OrderItemProjectChange(
            order=order, order_item=item, customer=customer, old_project_id=item.project_id, new_project=project,
            action=OrderItemProjectChange.MOVE if item.project_id else OrderItemProjectChange.LINK,
        ))
        item.project = project
        item.category_root_id = category_root_id(item.product)
        changed.append(item)
    OrderItem.objects.bulk_update(changed, ["project", "category_root"])
    OrderItemProjectChange.objects.bulk_create(history)
    return order


@transaction.atomic
def unlink_items(customer, order_id, item_ids=None):
    order = _lock_order(customer, order_id)
    changed, history = [], []
    for item in _order_items(order, item_ids):
        if item.project_id is None:
            continue
        history.append(OrderItemProjectChange(order=order, order_item=item, customer=customer,
                                              old_project_id=item.project_id, action=OrderItemProjectChange.UNLINK))
        item.project = None
        item.category_root = None
        changed.append(item)
    OrderItem.objects.bulk_update(changed, ["project", "category_root"])
    OrderItemProjectChange.objects.bulk_create(history)
    return order


def orders_with_unlinked_items(customer):
    orders = Order.objects.filter(customer=customer).exclude(status=CANCELED).filter(
        Exists(OrderItem.objects.filter(order=OuterRef("pk"), project__isnull=True)))
    if not LINK_PRE_PRO_ORDERS:
        orders = orders.filter(account_type_at_order=Customer.AccountType.PRO)
    return orders.annotate(
        items_count=Count("order_items"),
        unlinked_items_count=Count("order_items", filter=Q(order_items__project__isnull=True)),
    ).order_by("-created_at", "-id")


# --- expenses -------------------------------------------------------------------------------------------------------

def allocate(amount, weights):
    """Splits `amount` into whole cents in proportion to `weights`; the parts add up to `amount` exactly
    (largest remainder; equal parts when all weights are 0)."""
    count = len(weights)
    if not count:
        return []
    cents = int((money(amount) / CENT).to_integral_value(ROUND_HALF_UP))
    total = sum(weights, Decimal(0))
    if total <= 0:
        weights, total = [Decimal(1)] * count, Decimal(count)
    raw = [Decimal(cents) * weight / total for weight in weights]
    parts = [int(value.to_integral_value(ROUND_FLOOR)) for value in raw]
    by_remainder = sorted(range(count), key=lambda i: (parts[i] - raw[i], i))
    for i in by_remainder[:cents - sum(parts)]:
        parts[i] += 1
    return [Decimal(part) * CENT for part in parts]


def item_unit_price(item):
    # items placed before `unit_price` existed: the product's current price
    return item.unit_price if item.unit_price is not None else OrderItem.unit_price_of(item.product)


def delivery_cost(order):
    return money(order.delivery_price) if order.delivery_type == DELIVERY else ZERO


def promocode_discount(order, subtotal):
    if order.promocode_discount is not None:
        discount = money(order.promocode_discount)
    elif order.promocode_id:
        # orders older than the field: what the goods cost less than their sum
        discount = subtotal - (money(order.total_price) - delivery_cost(order))
    else:
        discount = ZERO
    return min(max(discount, ZERO), subtotal)


@dataclass
class ItemExpense:
    item: OrderItem
    order: Order
    unit_price: Decimal
    amount: Decimal  # unit price × quantity
    discount: Decimal  # share of the promocode discount
    delivery: Decimal  # share of the delivery

    @property
    def goods(self):
        return self.amount - self.discount

    @property
    def total(self):
        return self.goods + self.delivery


def order_expenses(order, items):
    """Every item of the order with its share of the promocode discount and of the delivery."""
    prices = [item_unit_price(item) for item in items]
    amounts = [price * item.quantity for price, item in zip(prices, items)]
    subtotal = sum(amounts, ZERO)
    discounts = allocate(promocode_discount(order, subtotal), amounts)
    deliveries = allocate(delivery_cost(order), amounts)
    return [ItemExpense(item, order, price, amount, discount, delivery)
            for item, price, amount, discount, delivery in zip(items, prices, amounts, discounts, deliveries)]


def linked_expenses(customer, date_from=None, date_to=None, project_id=None):
    """Expenses of the customer's items linked to projects (or to one project), newest order first.
    Counted: paid, not canceled orders, by the order date."""
    linked = OrderItem.objects.filter(order=OuterRef("pk"), project__customer=customer)
    if project_id is not None:
        linked = linked.filter(project_id=project_id)
    orders = Order.objects.filter(customer=customer, payment_status=PAID).exclude(status=CANCELED).filter(
        Exists(linked))
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    orders = orders.prefetch_related(Prefetch(
        "order_items", queryset=OrderItem.objects.select_related("product", "project", "category_root")
        .prefetch_related("product__product_image").order_by("id"),
    )).order_by("-created_at", "-id")

    result = []
    for order in orders:
        for expense in order_expenses(order, list(order.order_items.all())):
            project = expense.item.project
            if project is None or project.customer_id != customer.id:
                continue
            if project_id is None or project.id == project_id:
                result.append(expense)
    return result


def expense_totals(expenses):
    goods = sum((expense.goods for expense in expenses), ZERO)
    delivery = sum((expense.delivery for expense in expenses), ZERO)
    return {
        "goods": goods,
        "delivery": delivery,
        "total": goods + delivery,
        "orders_count": len({expense.order.id for expense in expenses}),
        "items_count": len(expenses),
    }


def expenses_by_project(expenses, projects):
    grouped = defaultdict(list)
    for expense in expenses:
        grouped[expense.item.project_id].append(expense)
    return [{"id": project.id, "name": project.name, "status": project.status, **expense_totals(grouped[project.id])}
            for project in projects]


def expenses_by_category(expenses, name_of):
    """Goods (after the promocode) by the root category kept at linking; adds up to the goods total.
    `name_of(category)` gives the label; items without a category are one row with `id` null."""
    goods, categories = defaultdict(lambda: ZERO), {}
    for expense in expenses:
        key = expense.item.category_root_id
        goods[key] += expense.goods
        categories[key] = expense.item.category_root
    rows = [{"id": key, "name": name_of(categories[key]) if categories[key] else None, "goods": value}
            for key, value in goods.items()]
    return sorted(rows, key=lambda row: (-row["goods"], row["id"] is None, row["id"] or 0))
