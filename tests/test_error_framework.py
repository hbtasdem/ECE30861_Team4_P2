# #!/usr/bin/env python3
# """
# Simple test script to demonstrate the error handling framework.

# This script shows basic usage of the error handling framework
# without modifying any existing project files.
# """

# import os
# import sys

# # Add phase1metrics directory to path
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# from error_handling import (  # noqa: E402  # type: ignore[import-not-found]
#     ErrorCode, ErrorHandler, ErrorSeverity, HuggingFaceError, ValidationError,
#     create_error_summary, graceful_fallback, retry_on_error, safe_execute,
#     setup_error_logging, validate_model_id)


# def test_validation() -> None:
#     """Test input validation."""
#     print("=== Testing Input Validation ===")

#     # Valid model ID
#     try:
#         result = validate_model_id("author/model-name")
#         print(f"✅ Valid model ID: {result}")
#     except ValidationError as e:
#         print(f"❌ Unexpected error: {e}")

#     # Invalid model ID
#     try:
#         validate_model_id("invalid-format")
#     except ValidationError as e:
#         print(f"✅ Caught validation error: {e.error_code.value}")
#         print(f"   Severity: {e.severity.value}")
#         print(f"   Suggestion: {e.recovery_suggestion}")

#     print()


# def test_graceful_fallback() -> None:
#     """Test graceful fallback decorator."""
#     print("=== Testing Graceful Fallback ===")

#     @graceful_fallback(fallback_value=0, log_errors=True)  # type: ignore[misc]
#     def risky_function(value: str) -> int:
#         if value == "error":
#             raise HuggingFaceError(
#                 ErrorCode.HF_MODEL_NOT_FOUND,
#                 "Simulated model not found",
#                 model_id=value
#             )
#         return len(value)

#     # Success case
#     result1 = risky_function("hello")
#     print(f"✅ Success case: {result1}")

#     # Failure case with fallback
#     result2 = risky_function("error")
#     print(f"✅ Failure case (with fallback): {result2}")

#     print()


# def test_retry_mechanism() -> None:
#     """Test retry mechanism."""
#     print("=== Testing Retry Mechanism ===")

#     class AttemptCounter:
#         def __init__(self) -> None:
#             self.count = 0

#     counter = AttemptCounter()

#     @retry_on_error(max_retries=2, delay=0.1)  # type: ignore[misc]
#     def flaky_function() -> str:
#         counter.count += 1

#         if counter.count < 2:
#             raise HuggingFaceError(
#                 ErrorCode.HF_REPOSITORY_ACCESS_ERROR,
#                 f"Attempt {counter.count} failed"
#             )

#         return f"Success on attempt {counter.count}"

#     try:
#         result = flaky_function()
#         print(f"✅ Retry success: {result}")
#     except HuggingFaceError as e:
#         print(f"❌ Retry failed: {e}")

#     print()


# def test_error_context_manager() -> None:
#     """Test error context manager."""
#     print("=== Testing Error Context Manager ===")

#     with ErrorHandler(
#         error_type=ValidationError,
#         fallback_value="default",
#         log_errors=True
#     ) as handler:
#         # This will succeed
#         validate_model_id("author/model")
#         print("✅ Validation succeeded")

#     print(f"   Error occurred: {handler.error_occurred}")

#     with ErrorHandler(
#         error_type=ValidationError,
#         fallback_value="default",
#         log_errors=True
#     ) as handler:
#         # This will fail
#         validate_model_id("invalid")

#     print(f"✅ Error handled: {handler.error_occurred}")
#     print(f"   Fallback result: {handler.get_result()}")

#     print()


# def test_safe_execution() -> None:
#     """Test safe execution."""
#     print("=== Testing Safe Execution ===")

#     def risky_function(value: str) -> str:
#         if value == "error":
#             raise ValueError("Simulated error")
#         return f"Processed: {value}"

#     # Success case
#     result1 = safe_execute(risky_function, "hello", default_value="fallback")
#     print(f"✅ Success: {result1}")

#     # Failure case
#     result2 = safe_execute(risky_function, "error", default_value="fallback")
#     print(f"✅ Failure (with fallback): {result2}")

#     print()


# def test_error_summary() -> None:
#     """Test error summary generation."""
#     print("=== Testing Error Summary ===")

#     errors = [
#         ValidationError(
#             ErrorCode.INVALID_MODEL_ID,
#             "Invalid model ID",
#             severity=ErrorSeverity.MEDIUM
#         ),
#         HuggingFaceError(
#             ErrorCode.HF_MODEL_NOT_FOUND,
#             "Model not found",
#             severity=ErrorSeverity.HIGH
#         ),
#         ValidationError(
#             ErrorCode.INVALID_INPUT_DATA,
#             "Invalid input",
#             severity=ErrorSeverity.LOW
#         ),
#     ]

#     summary = create_error_summary(errors)
#     print("✅ Error Summary:")
#     for key, value in summary.items():
#         print(f"   {key}: {value}")

#     print()


# def main() -> None:
#     """Run all tests."""
#     print("🚀 Error Handling Framework Test")
#     print("=" * 50)

#     # Set up logging
#     setup_error_logging("INFO")
#     print("📝 Logging configured (check errors.log file)")
#     print()

#     # Run tests
#     test_validation()
#     test_graceful_fallback()
#     test_retry_mechanism()
#     test_error_context_manager()
#     test_safe_execution()
#     test_error_summary()

#     print("✅ All tests completed!")
#     print()
#     print("📋 Framework Features Demonstrated:")
#     print("   • Input validation with detailed error messages")
#     print("   • Graceful fallback when operations fail")
#     print("   • Automatic retry with exponential backoff")
#     print("   • Error context managers for safe execution")
#     print("   • Safe execution with fallback values")
#     print("   • Error summary generation for debugging")
#     print("   • Structured logging with severity levels")


# if __name__ == "__main__":
#     main()
