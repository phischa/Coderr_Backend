from django.test import TestCase
from django.apps import apps
from Coderr_app.apps import CoderrAppConfig


class CoderrAppConfigTest(TestCase):
    """Test CoderrAppConfig"""
    def test_app_config(self):
        app_config = apps.get_app_config('Coderr_app')
        self.assertIsInstance(app_config, CoderrAppConfig)
        self.assertEqual(app_config.name, 'Coderr_app')
        self.assertEqual(app_config.default_auto_field, 'django.db.models.BigAutoField')
