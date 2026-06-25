from django.contrib import admin, messages


def toggle_bool_field(field_name, enable_value=True, label=None):
    short_label = label or (f"Set {field_name} = {enable_value}")

    def action(modeladmin, request, queryset):
        updated = queryset.update(**{field_name: enable_value})
        messages.success(request, f"{updated} objects updated.")

    action.__name__ = f"set_{field_name}_{enable_value}"
    action.short_description = short_label
    return action


make_visible = toggle_bool_field("is_visible", True, "Set selected as visible")
make_hidden = toggle_bool_field("is_visible", False, "Set selected as hidden")
activate = toggle_bool_field("is_active", True, "Set selected as active")
deactivate = toggle_bool_field("is_active", False, "Set selected as inactive")
mark_as_main = toggle_bool_field("is_main", True, "Mark selected as main")
mark_as_not_main = toggle_bool_field("is_main", False, "Mark selected as not main")
mark_verified = toggle_bool_field("verified", True, "Mark selected as verified")
mark_unverified = toggle_bool_field("verified", False, "Mark selected as unverified")
mark_as_answer = toggle_bool_field("is_answer", True, "Mark selected as admin answer")
mark_default = toggle_bool_field("is_default", True, "Set selected as default")


@admin.action(description="Set order status to Collecting")
def status_collecting(modeladmin, request, queryset):
    updated = queryset.update(status=1)
    messages.success(request, f"{updated} orders set to Collecting.")


@admin.action(description="Set order status to Delivering")
def status_delivering(modeladmin, request, queryset):
    updated = queryset.update(status=2)
    messages.success(request, f"{updated} orders set to Delivering.")


@admin.action(description="Set order status to Completed")
def status_completed(modeladmin, request, queryset):
    updated = queryset.update(status=3)
    messages.success(request, f"{updated} orders set to Completed.")


@admin.action(description="Set order status to Canceled")
def status_canceled(modeladmin, request, queryset):
    updated = queryset.update(status=4)
    messages.success(request, f"{updated} orders set to Canceled.")
