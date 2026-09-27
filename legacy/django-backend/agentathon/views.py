from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny # For demo simplicity
import uuid
import os
from django.conf import settings
from .models import AgentathonSession, AgentLog
from .pipeline import trigger_pipeline

class DocumentUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        # Save file locally for pipeline to read
        temp_dir = os.path.join(settings.BASE_DIR, "tmp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # Create a new session
        session_id = str(uuid.uuid4())
        session = AgentathonSession.objects.create(session_id=session_id)

        # Trigger background pipeline
        trigger_pipeline(session_id, file_path)

        return Response({"session_id": session_id, "message": "Document uploaded, agents started processing"}, status=status.HTTP_202_ACCEPTED)

class SessionStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({"error": "Missing session_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = AgentathonSession.objects.get(session_id=session_id)
            logs = AgentLog.objects.filter(session=session).order_by('timestamp')
            
            log_data = [
                {
                    "id": log.id,
                    "agent_name": log.agent_name,
                    "decision": log.decision,
                    "timestamp": log.timestamp.isoformat(),
                    "verified": log.verified
                }
                for log in logs
            ]

            return Response({
                "session_id": session_id,
                "status": session.status,
                "logs": log_data,
                "quiz_data": session.quiz_data,
                "pathway_data": session.pathway_data
            }, status=status.HTTP_200_OK)
            
        except AgentathonSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
