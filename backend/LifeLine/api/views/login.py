import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from django.db import IntegrityError

logger = logging.getLogger(__name__)
User = get_user_model()

__all__ = ['RegisterView', 'LoginView']

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            username = request.data.get('username')
            email = request.data.get('email')
            password = request.data.get('password')

            if not all([username, email, password]):
                logger.warning(f"Registration attempt with missing fields: {request.data}")
                return Response(
                    {'detail': 'Please provide username, email and password'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Create auth token
            token = Token.objects.create(user=user)

            logger.info(f"User registered successfully: {username}")
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username
            }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            logger.error(f"Registration failed - IntegrityError: {str(e)}")
            return Response(
                {'detail': 'Username or email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Registration failed - Unexpected error: {str(e)}")
            return Response(
                {'detail': 'Registration failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not all([username, password]):
            logger.warning(f"Login attempt with missing credentials for username: {username}")
            return Response(
                {'detail': 'Please provide username and password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(username=username)
            if not user.check_password(password):
                logger.warning(f"Failed login attempt for user: {username}")
                raise User.DoesNotExist
        except User.DoesNotExist:
            logger.warning(f"Login attempt for non-existent user: {username}")
            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)
        logger.info(f"Successful login for user: {username}")
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username
        })
