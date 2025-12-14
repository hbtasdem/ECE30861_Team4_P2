#!/usr/bin/env python3
"""
Interactive Regex Endpoint Tester
==================================

Tests the POST /artifact/byRegEx endpoint against your live server.
Run this from your local Windows machine to validate server behavior.

Requirements: pip install requests
"""

import json
import requests
from typing import Dict, Any, List

# ===========================================================================
# CONFIGURATION
# ===========================================================================

SERVER_URL = "http://3.22.221.210:8000"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwibmFtZSI6ImVjZTMwODYxZGVmYXVsdGFkbWludXNlciIsImlzX2FkbWluIjp0cnVlLCJleHAiOjE3NjU3NzkzNTZ9.o75fVtL8U8bz3xalRbCVT0MhjQ8M1qOpt4GpMZmqaGc"

# Update this token if expired!
# Get new token: curl -X POST http://3.22.221.210:8000/authenticate -d '{"username":"ece30861defaultadminuser","password":"correcthorsebatterystaple123(!__+@**(A'\''\"`;DROP TABLE artifacts;"}'


# ===========================================================================
# TEST RUNNER
# ===========================================================================

class RegexTester:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "X-Authorization": f"bearer {token}"
        }
        self.passed = 0
        self.failed = 0
    
    def test_regex(self, pattern: str, expected_status: int, description: str) -> Dict[str, Any]:
        """Test a regex pattern and return results."""
        url = f"{self.base_url}/artifact/byRegEx"
        payload = {"regex": pattern}
        
        print(f"\n{'='*70}")
        print(f"TEST: {description}")
        print(f"{'='*70}")
        print(f"Pattern: {pattern}")
        print(f"Expected Status: {expected_status}")
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            
            print(f"\nActual Status: {response.status_code}")
            
            # Pretty print response
            if response.status_code == 200:
                results = response.json()
                print(f"Results: {len(results)} artifacts found")
                for i, artifact in enumerate(results, 1):
                    print(f"  {i}. {artifact['name']} (id: {artifact['id'][:16]}..., type: {artifact['type']})")
            else:
                error = response.json()
                print(f"Error: {error.get('detail', 'Unknown error')}")
            
            # Check if status matches
            if response.status_code == expected_status:
                print("✅ PASS - Status code matches")
                self.passed += 1
                return {"status": "PASS", "response": response.json()}
            else:
                print(f"❌ FAIL - Expected {expected_status}, got {response.status_code}")
                self.failed += 1
                return {"status": "FAIL", "response": response.json()}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR - Request failed: {e}")
            self.failed += 1
            return {"status": "ERROR", "error": str(e)}
    
    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success Rate: {(self.passed/total*100) if total > 0 else 0:.1f}%")
        print(f"{'='*70}\n")


# ===========================================================================
# TEST CASES
# ===========================================================================

def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*70)
    print("REGEX ENDPOINT INTEGRATION TESTS")
    print("="*70)
    print(f"Server: {SERVER_URL}")
    print(f"Endpoint: POST /artifact/byRegEx")
    print("="*70)
    
    tester = RegexTester(SERVER_URL, AUTH_TOKEN)
    
    # ===== SUCCESS CASES (200) =====
    
    tester.test_regex(
        pattern="bert",
        expected_status=200,
        description="Basic search - should find artifacts with 'bert' in name"
    )
    
    tester.test_regex(
        pattern="BERT",
        expected_status=200,
        description="Case insensitive - should match 'bert', 'Bert', etc."
    )
    
    tester.test_regex(
        pattern=".*",
        expected_status=200,
        description="Match all - should return all artifacts"
    )
    
    tester.test_regex(
        pattern="^bert",
        expected_status=200,
        description="Start anchor - only names starting with 'bert'"
    )
    
    tester.test_regex(
        pattern="model$",
        expected_status=200,
        description="End anchor - only names ending with 'model'"
    )
    
    tester.test_regex(
        pattern="distil.*squad",
        expected_status=200,
        description="Complex pattern - 'distil' followed by 'squad'"
    )
    
    # ===== ERROR CASES =====
    
    tester.test_regex(
        pattern="xyz123nonexistent",
        expected_status=404,
        description="No matches - should return 404"
    )
    
    tester.test_regex(
        pattern="[invalid",
        expected_status=400,
        description="Invalid regex - unclosed bracket"
    )
    
    tester.test_regex(
        pattern="(unclosed",
        expected_status=400,
        description="Invalid regex - unclosed parenthesis"
    )
    
    # Print summary
    tester.print_summary()


# ===========================================================================
# INDIVIDUAL TEST FUNCTIONS
# ===========================================================================

def test_basic_search():
    """Test basic 'bert' search."""
    tester = RegexTester(SERVER_URL, AUTH_TOKEN)
    tester.test_regex("bert", 200, "Basic 'bert' search")


def test_match_all():
    """Test matching all artifacts."""
    tester = RegexTester(SERVER_URL, AUTH_TOKEN)
    tester.test_regex(".*", 200, "Match all artifacts")


def test_invalid_regex():
    """Test invalid regex pattern."""
    tester = RegexTester(SERVER_URL, AUTH_TOKEN)
    tester.test_regex("[invalid", 400, "Invalid regex pattern")


def test_no_matches():
    """Test pattern with no matches."""
    tester = RegexTester(SERVER_URL, AUTH_TOKEN)
    tester.test_regex("xyz123impossible", 404, "No matching artifacts")


def interactive_test():
    """Interactive mode - test your own patterns."""
    print("\n" + "="*70)
    print("INTERACTIVE REGEX TESTER")
    print("="*70)
    print("Enter regex patterns to test (or 'quit' to exit)")
    print("="*70 + "\n")
    
    tester = RegexTester(SERVER_URL, AUTH_TOKEN)
    
    while True:
        try:
            pattern = input("\nEnter regex pattern: ").strip()
            
            if pattern.lower() in ['quit', 'exit', 'q']:
                print("\nExiting...")
                break
            
            if not pattern:
                print("Empty pattern - please enter a regex")
                continue
            
            # Test the pattern
            result = tester.test_regex(
                pattern=pattern,
                expected_status=200,  # We expect success, but any status is OK
                description=f"Custom pattern: {pattern}"
            )
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "all":
            run_all_tests()
        elif mode == "basic":
            test_basic_search()
        elif mode == "matchall":
            test_match_all()
        elif mode == "invalid":
            test_invalid_regex()
        elif mode == "nomatches":
            test_no_matches()
        elif mode == "interactive" or mode == "i":
            interactive_test()
        else:
            print(f"Unknown mode: {mode}")
            print_usage()
    else:
        # Default: run all tests
        run_all_tests()


def print_usage():
    """Print usage information."""
    print("""
Usage: python test_regex_live.py [mode]

Modes:
  all         - Run all test cases (default)
  basic       - Test basic 'bert' search
  matchall    - Test match all pattern
  invalid     - Test invalid regex
  nomatches   - Test pattern with no matches
  interactive - Interactive mode (enter your own patterns)
  i           - Short for interactive

Examples:
  python test_regex_live.py all
  python test_regex_live.py interactive
  python test_regex_live.py
""")


if __name__ == "__main__":
    main()