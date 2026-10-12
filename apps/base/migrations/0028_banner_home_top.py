from django.db import migrations, models

OLD_PLACEMENTS = ("site_home", "app_home")


def forwards(apps, schema_editor):
    # the two top placements become one list: keep the order the clients already get them in
    # (both together, by position)
    Banner = apps.get_model("base", "Banner")
    banners = list(Banner.objects.filter(placement__in=OLD_PLACEMENTS).order_by("position", "id"))
    for position, banner in enumerate(banners, start=1):
        banner.placement = "home_top"
        banner.position = position
    Banner.objects.bulk_update(banners, ["placement", "position"])


def backwards(apps, schema_editor):
    apps.get_model("base", "Banner").objects.filter(placement="home_top").update(placement="site_home")


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0027_notification_audience'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name='banner',
            name='placement',
            field=models.CharField(choices=[('home_top', 'Главная · верхний слайдер'), ('home_bottom', 'Главная · внизу страницы'), ('catalog', 'Внутри каталога')], default='home_top', max_length=20, verbose_name='Расположение'),
        ),
    ]
