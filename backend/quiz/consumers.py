from channels.generic.websocket import AsyncWebsocketConsumer
import json


class QuizConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time quiz updates.
    Handles live difficulty adjustments, score updates, and instant feedback.
    """
    
    async def connect(self):
        """Accept WebSocket connection"""
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'quiz_{self.session_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Connected to quiz session {self.session_id}'
        }))
    
    async def disconnect(self, close_code):
        """Leave room group on disconnect"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'ping':
            # Respond to ping
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': data.get('timestamp')
            }))
        
        elif message_type == 'request_update':
            # Client requesting current session status
            await self.send_session_update()
    
    async def send_session_update(self):
        """Send current session status to client"""
        # This would fetch real session data from database
        # For now, sending a placeholder
        await self.send(text_data=json.dumps({
            'type': 'session_update',
            'data': {
                'current_question': 1,
                'total_questions': 10,
                'current_difficulty': 3,
                'student_ability': 0.5,
                'correct_answers': 0,
                'incorrect_answers': 0
            }
        }))
    
    # Event handlers for group messages
    async def difficulty_update(self, event):
        """Send difficulty update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'difficulty_update',
            'new_difficulty': event['difficulty'],
            'reason': event.get('reason', 'Performance-based adjustment')
        }))
    
    async def score_update(self, event):
        """Send score update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'score_update',
            'total_score': event['score'],
            'correct': event['correct'],
            'incorrect': event['incorrect'],
            'accuracy': event['accuracy']
        }))
    
    async def answer_feedback(self, event):
        """Send instant answer feedback to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'answer_feedback',
            'is_correct': event['is_correct'],
            'correct_answer': event['correct_answer'],
            'explanation': event['explanation'],
            'new_ability': event.get('new_ability')
        }))
    
    async def mindset_update(self, event):
        """Send mindset detection update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'mindset_update',
            'mindset': event['mindset'],
            'confidence': event.get('confidence', 0),
            'suggestion': event.get('suggestion', '')
        }))
    
    async def quiz_completed(self, event):
        """Send quiz completion notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'quiz_completed',
            'final_score': event['final_score'],
            'behavior_score': event['behavior_score'],
            'detected_mindset': event['mindset'],
            'message': 'Quiz completed successfully!'
        }))
