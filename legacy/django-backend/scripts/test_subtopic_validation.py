import requests
import json

# Replace with actual tokens if needed, but for now let's just see if we can get a response
# Or use python manage.py shell to test serializer validation directly

from quiz.models import Topic, Subtopic
from quiz.serializers import SubtopicSerializer

def test_subtopic_creation():
    topic = Topic.objects.first()
    if not topic:
        print("No topic found")
        return

    data = {
        "name": "Test Subtopic",
        "description": "Test Description",
        "prerequisite_subtopics": [],
        "topic": str(topic.id)
    }

    serializer = SubtopicSerializer(data=data)
    if serializer.is_valid():
        print("Validation successful")
    else:
        print("Validation failed:")
        print(serializer.errors)

if __name__ == "__main__":
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    test_subtopic_creation()
