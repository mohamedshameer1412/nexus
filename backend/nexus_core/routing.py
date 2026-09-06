from django.urls import re_path
from .consumers import AgentPipelineConsumer

websocket_urlpatterns = [
    re_path(r"ws/nexus/agents/(?P<session_id>[^/]+)/$", AgentPipelineConsumer.as_asgi()),
]
