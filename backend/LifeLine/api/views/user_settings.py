import logging

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import check_password
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models.chat import Memory
from ..serializers import MemorySerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class UserProfileView(APIView):
    """View for managing user profile information"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user's profile information"""
        try:
            user = request.user
            profile_data = {
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_joined": user.date_joined,
                "last_login": user.last_login,
            }
            return Response(profile_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            return Response({"error": "Failed to fetch profile"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request):
        """Update user profile information with password confirmation"""
        try:
            user = request.user
            data = request.data

            # Password confirmation is required for profile changes
            password = data.get("password")
            if not password:
                return Response({"error": "Password confirmation is required"}, status=status.HTTP_400_BAD_REQUEST)

            # Verify current password
            if not check_password(password, user.password):
                return Response({"error": "Invalid password"}, status=status.HTTP_400_BAD_REQUEST)

            # Update allowed fields
            allowed_fields = ["username", "email", "first_name", "last_name"]
            updated_fields = []

            for field in allowed_fields:
                if field in data and data[field] != getattr(user, field):
                    # Check if username is already taken
                    if field == "username" and User.objects.filter(username=data[field]).exclude(id=user.id).exists():
                        return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)

                    # Check if email is already taken
                    if field == "email" and User.objects.filter(email=data[field]).exclude(id=user.id).exists():
                        return Response({"error": "Email already taken"}, status=status.HTTP_400_BAD_REQUEST)

                    setattr(user, field, data[field])
                    updated_fields.append(field)

            if updated_fields:
                user.save()
                logger.info(f"User {user.username} updated fields: {updated_fields}")

            return Response(
                {"message": "Profile updated successfully", "updated_fields": updated_fields}, status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return Response({"error": "Failed to update profile"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChangePasswordView(APIView):
    """View for changing user password"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Change user password"""
        try:
            user = request.user
            data = request.data

            current_password = data.get("current_password")
            new_password = data.get("new_password")

            if not current_password or not new_password:
                return Response(
                    {"error": "Both current and new passwords are required"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Verify current password
            if not authenticate(username=user.username, password=current_password):
                return Response({"error": "Current password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

            # Validate new password
            if len(new_password) < 8:
                return Response(
                    {"error": "New password must be at least 8 characters long"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Set new password
            user.set_password(new_password)
            user.save()

            logger.info(f"Password changed for user {user.username}")
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return Response({"error": "Failed to change password"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MemoryListView(APIView):
    """View for listing user memories with pagination"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get paginated list of user's memories"""
        try:
            user = request.user
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))

            # Get all memories for the user, ordered by creation date (newest first)
            memories_queryset = Memory.objects.filter(user=user).order_by("-created_at")

            # Paginate
            paginator = Paginator(memories_queryset, page_size)
            memories_page = paginator.get_page(page)

            # Serialize memories
            serializer = MemorySerializer(memories_page.object_list, many=True)

            return Response(
                {
                    "memories": serializer.data,
                    "pagination": {
                        "current_page": page,
                        "total_pages": paginator.num_pages,
                        "total_memories": paginator.count,
                        "has_next": memories_page.has_next(),
                        "has_previous": memories_page.has_previous(),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error fetching memories: {str(e)}")
            return Response({"error": "Failed to fetch memories"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MemoryDetailView(APIView):
    """View for managing individual memories"""

    permission_classes = [IsAuthenticated]

    def patch(self, request, memory_id):
        """Update a memory and set edited_at timestamp"""
        try:
            memory = Memory.objects.get(id=memory_id, user=request.user)
            data = request.data

            # Update memory content
            if "content" in data:
                memory.content = data["content"]

            # Set edited_at timestamp when user edits
            from django.utils import timezone

            memory.edited_at = timezone.now()
            memory.save()

            serializer = MemorySerializer(memory)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Memory.DoesNotExist:
            return Response({"error": "Memory not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
            return Response({"error": "Failed to update memory"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, memory_id):
        """Delete a memory"""
        try:
            memory = Memory.objects.get(id=memory_id, user=request.user)
            memory.delete()

            return Response({"message": "Memory deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

        except Memory.DoesNotExist:
            return Response({"error": "Memory not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting memory: {str(e)}")
            return Response({"error": "Failed to delete memory"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
