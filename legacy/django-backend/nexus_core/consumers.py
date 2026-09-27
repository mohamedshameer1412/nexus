"""
nexus_core/consumers.py
Django Channels WebSocket consumer.
Streams agent task completion events to the frontend in real time.

Frontend connects to: ws://localhost:8000/ws/nexus/agents/<session_id>/
Then listens for messages: { "agent": "analytics", "status": "done", "result": {...} }
"""
import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from celery.result import AsyncResult

logger = logging.getLogger(__name__)

POLL_INTERVAL = 0.5   # seconds between status checks
MAX_WAIT_S    = 35    # give up after 35 seconds


class AgentPipelineConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        await self.accept()
        logger.info(f"[WS] Client connected for session {self.session_id}")

    async def disconnect(self, close_code):
        logger.info(f"[WS] Client disconnected for session {self.session_id}")

    async def receive(self, text_data):
        """
        Frontend sends: { "task_ids": {"analytics": "abc-123", "evaluator": "def-456", ...} }
        We poll each task and stream status back as they complete.
        """
        try:
            data = json.loads(text_data)
            task_ids = data.get("task_ids", {})

            if not task_ids:
                await self.send_json({"error": "No task_ids provided"})
                return

            await self.stream_agent_results(task_ids)

        except Exception as e:
            logger.error(f"[WS] Error: {e}")
            await self.send_json({"error": str(e)})

    async def stream_agent_results(self, task_ids: dict):
        """
        Poll all tasks until complete (or timeout).
        Send a message for each agent as it finishes.
        """
        pending = dict(task_ids)  # {agent_name: task_id}
        elapsed = 0

        await self.send_json({
            "type": "pipeline_start",
            "agents": list(pending.keys()),
            "session_id": self.session_id,
        })

        while pending and elapsed < MAX_WAIT_S:
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

            completed = []
            for agent_name, task_id in pending.items():
                result = AsyncResult(task_id)

                if result.ready():
                    status = "done" if result.successful() else "failed"
                    output = result.result if result.successful() else str(result.result)

                    await self.send_json({
                        "type":    "agent_complete",
                        "agent":   agent_name,
                        "status":  status,
                        "result":  output if isinstance(output, dict) else {"raw": str(output)},
                    })
                    completed.append(agent_name)

            for agent_name in completed:
                del pending[agent_name]

        # Handle timeouts
        for agent_name in pending:
            await self.send_json({
                "type":   "agent_timeout",
                "agent":  agent_name,
                "status": "timeout",
            })

        await self.send_json({"type": "pipeline_complete", "session_id": self.session_id})

    async def send_json(self, data: dict):
        await self.send(text_data=json.dumps(data))
