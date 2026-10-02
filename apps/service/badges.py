import operator
from datetime import timedelta
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from apps.service.models import OrderItem, Product, ProductBadge

SALES_DAYS = 30
ORDER_CANCELED = 4

OPERATORS = {
    ProductBadge.GT: operator.gt,
    ProductBadge.GTE: operator.ge,
    ProductBadge.LT: operator.lt,
    ProductBadge.LTE: operator.le,
    ProductBadge.EQ: operator.eq,
}


def _lookup(field, op):
    return field if op == ProductBadge.EQ else f"{field}__{op}"


def _number_q(field, op, value, null_as_zero=False):
    q = Q(**{_lookup(field, op): value})
    if null_as_zero and OPERATORS[op](0, value):
        q |= Q(**{f"{field}__isnull": True})
    return q


def _created_days_q(op, days, now):
    # full days since the product was added: `< 30` = added within the last 30 days
    newer = now - timedelta(days=days)
    older = now - timedelta(days=days + 1)
    return {
        ProductBadge.LT: Q(created_at__gt=newer),
        ProductBadge.LTE: Q(created_at__gt=older),
        ProductBadge.GT: Q(created_at__lte=older),
        ProductBadge.GTE: Q(created_at__lte=newer),
        ProductBadge.EQ: Q(created_at__gt=older, created_at__lte=newer),
    }[op]


def _sales_q(op, value, now):
    # units sold in not canceled orders of the last SALES_DAYS days
    items = OrderItem.objects.filter(order__created_at__gte=now - timedelta(days=SALES_DAYS)) \
        .exclude(order__status=ORDER_CANCELED).order_by()
    sold = items.values("product").annotate(total=Sum("quantity")).filter(**{_lookup("total", op): value})
    q = Q(pk__in=sold.values("product"))
    if OPERATORS[op](0, value):
        # products without sales have no rows at all
        q |= ~Q(pk__in=items.values("product"))
    return q


def rule_q(badge, now=None):
    """Products matching the rule of an auto badge."""
    now = now or timezone.now()
    field, op, value = badge.rule_field, badge.rule_operator, badge.rule_value
    if field == ProductBadge.DISCOUNT:
        return _number_q("discount", op, value, null_as_zero=True)
    if field == ProductBadge.QUANTITY:
        return _number_q("quantity", op, value)
    if field == ProductBadge.CREATED_DAYS:
        return _created_days_q(op, value, now)
    return _sales_q(op, value, now)


@transaction.atomic
def sync_auto_badge(badge, now=None):
    """Make the products of an auto badge exactly those matching its rule. Returns the number of changed links."""
    link = Product.badges.through
    links = link.objects.filter(productbadge=badge)
    matching = Product.objects.filter(rule_q(badge, now))
    removed, _ = links.exclude(product__in=matching).delete()
    missing = matching.exclude(pk__in=links.values("product")).values_list("pk", flat=True)
    added = link.objects.bulk_create([link(product_id=pk, productbadge_id=badge.pk) for pk in missing],
                                     batch_size=1000, ignore_conflicts=True)
    return removed + len(added)


def recalculate_auto_badges():
    """Sync every auto badge (inactive ones too, the admin list shows their product count) with its rule.
    Manual badges are never touched. Returns the number of changed links."""
    now = timezone.now()
    return sum(sync_auto_badge(badge, now) for badge in ProductBadge.objects.filter(kind=ProductBadge.AUTO))
