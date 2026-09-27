from django.db import models

class AgentathonSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, default="started") # started, processing, completed, error
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Store outputs as JSON fields
    extracted_text = models.TextField(blank=True, null=True)
    quiz_data = models.JSONField(blank=True, null=True)
    pathway_data = models.JSONField(blank=True, null=True)
    
    def __str__(self):
        return f"Session {self.session_id}"

class AgentLog(models.Model):
    session = models.ForeignKey(AgentathonSession, on_delete=models.CASCADE, related_name='logs')
    agent_name = models.CharField(max_length=50) # Tutor, Content, Evaluator, Analytics, Planner, Mentor
    decision = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.agent_name} - {self.session.session_id}"
