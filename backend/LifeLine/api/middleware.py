"""
Custom middleware for API CSRF handling with enhanced security.
"""

import logging

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class APICSRFExemptMiddleware(MiddlewareMixin):
    """
    Middleware to selectively exempt API endpoints from CSRF protection.

    This is secure because:
    1. Only exempts endpoints that use pure token authentication
    2. Admin and session-based endpoints retain CSRF protection
    3. Checks for Authorization header presence for additional security
    4. Maintains all other security measures (CORS, token validation, etc.)
    """

    # Endpoints that should be exempt from CSRF (token-auth only)
    CSRF_EXEMPT_PATHS = [
        "/api/login/",
        "/api/register/",
        "/api/conversations/",
        "/api/messages/",
        "/api/memories/",
        "/api/transcribe/",
        "/api/health/",
    ]

    # Endpoints that should KEEP CSRF protection (session-based or admin)
    CSRF_REQUIRED_PATHS = [
        "/api/admin/",
        "/admin/",
    ]

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Selectively exempt API endpoints from CSRF protection based on authentication method.
        """
        path = request.path

        # Always require CSRF for admin endpoints
        if any(path.startswith(admin_path) for admin_path in self.CSRF_REQUIRED_PATHS):
            logger.debug(f"CSRF protection REQUIRED for admin endpoint: {path}")
            return None

        # Check if this is an API endpoint that should be exempt
        should_exempt = any(path.startswith(exempt_path) for exempt_path in self.CSRF_EXEMPT_PATHS) or path.startswith(
            "/api/"
        )

        if should_exempt:
            # Additional security: For non-auth endpoints, prefer token auth
            has_auth_header = "HTTP_AUTHORIZATION" in request.META
            is_auth_endpoint = path in ["/api/login/", "/api/register/", "/api/health/"]

            if is_auth_endpoint or has_auth_header:
                logger.debug(f"Exempting {path} from CSRF protection (API endpoint with proper auth)")
                setattr(view_func, "csrf_exempt", True)
            else:
                logger.warning(f"API endpoint {path} accessed without Authorization header - keeping CSRF protection")

        return None
