import logging
import inspect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from django.db import IntegrityError

# Configure logging with filename and line numbers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)
User = get_user_model()

def _log_request_info(request, action):
    """Log request information with client details."""
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    logger.info(f"{action} request from {client_ip} - User-Agent: {user_agent[:100]}...")

__all__ = ['RegisterView', 'LoginView']

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        _log_request_info(request, "Registration")

        try:
            username = request.data.get('username')
            email = request.data.get('email')
            password = request.data.get('password')

            logger.info(f"Registration attempt for username: {username}, email: {email}")

            if not all([username, email, password]):
                logger.warning(f"Registration attempt with missing fields - username: {bool(username)}, email: {bool(email)}, password: {bool(password)}")
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

            logger.info(f"User registered successfully: {username} (ID: {user.id})")
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username
            }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            logger.error(f"Registration failed - IntegrityError for {username}: {str(e)}")
            return Response(
                {'detail': 'Username or email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Registration failed - Unexpected error for {username}: {str(e)}")
            return Response(
                {'detail': 'Registration failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        _log_request_info(request, "Login")

        username = request.data.get('username')
        password = request.data.get('password')

        logger.info(f"Login attempt for username: {username}")

        if not all([username, password]):
            logger.warning(f"Login attempt with missing credentials for username: {username}")
            return Response(
                {'detail': 'Please provide username and password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(username=username)
            if not user.check_password(password):
                logger.warning(f"Failed login attempt - incorrect password for user: {username}")
                raise User.DoesNotExist
        except User.DoesNotExist:
            logger.warning(f"Login attempt for non-existent user or wrong password: {username}")
            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get or create token - ensure we always have a valid token
        token, created = Token.objects.get_or_create(user=user)

        # If token already existed, regenerate it to ensure it's fresh
        if not created:
            token.delete()
            token = Token.objects.create(user=user)

        logger.info(f"Successful login for user: {username} (ID: {user.id}) - Fresh token created")

        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username
        })
