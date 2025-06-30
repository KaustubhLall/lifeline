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

    # Override the many-to-many fields to prevent conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='api_users',
        related_query_name='api_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='api_users',
        related_query_name='api_user',
    )

    def __str__(self):
        return self.username
