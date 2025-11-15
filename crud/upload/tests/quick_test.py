#!/usr/bin/env python
"""
Quick start script for testing the upload endpoint.
This script helps you run the API and tests easily.
"""

import subprocess
import sys
from pathlib import Path


def print_banner() -> None:
    """Print welcome banner."""
    print(
        """
    ╔════════════════════════════════════════════════════════════════╗
    ║                   Upload Testing - Quick Start                 ║
    ╚════════════════════════════════════════════════════════════════╝
    """
    )


def check_api_running() -> bool:
    """Check if API is running."""
    try:
        import requests

        response = requests.get("http://127.0.0.1:8000/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def show_menu() -> str:
    """Show menu and get user choice."""
    print(
        """
    What would you like to do?

    1. Start the API server
    2. Run manual tests (easy, interactive)
    3. Run automated tests (pytest)
    4. Run specific test type
    5. Exit

    """
    )
    return input("Enter choice (1-5): ").strip()


def start_api() -> None:
    """Start the API server."""
    print("\n🚀 Starting API server...")
    print("   Running: python run_app.py")
    print("   API will be available at: http://127.0.0.1:8000")
    print("   Press Ctrl+C to stop\n")
    try:
        subprocess.run([sys.executable, "run_app.py"], cwd=str(Path(__file__).parent))
    except KeyboardInterrupt:
        print("\n\n✋ API server stopped")


def run_manual_tests() -> None:
    """Run manual tests."""
    if not check_api_running():
        print("\n❌ API is not running!")
        print("   Please start the API first (option 1)")
        return

    print("\n🧪 Running manual tests...")
    print("   This will run all upload tests with clear results\n")
    try:
        subprocess.run(
            [sys.executable, "test_upload_manual.py"], cwd=str(Path(__file__).parent)
        )
    except KeyboardInterrupt:
        print("\n\n✋ Tests stopped")


def run_pytest() -> None:
    """Run pytest tests."""
    if not check_api_running():
        print("\n❌ API is not running!")
        print("   Please start the API first (option 1)")
        return

    print("\n🧪 Running pytest tests...")
    print("   Running: pytest tests/test_upload_endpoint.py -v\n")
    try:
        subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_upload_endpoint.py", "-v"],
            cwd=str(Path(__file__).parent),
        )
    except KeyboardInterrupt:
        print("\n\n✋ Tests stopped")


def run_specific_test() -> None:
    """Run specific test type."""
    if not check_api_running():
        print("\n❌ API is not running!")
        print("   Please start the API first (option 1)")
        return

    print("\nAvailable test types:")
    print("  • all         - All tests")
    print("  • basic       - Basic upload tests")
    print("  • metadata    - Metadata and sensitive model tests")
    print("  • validation  - Validation and error handling tests")
    print("  • sequential  - Multiple upload tests")
    print("  • special     - Special characters tests")

    test_type = input("\nEnter test type: ").strip().lower()

    if test_type not in [
        "all",
        "basic",
        "metadata",
        "validation",
        "sequential",
        "special",
    ]:
        print(f"❌ Unknown test type: {test_type}")
        return

    print(f"\n🧪 Running {test_type} tests...\n")
    try:
        subprocess.run(
            [sys.executable, "test_upload_manual.py", test_type],
            cwd=str(Path(__file__).parent),
        )
    except KeyboardInterrupt:
        print("\n\n✋ Tests stopped")


def main() -> None:
    """Main menu loop."""
    print_banner()

    while True:
        # Check API status
        if check_api_running():
            print("✅ API is running on http://127.0.0.1:8000")
        else:
            print("⚠️  API is not running")

        choice = show_menu()

        if choice == "1":
            start_api()
        elif choice == "2":
            run_manual_tests()
        elif choice == "3":
            run_pytest()
        elif choice == "4":
            run_specific_test()
        elif choice == "5":
            print("\n👋 Goodbye!\n")
            sys.exit(0)
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
        sys.exit(0)
