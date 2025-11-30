import docker
import re
import os
import sys
import time
import google.generativeai as genai
from typing import Tuple, Optional

class ReproducibilityChecker:
    """
    Checks if model card demonstration code is reproducible.
    Scores: 0 (no code/doesn't run), 0.5 (runs with AI debugging), 1 (runs perfectly)
    """
    
    def __init__(self, genai_api_key: str):
        self.client = docker.from_env()
        genai.configure(api_key=genai_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.timeout = 300  # 5 minutes max execution time
        
    def extract_code_from_model_card(self, model_card_content: str) -> Optional[str]:
        """
        Extract Python code blocks from model card (README.md).
        Returns the first substantial code block found.
        """
        # Find Python code blocks in markdown
        pattern = r'```python\n(.*?)```'
        matches = re.findall(pattern, model_card_content, re.DOTALL)
        
        if not matches:
            # Try generic code blocks
            pattern = r'```\n(.*?)```'
            matches = re.findall(pattern, model_card_content, re.DOTALL)
        
        # Find the first block with actual code (not just imports)
        for code in matches:
            if len(code.strip()) > 20:  # Substantial code
                return code.strip()
        
        return None
    
    def create_test_script(self, code: str, requirements: str = "") -> str:
        """
        Create a complete Python script with error handling.
        """
        script = f"""
import sys
import traceback

# Install requirements if needed
{f"# Requirements: {requirements}" if requirements else ""}

try:
    # User's demonstration code
{self._indent_code(code, 4)}
    
    print("\\n=== CODE EXECUTED SUCCESSFULLY ===")
    sys.exit(0)
    
except Exception as e:
    print(f"\\n=== ERROR OCCURRED ===")
    print(f"Error Type: {{type(e).__name__}}")
    print(f"Error Message: {{str(e)}}")
    print("\\n=== TRACEBACK ===")
    traceback.print_exc()
    sys.exit(1)
"""
        return script
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Helper to indent code blocks."""
        indent = " " * spaces
        return "\n".join(indent + line for line in code.split("\n"))
    
    def run_code_in_docker(self, code: str, image: str = "python:3.9-slim") -> Tuple[bool, str]:
        """
        Run code in isolated Docker container.
        Returns (success, output/error).
        """
        script = self.create_test_script(code)
        container_name = f"repro_test_{int(time.time())}"
        
        try:
            # Create and run container
            container = self.client.containers.run(
                image=image,
                command=["python", "-c", script],
                name=container_name,
                detach=False,
                remove=True,
                mem_limit="512m",
                network_mode="bridge",
                stdout=True,
                stderr=True,
                timeout=self.timeout
            )
            
            output = container.decode('utf-8')
            success = "CODE EXECUTED SUCCESSFULLY" in output
            return success, output
            
        except docker.errors.ContainerError as e:
            return False, e.stderr.decode('utf-8')
        except Exception as e:
            return False, str(e)
    
    def get_ai_fix(self, code: str, error_output: str, attempt: int = 1) -> Optional[str]:
        """
        Use Gemini to debug and fix the code.
        """
        prompt = f"""You are an expert Python debugger. Return only fixed code, no explanations.

Original Code:
```python
{code}
```

Error Output:
```
{error_output}
```

Please provide ONLY the fixed Python code that resolves this error. 
Do not include explanations, just the corrected code in a single code block.
If the error is due to missing packages, add pip install commands as comments at the top.

Attempt {attempt}/3
"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000,
                )
            )
            
            fixed_code = response.text
            
            # Extract code from markdown if present
            if "```python" in fixed_code:
                match = re.search(r'```python\n(.*?)```', fixed_code, re.DOTALL)
                if match:
                    fixed_code = match.group(1)
            elif "```" in fixed_code:
                match = re.search(r'```\n(.*?)```', fixed_code, re.DOTALL)
                if match:
                    fixed_code = match.group(1)
            
            return fixed_code.strip()
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            return None
    
    def check_reproducibility(self, model_card_path: str) -> Tuple[float, str]:
        """
        Main method to check reproducibility of a model.
        
        Returns:
            (score, explanation) where score is 0, 0.5, or 1
        """
        # Read model card
        try:
            with open(model_card_path, 'r', encoding='utf-8') as f:
                model_card = f.read()
        except Exception as e:
            return 0.0, f"Could not read model card: {e}"
        
        # Extract code
        code = self.extract_code_from_model_card(model_card)
        if not code:
            return 0.0, "No demonstration code found in model card"
        
        print(f"Extracted code ({len(code)} chars)")
        
        # First attempt: run as-is
        print("Attempting to run code as-is...")
        success, output = self.run_code_in_docker(code)
        
        if success:
            return 1.0, "Code runs successfully without modifications"
        
        print(f"Initial run failed. Error: {output[:200]}...")
        
        # Second attempt: with AI debugging
        print("Attempting AI-assisted debugging...")
        max_attempts = 3
        
        for attempt in range(1, max_attempts + 1):
            print(f"Debug attempt {attempt}/{max_attempts}")
            
            fixed_code = self.get_ai_fix(code, output, attempt)
            if not fixed_code:
                continue
            
            success, output = self.run_code_in_docker(fixed_code)
            
            if success:
                return 0.5, f"Code runs after AI debugging (attempt {attempt}/{max_attempts})"
            
            code = fixed_code  # Use fixed version for next iteration
        
        return 0.0, f"Code does not run even after {max_attempts} AI debugging attempts"


# Example usage
if __name__ == "__main__":
    # Initialize checker
    checker = ReproducibilityChecker(
        genai_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    # Check a model
    score, explanation = checker.check_reproducibility("path/to/README.md")
    
    print(f"\nReproducibility Score: {score}")
    print(f"Explanation: {explanation}")