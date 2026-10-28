import logging
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

CACHE_SECONDS = 26 * 60 * 60  # longer than a day: the key carries the date anyway


def record_visit(customer, language=None):
    """Mark today as a day the customer used the client API and keep `Customer.language` (the language of the
    request, None = the client sent none). At most one db write per customer and day (cache.add is the guard);
    never breaks the request."""
    try:
        from .models import Customer, CustomerVisit
        today = timezone.now().date()  # USE_TZ=False -> naive local time
        if not cache.add(f"customer_visit:{customer.pk}:{today.isoformat()}", 1, CACHE_SECONDS):
            return
        CustomerVisit.objects.bulk_create([CustomerVisit(customer_id=customer.pk, day=today)],
                                          ignore_conflicts=True)
        if language in Customer.Language.values and language != customer.language:
            Customer.objects.filter(pk=customer.pk).update(language=language)
    except Exception:  # noqa: BLE001 - activity tracking must not fail the request
        logger.exception("customer visit not recorded")
