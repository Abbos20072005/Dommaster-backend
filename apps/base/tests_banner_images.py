import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework import serializers
from rest_framework.test import APIClient

from apps.base.api.v1.admin.serializers import BannerSerializer
from apps.base.models import Banner

MEDIA = tempfile.mkdtemp()


def image(name):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def save(data, instance=None):
    base = {"title_ru": "Баннер", "link_type": "url", "link": "https://buildex.uz", "starts_at": "2026-01-01T00:00"}
    serializer = BannerSerializer(instance, data=data if instance else {**base, **data}, partial=bool(instance))
    serializer.is_valid(raise_exception=True)
    return serializer.save()


@override_settings(MEDIA_ROOT=MEDIA)
class BannerImagesTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def client_banner(self, language):
        response = APIClient().get("/api/v1/base/banner/", HTTP_ACCEPT_LANGUAGE=language)
        return response.json()["result"][0]

    def test_each_language_gets_its_images_uz_falls_back_to_ru(self):
        save({"desktop_image_ru": image("d_ru.png"), "desktop_image_uz": image("d_uz.png"),
              "mobile_image_ru": image("m_ru.png")})
        ru, uz = self.client_banner("ru"), self.client_banner("uz")
        self.assertIn("d_ru", ru["desktop_image"])
        self.assertIn("m_ru", ru["mobile_image"])
        self.assertIn("d_uz", uz["desktop_image"])
        self.assertIn("m_ru", uz["mobile_image"])  # no uz mobile -> the ru one

    def test_no_mobile_image_is_null(self):
        save({"desktop_image_ru": image("d_ru.png")})
        self.assertIsNone(self.client_banner("uz")["mobile_image"])

    def test_ru_desktop_image_is_required(self):
        with self.assertRaises(serializers.ValidationError) as error:
            save({"desktop_image_uz": image("d_uz.png")})
        self.assertIn("desktop_image_ru", error.exception.detail)

    def test_ru_desktop_image_cannot_be_cleared(self):
        banner = save({"desktop_image_ru": image("d_ru.png")})
        with self.assertRaises(serializers.ValidationError):
            save({"desktop_image_ru": None}, banner)

    def test_deprecated_plain_names_write_ru(self):
        banner = save({"desktop_image": image("old_d.png"), "mobile_image": image("old_m.png")})
        self.assertIn("old_d", banner.desktop_image_ru.name)
        self.assertIn("old_m", banner.mobile_image_ru.name)
        self.assertFalse(banner.desktop_image_uz)

    def test_replaced_image_file_is_removed(self):
        banner = save({"desktop_image_ru": image("d_ru.png"), "desktop_image_uz": image("d_uz.png")})
        old = banner.desktop_image_uz
        storage, old_name = old.storage, old.name
        banner = save({"desktop_image_uz": image("d_uz2.png")}, banner)
        self.assertFalse(storage.exists(old_name))
        self.assertIn("d_uz2", banner.desktop_image_uz.name)

    def test_admin_response_has_every_image(self):
        banner = save({"desktop_image_ru": image("d_ru.png"), "mobile_image_uz": image("m_uz.png")})
        data = BannerSerializer(banner).data
        self.assertIn("d_ru", data["desktop_image_ru"])
        self.assertIsNone(data["desktop_image_uz"])
        self.assertIn("m_uz", data["mobile_image_uz"])
        self.assertIsNone(data["mobile_image_ru"])


class BackfillBannerImagesTests(TestCase):
    def setUp(self):
        Banner.objects.create(title_ru="Старый", link="https://buildex.uz")
        # a banner made before the per-language images: only the old plain columns are set
        Banner.objects.rewrite(False).update(desktop_image="banner/desktop/old.png", mobile_image="",
                                             desktop_image_ru=None, mobile_image_ru=None)

    def test_old_columns_go_to_ru(self):
        call_command("backfill_banner_images", stdout=io.StringIO())
        banner = Banner.objects.get()
        self.assertEqual(banner.desktop_image_ru.name, "banner/desktop/old.png")
        self.assertFalse(banner.mobile_image_ru)
        self.assertFalse(banner.desktop_image_uz)

    def test_dry_run_changes_nothing(self):
        call_command("backfill_banner_images", "--dry-run", stdout=io.StringIO())
        self.assertFalse(Banner.objects.get().desktop_image_ru)

    def test_filled_ru_is_kept(self):
        Banner.objects.update(desktop_image_ru="banner/desktop/new.png")
        call_command("backfill_banner_images", stdout=io.StringIO())
        self.assertEqual(Banner.objects.get().desktop_image_ru.name, "banner/desktop/new.png")
