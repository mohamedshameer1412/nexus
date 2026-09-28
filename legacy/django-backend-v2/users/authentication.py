from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

print("DEBUG: users.authentication module loaded")

class DebugJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
            print(f"DebugJWT: Authenticating user_id: {user_id}")
            user = self.user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
            print(f"DebugJWT: Success! User found: {user.username}")
            return user
        except KeyError:
            print("DebugJWT: Token contained no recognizable user identification")
            raise InvalidToken(('Token contained no recognizable user identification'))
        except self.user_model.DoesNotExist:
            print(f"DebugJWT: FAILED! User {user_id} not found in DB even with CharField fix.")
            raise AuthenticationFailed(('User not found'), code='user_not_found')

        if not user.is_active:
            print(f"DebugJWT: User {user.username} is inactive")
            raise AuthenticationFailed(('User is inactive'), code='user_inactive')

        return user
