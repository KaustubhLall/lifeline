import asyncio
import json
import logging
import os
from urllib.parse import urljoin

from api.models import MCPConnector, MCPOperation
from api.utils.connectors.gmail.gmail_mcp import get_gmail_mcp_server, cleanup_mcp_server
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect
from django.conf import settings
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


class GmailMCPView(APIView):
    """Main view for Gmail MCP operations"""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_or_create_connector(self, user):
        """Get or create Gmail connector for user"""
        connector, created = MCPConnector.objects.get_or_create(
            user=user,
            connector_type="gmail",
            name="Gmail",
            defaults={
                "scopes": [
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.modify",
                    "https://www.googleapis.com/auth/gmail.labels",
                ],
                "redirect_uri": "http://localhost:8000/api/auth/gmail/callback",
                "config": {},
            },
        )
        return connector

    def log_operation(self, connector, operation_type, request_data=None):
        """Create operation log entry"""
        return MCPOperation.objects.create(
            connector=connector, operation_type=operation_type, request_data=request_data or {}
        )


class GmailAuthView(GmailMCPView):
    """Handle Gmail authentication"""

    def get(self, request):
        """Get authentication URL"""
        try:
            connector = self.get_or_create_connector(request.user)
            gmail_server = get_gmail_mcp_server(str(request.user.id))

            # Check if already authenticated
            if gmail_server.has_valid_credentials():
                connector.mark_as_authenticated()
                return Response({"authenticated": True, "message": "Already authenticated with Gmail"})

            # Get auth URL - let the Gmail server handle redirect URI logic consistently
            try:
                auth_url = gmail_server.get_auth_url()
                connector.status = "pending"
                connector.save()

                return Response(
                    {
                        "authenticated": False,
                        "auth_url": auth_url,
                        "message": "Please complete authentication",
                    }
                )
            except FileNotFoundError:
                return Response(
                    {
                        "error": "OAuth configuration file not found. Please upload your Google Cloud credentials.",
                        "requires_config": True,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error in Gmail auth view: {e}")
            connector.mark_as_error(str(e))
            return Response(
                {"error": str(e), "message": "Failed to initiate authentication"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GmailStatusView(GmailMCPView):
    """Get Gmail connector status"""

    def get(self, request):
        """Get current Gmail status"""
        try:
            connector = self.get_or_create_connector(request.user)
            gmail_server = get_gmail_mcp_server(str(request.user.id))

            # Get recent operations
            recent_operations = MCPOperation.objects.filter(connector=connector).order_by("-started_at")[:10]

            operations_data = []
            for op in recent_operations:
                operations_data.append(
                    {
                        "id": op.id,
                        "operation_type": op.operation_type,
                        "status": op.status,
                        "started_at": op.started_at.isoformat(),
                        "completed_at": op.completed_at.isoformat() if op.completed_at else None,
                        "duration_ms": op.duration_ms,
                        "error_message": op.error_message,
                    }
                )

            # Check authentication status
            authenticated = gmail_server.has_valid_credentials()
            if authenticated:
                connector.mark_as_authenticated()
                connector.mark_as_used()

            status_data = {
                "authenticated": authenticated,
                "status": connector.status,
                "message": connector.config.get("last_error")
                or ("Gmail connector ready" if authenticated else "Not authenticated"),
                "last_authenticated": (
                    connector.last_authenticated.isoformat() if connector.last_authenticated else None
                ),
                "last_used": connector.last_used.isoformat() if connector.last_used else None,
                "recent_operations": operations_data,
            }

            return Response(status_data)

        except Exception as e:
            logger.error(f"Error getting Gmail status: {e}")
            return Response(
                {
                    "authenticated": False,
                    "status": "error",
                    "message": f"Error checking status: {str(e)}",
                    "recent_operations": [],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GmailOperationsView(GmailMCPView):
    """Handle Gmail operations"""

    def post(self, request):
        """Execute Gmail operation"""
        try:
            operation = request.data.get("operation")
            operation_data = request.data.get("data", {})

            connector = self.get_or_create_connector(request.user)
            gmail_server = get_gmail_mcp_server(str(request.user.id))

            # Log the operation
            op_log = self.log_operation(connector, operation, operation_data)

            # Execute the operation using asyncio.run for async operations
            result = None
            try:
                if operation == "list_labels":
                    result = asyncio.run(gmail_server.list_labels())
                elif operation == "search_emails":
                    result = asyncio.run(
                        gmail_server.search_emails(
                            query=operation_data.get("query", "in:inbox"),
                            max_results=operation_data.get("max_results", 10),
                        )
                    )
                elif operation == "send_email":
                    result = asyncio.run(
                        gmail_server.send_email(
                            to=operation_data.get("to", []),
                            subject=operation_data.get("subject", ""),
                            body=operation_data.get("body", ""),
                            cc=operation_data.get("cc"),
                            bcc=operation_data.get("bcc"),
                            html_body=operation_data.get("html_body"),
                            attachments=operation_data.get("attachments"),
                            mime_type=operation_data.get("mime_type", "text/plain"),
                        )
                    )
                elif operation == "read_email":
                    result = asyncio.run(gmail_server.read_email(operation_data.get("message_id")))
                elif operation == "modify_email":
                    result = asyncio.run(
                        gmail_server.modify_email(
                            message_id=operation_data.get("message_id"),
                            add_label_ids=operation_data.get("add_label_ids"),
                            remove_label_ids=operation_data.get("remove_label_ids"),
                        )
                    )
                elif operation == "delete_email":
                    result = asyncio.run(gmail_server.delete_email(operation_data.get("message_id")))
                elif operation == "create_label":
                    result = asyncio.run(
                        gmail_server.create_label(
                            name=operation_data.get("name"),
                            message_list_visibility=operation_data.get("message_list_visibility", "show"),
                            label_list_visibility=operation_data.get("label_list_visibility", "labelShow"),
                        )
                    )
                else:
                    result = {"error": f"Unknown operation: {operation}"}

                # Mark operation as completed
                if "error" in result:
                    op_log.mark_completed(error_message=result["error"])
                else:
                    op_log.mark_completed(response_data=result)
                    connector.mark_as_used()

                return Response(result)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error executing {operation}: {error_msg}")
                op_log.mark_completed(error_message=error_msg)
                return Response({"error": error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error in Gmail operations view: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GmailConfigUploadView(GmailMCPView):
    """Handle OAuth config upload"""

    def get(self, request):
        """Get OAuth configuration info including redirect URI"""
        try:
            gmail_server = get_gmail_mcp_server(str(request.user.id))

            # Get the redirect URI that will be used
            oauth_config = gmail_server.get_oauth_config()
            redirect_uri = None

            if oauth_config and oauth_config.get("web", {}).get("redirect_uris"):
                redirect_uri = oauth_config["web"]["redirect_uris"][0]
            else:
                # Generate dynamic redirect URI based on request
                scheme = "https" if request.is_secure() else "http"
                host = request.get_host()
                redirect_uri = f"{scheme}://{host}/api/auth/gmail/callback"

            return Response({"redirect_uri": redirect_uri, "has_config": oauth_config is not None})
        except Exception as e:
            logger.error(f"Error getting OAuth config info: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Upload OAuth configuration file"""
        try:
            if "oauth_config" not in request.FILES:
                return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

            config_file = request.FILES["oauth_config"]

            # Validate file type
            if not config_file.name.endswith(".json"):
                return Response({"error": "File must be a JSON file"}, status=status.HTTP_400_BAD_REQUEST)

            # Read and validate JSON content
            try:
                config_content = config_file.read().decode("utf-8")
                config_data = json.loads(config_content)

                # Validate it's a proper OAuth config
                if "web" not in config_data and "installed" not in config_data:
                    return Response(
                        {"error": "Invalid OAuth configuration. File must contain 'web' or 'installed' credentials."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            except json.JSONDecodeError:
                return Response({"error": "Invalid JSON file"}, status=status.HTTP_400_BAD_REQUEST)
            except UnicodeDecodeError:
                return Response({"error": "File must be UTF-8 encoded"}, status=status.HTTP_400_BAD_REQUEST)

            # Save the config file
            gmail_server = get_gmail_mcp_server(str(request.user.id))
            config_path = gmail_server.get_oauth_config_path()

            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                f.write(config_content)

            logger.info(f"OAuth config uploaded for user {request.user.id}")
            return Response({"message": "OAuth configuration uploaded successfully"})

        except Exception as e:
            logger.error(f"Error uploading OAuth config: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def gmail_oauth_callback(request):
    """Handle Gmail OAuth callback"""
    try:
        code = request.GET.get("code")
        state = request.GET.get("state")  # This is the user_id
        error = request.GET.get("error")

        # It's better to redirect to a configurable frontend URL
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000/")
        settings_url = urljoin(frontend_url, "settings")

        if error:
            logger.error(f"OAuth error: {error}")
            return redirect(f"{settings_url}?auth_error={error}")

        if not code or not state:
            logger.error("Missing code or state in OAuth callback")
            return redirect(f"{settings_url}?auth_error=missing_code_or_state")

        # Get user from state
        try:
            User = get_user_model()
            user = User.objects.get(id=state)
        except (User.DoesNotExist, ValueError):
            logger.error(f"Invalid user ID in state: {state}")
            return redirect(f"{settings_url}?auth_error=invalid_user")

        # Handle the callback
        gmail_server = get_gmail_mcp_server(str(user.id))

        # Generate the same redirect URI that was used for auth
        scheme = "https" if request.is_secure() else "http"
        host = request.get_host()
        redirect_uri = f"{scheme}://{host}/api/auth/gmail/callback"

        success = gmail_server.handle_oauth_callback(code, redirect_uri=redirect_uri)

        if success:
            # Update connector status
            try:
                connector = MCPConnector.objects.get(user=user, connector_type="gmail")
                connector.mark_as_authenticated()
                logger.info(f"Gmail OAuth successful for user {user.id}")
                return redirect(f"{settings_url}?auth_success=gmail")
            except MCPConnector.DoesNotExist:
                logger.warning(f"Connector not found for user {user.id}")
                return redirect(f"{settings_url}?auth_error=callback_failed")
        else:
            logger.error(f"OAuth callback failed for user {user.id}")
            return redirect(f"{settings_url}?auth_error=callback_failed")

    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        # Also redirect to frontend on general exceptions
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000/")
        settings_url = urljoin(frontend_url, "settings")
        return redirect(f"{settings_url}?auth_error=server_error")
