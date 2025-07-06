from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    label = "api"
    verbose_name = "LifeLine API"

    def ready(self):
        # Import models here to ensure they're registered properly
        pass
