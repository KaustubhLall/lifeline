# login and auth views

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
import rest_framework_simplejwt.tokens
from rest_framework.permissions import AllowAny

User = get_user_model()

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({'error': 'Username and password required.'}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists.'}, status=400)
        user = User.objects.create_user(username=username, password=password)
        refresh = rest_framework_simplejwt.tokens.RefreshToken.for_user(user)
        return Response({'refresh': str(refresh), 'access': str(refresh.access_token)}, status=201)

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            refresh = rest_framework_simplejwt.tokens.RefreshToken.for_user(user)
            return Response({'refresh': str(refresh), 'access': str(refresh.access_token)})
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
