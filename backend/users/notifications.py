"""
Utility functions for creating and sending notifications
"""
from .models import Notification
from django.core.mail import send_mail
from django.conf import settings


def create_notification(user, title, message, notification_type='general', 
                       related_object_id=None, related_object_type=None, send_email=False, html_message=None):
    """
    Create a notification for a user
    
    Args:
        user: User object
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        related_object_id: UUID of related object
        related_object_type: Type of related object (quiz, session, link, etc.)
        send_email: Whether to send email notification
        html_message: Optional HTML content for the email
    
    Returns:
        Notification object
    """
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        related_object_id=related_object_id,
        related_object_type=related_object_type
    )
    
    if send_email and user.email and getattr(user, 'preference_email_notifications', True):
        try:
            send_mail(
                subject=title,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
                html_message=html_message
            )
        except Exception as e:
            print(f"Failed to send email: {e}")
    
    return notification




def notify_quiz_assigned(students, quiz, classroom):
    """Notify students when a quiz is assigned"""
    notifications = []
    
    # HTML template for quiz assignment
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; line-height: 1.6; background-color: #f4f6f8; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #fff; padding: 0; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); padding: 30px 20px; text-align: center; color: white; }}
            .content {{ padding: 30px 20px; }}
            .btn {{ display: inline-block; background: #4f46e5; color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
            .quiz-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 20px 0; }}
            .footer {{ background: #f8fafc; padding: 15px; text-align: center; font-size: 12px; color: #64748b; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0; font-size: 24px;">New Assignment</h1>
            </div>
            <div class="content">
                <p>Hello <strong>{student_name}</strong>,</p>
                <p>A new quiz has been assigned to you in <strong>{classroom_name}</strong>.</p>
                
                <div class="quiz-card">
                    <h3 style="margin-top:0; color: #1e293b;">{quiz_title}</h3>
                    <p style="margin-bottom:0; color: #64748b; font-size: 14px;">Please complete this assignment before the due date.</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{dashboard_url}" class="btn">View Assignment</a>
                </div>
            </div>
            <div class="footer">
                <p>AI Learning Platform &bull; Automated Notification</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    for student in students:
        html_msg = html_template.format(
            student_name=student.full_name,
            classroom_name=classroom.name,
            quiz_title=quiz.title,
            dashboard_url=f"{settings.FRONTEND_URL}/dashboard" if hasattr(settings, 'FRONTEND_URL') else "#"
        )
        
        notification = create_notification(
            user=student,
            title="New Quiz Assigned",
            message=f"New quiz '{quiz.title}' assigned in {classroom.name}",
            notification_type='quiz_assigned',
            related_object_id=quiz.id,
            related_object_type='quiz',
            send_email=True,
            html_message=html_msg
        )
        notifications.append(notification)
    return notifications


    return notifications


def notify_classroom_invite(student, classroom):
    """Notify student of classroom invitation"""
    return create_notification(
        user=student,
        title="Classroom Invitation",
        message=f"You've been invited to join {classroom.name} by {classroom.teacher.full_name}",
        notification_type='classroom_invite',
        related_object_id=classroom.id,
        related_object_type='classroom',
        send_email=True
    )
