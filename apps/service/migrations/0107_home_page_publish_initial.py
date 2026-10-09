from django.db import migrations

RULE_FIELDS = ("hide_out_of_stock", "hide_stale_price", "min_products")
SNAPSHOT_FIELDS = ("id", "type", "title_uz", "title_ru", "title_en", "is_visible", "show_on_site", "show_in_app",
                   "banner_placement", "banner_id", "badge_id", "sale_id", "days", "pages")


def forwards(apps, schema_editor):
    # the seeded layout (0106) is what the clients render today: make it the published version,
    # so the client endpoint has data before the first "publish" in the admin panel
    HomeBlock = apps.get_model("service", "HomeBlock")
    HomePage = apps.get_model("service", "HomePage")
    page, _ = HomePage.objects.get_or_create(pk=1)
    if page.published_data is None:
        page.published_data = {
            "rules": {name: getattr(page, name) for name in RULE_FIELDS},
            "blocks": list(HomeBlock.objects.order_by("position", "id").values(*SNAPSHOT_FIELDS)),
        }
        page.save(update_fields=["published_data"])


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0106_home_blocks_data'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
