"""python manage.py set_role <username> faculty|officer  -- who may review questions and resolve contests."""
from django.core.management.base import BaseCommand, CommandError

from studyhub.db import open_db


class Command(BaseCommand):
    help = "Give an account the faculty or officer role."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("role", choices=["faculty", "officer"])

    def handle(self, username, role, **opts):
        store = open_db()
        try:
            n = store.db.execute("UPDATE users SET role=? WHERE username=?", (role, username)).rowcount
        finally:
            store.close()
        if n != 1:
            raise CommandError(f"no account named {username!r}")
        self.stdout.write(f"{username} is now {role}")
