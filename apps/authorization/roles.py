"""Customer role: prorab = PRO (projects, expenses). Granted / revoked by staff only (admin API), every change is
kept in CustomerRoleChange."""
from django.db import transaction

from apps.authorization.activity import record_admin
from apps.authorization.models import Customer, CustomerActivity, CustomerRoleChange


class RoleError(Exception):
    pass


@transaction.atomic
def change_role(customer_id, new_role, user, reason=""):
    """Sets the customer's role and writes the history row. Revoking PRO (prorab -> user) needs a reason.
    Projects of the customer are never touched: the client API hides them while the customer is not prorab."""
    customer = Customer.objects.select_for_update().get(pk=customer_id)
    old_role = customer.role
    reason = (reason or "").strip()
    if old_role == new_role:
        raise RoleError(f"Role is already {new_role}.")
    if old_role == Customer.Role.PRORAB and not reason:
        raise RoleError("A reason is required to revoke PRO.")

    customer.role = new_role
    customer.save(update_fields=["role", "updated_at"])
    CustomerRoleChange.objects.create(customer=customer, old_value=old_role, new_value=new_role, changed_by=user,
                                      reason=reason)
    record_admin(customer, CustomerActivity.Kind.ROLE_CHANGED, user, old_value=old_role, new_value=new_role,
                 reason=reason)
    return customer
