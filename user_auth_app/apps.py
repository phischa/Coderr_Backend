from django.apps import AppConfig

class UserAuthAppConfig(AppConfig):  # Name der Klasse ändern
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_auth_app'  # Name der App ändern

    def ready(self):
        import user_auth_app.signals  # Import aus der eigenen App
