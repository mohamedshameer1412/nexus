from django.core.management.base import BaseCommand
from ml_engine.train_models import main as train_models_main

class Command(BaseCommand):
    help = 'Unleash the AI! Trains XGBoost and Random Forest models for student analytics.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initiating AI Model Training Sequence...'))
        
        try:
            # Run the training script
            train_models_main()
            self.stdout.write(self.style.SUCCESS('Successfully trained all AI models!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to train models: {e}'))
