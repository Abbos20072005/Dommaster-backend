"""PRO status of a customer: granted / revoked by staff only, every change is kept in CustomerAccountTypeChange."""
from django.db import transaction

from apps.authorization.models import Customer, CustomerAccountTypeChange


class AccountTypeError(Exception):
    pass


@transaction.atomic
def change_account_type(customer_id, new_value, user, reason=""):
    """Sets the customer's account type and writes the history row. Revoking PRO needs a reason.
    Projects of the customer are never touched: the client API hides them while the customer is not PRO."""
    customer = Customer.objects.select_for_update().get(pk=customer_id)
    old_value = customer.account_type
    reason = (reason or "").strip()
    if old_value == new_value:
        raise AccountTypeError(f"Account type is already {new_value}.")
    if old_value == Customer.AccountType.PRO and not reason:
        raise AccountTypeError("A reason is required to revoke PRO.")

    customer.account_type = new_value
    customer.save(update_fields=["account_type", "updated_at"])
    CustomerAccountTypeChange.objects.create(customer=customer, old_value=old_value, new_value=new_value,
                                             changed_by=user, reason=reason)
    return customer
