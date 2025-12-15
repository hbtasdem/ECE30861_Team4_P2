#!/usr/bin/env python3
"""
LOCAL REGEX ENDPOINT TESTER
============================

Tests against LOCAL test server running on http://localhost:8000

SETUP:
1. Start local server: python local_test_server.py
2. Run this test: python test_regex_local.py all
"""

import json
import requests
from typing import Dict, Any

# ===========================================================================
# CONFIGURATION
# ===========================================================================

SERVER_URL = "http://localhost:8000"  # LOCAL SERVER
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwibmFtZSI6ImVjZTMwODYxZGVmYXVsdGFkbWludXNlciIsImlzX2FkbWluIjp0cnVlLCJleHAiOjE3NjU3NzkzNTZ9.o75fVtL8U8bz3xalRbCVT0MhjQ8M1qOpt4GpMZmqaGc"

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
            response = requests.post(url, headers=self.headers, json=payload, timeout=5)
            
            print(f"Actual Status: {response.status_code}")
            
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
                print("✅ PASS")
                self.passed += 1
                return {"status": "PASS", "response": response.json()}
            else:
                print(f"❌ FAIL - Expected {expected_status}, got {response.status_code}")
                self.failed += 1
                return {"status": "FAIL", "response": response.json()}
                
        except requests.exceptions.ConnectionError:
            print("❌ ERROR - Cannot connect to server!")
            print("   Make sure local server is running: python local_test_server.py")
            self.failed += 1
            return {"status": "ERROR", "error": "Connection refused"}
        except Exception as e:
            print(f"❌ ERROR - {e}")
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
        if total > 0:
            print(f"Success Rate: {(self.passed/total*100):.1f}%")
        print(f"{'='*70}\n")

# ===========================================================================
# TEST CASES
# ===========================================================================

def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*70)
    print("LOCAL REGEX ENDPOINT TESTS")
    print("="*70)
    print(f"Server: {SERVER_URL}")
    print(f"Endpoint: POST /artifact/byRegEx")
    print("="*70)
    
    tester = RegexTester(SERVER_URL, AUTH_TOKEN)
    
    # Check if server is running
    try:
        health = requests.get(f"{SERVER_URL}/", timeout=2)
        if health.status_code == 200:
            print("✅ Server is running\n")
        else:
            print("⚠️  Server returned unexpected status\n")
    except:
        print("❌ ERROR: Cannot connect to local server!")
        print("   Start it first: python local_test_server.py\n")
        return
    
    # Success cases
    tester.test_regex(
        pattern="bert",
        expected_status=200,
        description="Basic search - 'bert'"
    )
    
    tester.test_regex(
        pattern="BERT",
        expected_status=200,
        description="Case insensitive - 'BERT'"
    )
    
    tester.test_regex(
        pattern=".*",
        expected_status=200,
        description="Match all"
    )
    
    tester.test_regex(
        pattern="^bert",
        expected_status=200,
        description="Start anchor - '^bert'"
    )
    
    tester.test_regex(
        pattern="model$",
        expected_status=200,
        description="End anchor - 'model$'"
    )
    
    tester.test_regex(
        pattern="distil.*squad",
        expected_status=200,
        description="Complex pattern"
    )
    
    # Error cases
    tester.test_regex(
        pattern="xyz123nonexistent",
        expected_status=404,
        description="No matches - 404"
    )
    
    tester.test_regex(
        pattern="[invalid",
        expected_status=400,
        description="Invalid regex - 400"
    )
    
    # Print summary
    tester.print_summary()

def test_basic():
    """Quick basic test."""
    tester = RegexTester(SERVER_URL, AUTH_TOKEN)
    tester.test_regex("bert", 200, "Basic 'bert' search")
    tester.print_summary()

def interactive():
    """Interactive mode."""
    print("\n" + "="*70)
    print("INTERACTIVE MODE - Enter patterns to test")
    print("="*70)
    print("Type 'quit' to exit\n")
    
    tester = RegexTester(SERVER_URL, AUTH_TOKEN)
    
    while True:
        try:
            pattern = input("\nRegex pattern: ").strip()
            if pattern.lower() in ['quit', 'exit', 'q']:
                break
            if not pattern:
                continue
            
            tester.test_regex(pattern, 200, f"Custom: {pattern}")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break

# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "all":
            run_all_tests()
        elif mode == "basic":
            test_basic()
        elif mode == "i" or mode == "interactive":
            interactive()
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python test_regex_local.py [all|basic|interactive]")
    else:
        run_all_tests()