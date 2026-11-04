from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings


class ProfileImageSaveTests(TestCase):
    def setUp(self):
        self.media_root = TemporaryDirectory()
        self.addCleanup(self.media_root.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_root.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        self.profile = User.objects.create_user(username="profile-test").profile

    @patch("users.models.image_resize")
    def test_saving_profile_with_unchanged_image_skips_image_resize(self, image_resize):
        self.profile.phone_number = "555-0100"

        self.profile.save()

        image_resize.assert_not_called()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.phone_number, "555-0100")

    @patch("users.models.image_resize")
    def test_saving_profile_with_replaced_image_resizes_image(self, image_resize):
        self.profile.image = SimpleUploadedFile(
            "avatar.png", b"image content", content_type="image/png"
        )

        self.profile.save()

        image_resize.assert_called_once_with(self.profile.image, 512, 512)
