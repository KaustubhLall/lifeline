#!/usr/bin/env python3
"""
Gmail MCP Test Script
This script tests the Gmail MCP connector functionality
"""

import asyncio
import os
import sys

import django

# Add the Django project to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend", "LifeLine"))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LifeLine.settings")
django.setup()

from django.contrib.auth import get_user_model
from api.utils.connectors.gmail.gmail_mcp import get_gmail_mcp_server
from api.models import MCPConnector, MCPOperation

User = get_user_model()


class GmailMCPTester:
    def __init__(self, user_email=None):
        self.user_email = user_email
        self.user = None
        self.gmail_server = None

    def setup_user(self):
        """Get or create a test user"""
        if self.user_email:
            try:
                self.user = User.objects.get(email=self.user_email)
                print(f"Using existing user: {self.user.email}")
            except User.DoesNotExist:
                print(f"User {self.user_email} not found")
                return False
        else:
            # Create or get a test user
            self.user, created = User.objects.get_or_create(
                email="test@example.com", defaults={"username": "testuser", "first_name": "Test", "last_name": "User"}
            )
            if created:
                print(f"Created test user: {self.user.email}")
            else:
                print(f"Using existing test user: {self.user.email}")

        return True

    def setup_gmail_server(self):
        """Initialize Gmail MCP server"""
        self.gmail_server = get_gmail_mcp_server(str(self.user.id))
        print(f"Initialized Gmail MCP server for user {self.user.id}")
        return True

    def test_credentials_check(self):
        """Test credential validation"""
        print("\n--- Testing Credentials Check ---")
        has_creds = self.gmail_server.has_valid_credentials()
        print(f"Has valid credentials: {has_creds}")

        if not has_creds:
            print("No valid credentials found. You need to authenticate first.")
            print("Use the frontend to authenticate or manually place credentials.")
            return False

        return True

    def test_service_initialization(self):
        """Test Gmail service initialization"""
        print("\n--- Testing Service Initialization ---")
        success = self.gmail_server.initialize_service()
        print(f"Service initialized: {success}")
        return success

    async def test_list_labels(self):
        """Test listing Gmail labels"""
        print("\n--- Testing List Labels ---")
        try:
            result = await self.gmail_server.list_labels()
            if "error" in result:
                print(f"Error: {result['error']}")
                return False

            labels = result.get("labels", [])
            print(f"Found {len(labels)} labels:")
            for label in labels[:5]:  # Show first 5 labels
                print(f"  - {label.get('name', 'Unknown')} (ID: {label.get('id', 'Unknown')})")

            if len(labels) > 5:
                print(f"  ... and {len(labels) - 5} more")

            return True
        except Exception as e:
            print(f"Exception: {e}")
            return False

    async def test_search_emails(self):
        """Test searching emails"""
        print("\n--- Testing Search Emails ---")
        try:
            # Search for recent emails in inbox
            result = await self.gmail_server.search_emails(query="in:inbox", max_results=3)

            if "error" in result:
                print(f"Error: {result['error']}")
                return False

            messages = result.get("messages", [])
            print(f"Found {result.get('total_count', 0)} emails:")

            for msg in messages:
                print(f"  - Subject: {msg.get('subject', 'No Subject')}")
                print(f"    From: {msg.get('from', 'Unknown')}")
                print(f"    Date: {msg.get('date', 'Unknown')}")
                print(f"    ID: {msg.get('id', 'Unknown')}")
                print()

            return True
        except Exception as e:
            print(f"Exception: {e}")
            return False

    async def test_read_email(self, message_id=None):
        """Test reading a specific email"""
        print("\n--- Testing Read Email ---")

        if not message_id:
            # First get a message ID from search
            search_result = await self.gmail_server.search_emails(query="in:inbox", max_results=1)

            if "error" in search_result or not search_result.get("messages"):
                print("No emails found to read")
                return False

            message_id = search_result["messages"][0]["id"]

        try:
            result = await self.gmail_server.read_email(message_id)

            if "error" in result:
                print(f"Error: {result['error']}")
                return False

            print(f"Email Details:")
            print(f"  Subject: {result.get('subject', 'No Subject')}")
            print(f"  From: {result.get('from', 'Unknown')}")
            print(f"  To: {result.get('to', 'Unknown')}")
            print(f"  Date: {result.get('date', 'Unknown')}")
            print(f"  Body length: {len(result.get('body', ''))}")
            print(f"  Attachments: {len(result.get('attachments', []))}")

            return True
        except Exception as e:
            print(f"Exception: {e}")
            return False

    async def test_send_email(self, test_recipient=None):
        """Test sending an email"""
        print("\n--- Testing Send Email ---")

        if not test_recipient:
            test_recipient = self.user.email

        try:
            result = await self.gmail_server.send_email(
                to=[test_recipient],
                subject="Test Email from LifeLine MCP",
                body="This is a test email sent from the LifeLine Gmail MCP connector.\n\nIf you receive this, the integration is working correctly!",
                mime_type="text/plain",
            )

            if "error" in result:
                print(f"Error: {result['error']}")
                return False

            print(f"Email sent successfully!")
            print(f"  Message ID: {result.get('message_id', 'Unknown')}")
            print(f"  Thread ID: {result.get('thread_id', 'Unknown')}")

            return True
        except Exception as e:
            print(f"Exception: {e}")
            return False

    def test_database_integration(self):
        """Test database integration"""
        print("\n--- Testing Database Integration ---")

        # Check if connector exists
        try:
            connector = MCPConnector.objects.get(user=self.user, connector_type="gmail")
            print(f"Found existing connector: {connector}")
        except MCPConnector.DoesNotExist:
            # Create connector
            connector = MCPConnector.objects.create(
                user=self.user,
                connector_type="gmail",
                name="Gmail Test",
                status="active",
                scopes=[
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.modify",
                    "https://www.googleapis.com/auth/gmail.labels",
                ],
            )
            print(f"Created new connector: {connector}")

        # Check recent operations
        operations = MCPOperation.objects.filter(connector=connector).order_by("-started_at")[:5]

        print(f"Recent operations ({len(operations)}):")
        for op in operations:
            print(f"  - {op.operation_type}: {op.status} ({op.started_at})")

        return True

    async def run_all_tests(self, include_send_test=False, test_recipient=None):
        """Run all tests"""
        print("=== Gmail MCP Integration Test ===")

        # Setup
        if not self.setup_user():
            return False

        if not self.setup_gmail_server():
            return False

        # Test credentials
        if not self.test_credentials_check():
            return False

        # Test service initialization
        if not self.test_service_initialization():
            return False

        # Test database integration
        if not self.test_database_integration():
            return False

        # Test operations
        tests = [
            self.test_list_labels(),
            self.test_search_emails(),
            self.test_read_email(),
        ]

        if include_send_test:
            tests.append(self.test_send_email(test_recipient))

        results = await asyncio.gather(*tests, return_exceptions=True)

        # Summary
        print("\n=== Test Summary ===")
        test_names = ["List Labels", "Search Emails", "Read Email"]
        if include_send_test:
            test_names.append("Send Email")

        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"{test_names[i]}: FAILED ({result})")
            elif result:
                print(f"{test_names[i]}: PASSED")
                success_count += 1
            else:
                print(f"{test_names[i]}: FAILED")

        print(f"\nPassed: {success_count}/{len(results)} tests")
        return success_count == len(results)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test Gmail MCP integration")
    parser.add_argument("--user-email", help="Email of user to test with")
    parser.add_argument("--send-test", action="store_true", help="Include send email test")
    parser.add_argument("--test-recipient", help="Recipient for send test (defaults to user email)")

    args = parser.parse_args()

    tester = GmailMCPTester(args.user_email)

    try:
        success = asyncio.run(
            tester.run_all_tests(include_send_test=args.send_test, test_recipient=args.test_recipient)
        )

        if success:
            print("\n✅ All tests passed! Gmail MCP integration is working correctly.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Check the output above for details.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
