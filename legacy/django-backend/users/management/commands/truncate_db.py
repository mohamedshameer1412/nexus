"""
Database truncation script
Clears all data from the database
"""
from django.core.management.base import BaseCommand
from django.apps import apps


class Command(BaseCommand):
    help = 'Truncate all database tables'

    def handle(self, *args, **options):
        # Get all models
        models = apps.get_models()
        
        self.stdout.write("Truncating database...")
        
        for model in models:
            try:
                count = model.objects.count()
                model.objects.all().delete()
                self.stdout.write(f"✅ Deleted {count} records from {model.__name__}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error deleting from {model.__name__}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS("\n✅ Database truncated successfully!"))
