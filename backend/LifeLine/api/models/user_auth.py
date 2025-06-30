# login and user models

# user/auth model

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Meta:
        app_label = 'api'  # Explicitly set the app label
        db_table = 'api_user'  # Explicitly set the table name
        # Prevent model conflicts by being explicit about related names
        verbose_name = 'API User'
        verbose_name_plural = 'API Users'

    def __str__(self):
        return self.username
