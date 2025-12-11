# #!/usr/bin/env python
# """
# Quick start testing script for upload and download endpoints.
#
# Per OpenAPI v3.4.4 - Interactive Testing Tool
#
# PURPOSE:
# Provides interactive menu-driven testing interface for FastAPI upload endpoints.
# Allows users to start API server, run manual tests, and execute automated tests.
#
# USAGE:
#     python tests/quick_test.py
#
# FEATURES:
# 1. Start API Server
#    - Launches uvicorn on http://127.0.0.1:8000
#    - Enables auto-reload for development
#    - Shows access points (API, docs, redoc)
#
# 2. Manual Testing
#    - Interactive test suite for upload endpoints
#    - Easy walkthrough of registration and upload flows
#    - Clear result reporting with pass/fail indicators
#
# 3. Automated Testing
#    - Runs pytest test suite
#    - Generates detailed test reports
#    - Suitable for CI/CD pipelines
#
# 4. Specific Test Types
#    - all: Run complete test suite
#    - basic: Basic upload tests
#    - metadata: Metadata handling tests
#    - validation: Input validation tests
#    - sequential: Multiple sequential uploads
#    - special: Special characters handling
#
# MENU OPTIONS:
#     1. Start the API server
#     2. Run manual tests (easy, interactive)
#     3. Run automated tests (pytest)
#     4. Run specific test type
#     5. Exit
#
# ENDPOINTS TESTED:
#     Phase 2 (Baseline):
#     - POST /auth/register: User registration
#     - PUT /authenticate: User login
#     - POST /api/models/upload: Register model from URL
#     - GET /api/models/enumerate: List models
#
#     Phase 3 (File Upload):
#     - POST /api/models/upload-file: Single file upload
#     - POST /api/models/check-duplicate: Duplicate detection
#     - POST /api/models/validate: File validation
#     - GET /api/models/{id}/download: File download
#
#     Phase 4 (Batch & Chunked):
#     - POST /api/models/upload-batch: Batch upload
#     - POST /api/models/chunked-upload/init: Start chunked upload
#     - POST /api/models/chunked-upload/{id}/chunk: Upload chunk
#     - GET /api/models/chunked-upload/{id}/progress: Track progress
#
# REQUIREMENTS:
#     - Python 3.8+
#     - FastAPI installed
#     - Pytest installed
#     - All dependencies from requirements.txt
#
# TROUBLESHOOTING:
#     Port 8000 already in use:
#     - Edit run_app.py and change port number
#     - Or: kill existing process and retry
#
#     Tests fail:
#     - Check API is running (option 1)
#     - Check logs for error messages
#     - Verify database is accessible
#
#     Connection refused:
#     - Ensure API server is running
#     - Check http://127.0.0.1:8000/docs is accessible
#
# SPEC REFERENCES:
#     Section 3.1: Authentication endpoints
#     Section 3.2: Model registration endpoints
#     Section 3.3: File upload endpoints
#     Section 3.4: Batch and chunked uploads
# """

# import subprocess
# import sys
# from pathlib import Path


# def print_banner() -> None:
#     """Print welcome banner."""
#     print("""
#     ╔════════════════════════════════════════════════════════════════╗
#     ║                   Upload Testing - Quick Start                 ║
#     ╚════════════════════════════════════════════════════════════════╝
#     """)


# def check_api_running() -> bool:
#     """Check if API is running."""
#     try:
#         import requests
#         response = requests.get("http://127.0.0.1:8000/health", timeout=2)
#         return response.status_code == 200
#     except Exception:
#         return False


# def show_menu() -> str:
#     """Show menu and get user choice."""
#     print("""
#     What would you like to do?

#     1. Start the API server
#     2. Run manual tests (easy, interactive)
#     3. Run automated tests (pytest)
#     4. Run specific test type
#     5. Exit

#     """)
#     return input("Enter choice (1-5): ").strip()


# def start_api() -> None:
#     """Start the API server."""
#     print("\nStarting API server...")
#     print("   Running: python run_app.py")
#     print("   API will be available at: http://127.0.0.1:8000")
#     print("   Press Ctrl+C to stop\n")
#     try:
#         subprocess.run([sys.executable, "run_app.py"], cwd=str(Path(__file__).parent))
#     except KeyboardInterrupt:
#         print("\n\nAPI server stopped")


# def run_manual_tests() -> None:
#     """Run manual tests."""
#     if not check_api_running():
#         print("\nAPI is not running!")
#         print("   Please start the API first (option 1)")
#         return

#     print("\nRunning manual tests...")
#     print("   This will run all upload tests with clear results\n")
#     try:
#         subprocess.run([sys.executable, "test_upload_manual.py"], cwd=str(Path(__file__).parent))
#     except KeyboardInterrupt:
#         print("\n\nTests stopped")


# def run_pytest() -> None:
#     """Run pytest tests."""
#     if not check_api_running():
#         print("\nAPI is not running!")
#         print("   Please start the API first (option 1)")
#         return

#     print("\nRunning pytest tests...")
#     print("   Running: pytest tests/test_upload_endpoint.py -v\n")
#     try:
#         subprocess.run(
#             [sys.executable, "-m", "pytest", "tests/test_upload_endpoint.py", "-v"],
#             cwd=str(Path(__file__).parent),
#         )
#     except KeyboardInterrupt:
#         print("\n\nTests stopped")


# def run_specific_test() -> None:
#     """Run specific test type."""
#     if not check_api_running():
#         print("\nAPI is not running!")
#         print("   Please start the API first (option 1)")
#         return

#     print("\nAvailable test types:")
#     print("  • all         - All tests")
#     print("  • basic       - Basic upload tests")
#     print("  • metadata    - Metadata and sensitive model tests")
#     print("  • validation  - Validation and error handling tests")
#     print("  • sequential  - Multiple upload tests")
#     print("  • special     - Special characters tests")

#     test_type = input("\nEnter test type: ").strip().lower()

#     if test_type not in ["all", "basic", "metadata", "validation", "sequential", "special"]:
#         print(f"Unknown test type: {test_type}")
#         return

#     print(f"\nRunning {test_type} tests...\n")
#     try:
#         subprocess.run(
#             [sys.executable, "test_upload_manual.py", test_type],
#             cwd=str(Path(__file__).parent),
#         )
#     except KeyboardInterrupt:
#         print("\n\nTests stopped")


# def main() -> None:
#     """Main menu loop."""
#     print_banner()

#     while True:
#         # Check API status
#         if check_api_running():
#             print("API is running on http://127.0.0.1:8000")
#         else:
#             print("WARNING: API is not running")

#         choice = show_menu()

#         if choice == "1":
#             start_api()
#         elif choice == "2":
#             run_manual_tests()
#         elif choice == "3":
#             run_pytest()
#         elif choice == "4":
#             run_specific_test()
#         elif choice == "5":
#             print("\nGoodbye!\n")
#             sys.exit(0)
#         else:
#             print("Invalid choice. Please try again.")


# if __name__ == "__main__":
#     try:
#         main()
#     except KeyboardInterrupt:
#         print("\n\nGoodbye!\n")
#         sys.exit(0)
