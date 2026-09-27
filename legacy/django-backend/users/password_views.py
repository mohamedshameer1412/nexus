from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

User = get_user_model()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    if not old_password or not new_password:
        return Response({'error': 'Both old_password and new_password are required'}, status=400)
    if not user.check_password(old_password):
        return Response({'error': 'Current password is incorrect'}, status=400)
    if len(new_password) < 8:
        return Response({'error': 'New password must be at least 8 characters long'}, status=400)
    user.set_password(new_password)
    user.save()
    return Response({'message': 'Password changed successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """
    Send password reset link to user email.
    POST /api/auth/password-reset/
    Body: { "email": "..." }
    """
    email = request.data.get('email', '').strip()
    if not email:
        return Response({'error': 'Email is required'}, status=400)
    try:
        user = User.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = f"http://localhost:3000/reset-password?uid={uid}&token={token}"
        # In production, send via email. For demo, return the link.
        return Response({
            'message': 'Password reset link generated.',
            'reset_link': reset_link,
            'note': 'In production this would be emailed.'
        })
    except User.DoesNotExist:
        # Security: return same message even if user not found
        return Response({'message': 'If this email exists, a reset link has been sent.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """
    Confirm password reset with uid + token.
    POST /api/auth/password-reset-confirm/
    Body: { "uid": "...", "token": "...", "new_password": "..." }
    """
    uid = request.data.get('uid', '')
    token = request.data.get('token', '')
    new_password = request.data.get('new_password', '')
    if not all([uid, token, new_password]):
        return Response({'error': 'uid, token and new_password are required'}, status=400)
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, Exception):
        return Response({'error': 'Invalid reset link'}, status=400)
    if not default_token_generator.check_token(user, token):
        return Response({'error': 'Reset link is invalid or expired'}, status=400)
    if len(new_password) < 8:
        return Response({'error': 'Password must be at least 8 characters'}, status=400)
    user.set_password(new_password)
    user.save()
    return Response({'message': 'Password reset successfully. Please login.'})
