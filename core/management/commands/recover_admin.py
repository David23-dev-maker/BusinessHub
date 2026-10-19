import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Temporarily recover a production Django administrator."

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_RECOVERY_USERNAME")
        password = os.environ.get("ADMIN_RECOVERY_PASSWORD")

        if not username or not password:
            raise CommandError(
                "Set ADMIN_RECOVERY_USERNAME and ADMIN_RECOVERY_PASSWORD "
                "in the service environment before running this command."
            )

        if len(password) < 12:
            raise CommandError(
                "Use a temporary password with at least 12 characters."
            )

        User = get_user_model()

        user = User.objects.filter(username=username).first()

        if user is None:
            user = User(username=username)

        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Administrator account '{username}' has been recovered."
            )
        )