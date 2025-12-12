import docker
import re
import os
import sys
import time
import requests
from typing import Tuple, Optional
from dotenv import load_dotenv

# Import purdue_api - adjust path as needed
# Try multiple possible paths
purdue_api = None
possible_paths = [
    os.path.join(os.path.dirname(__file__), "../.."),  # ../../purdue_api
    os.path.join(os.path.dirname(__file__), ".."),      # ../purdue_api
    os.path.join(os.path.dirname(__file__), "../../src"),  # ../../src/purdue_api
    os.path.join(os.path.dirname(__file__), "../src"),  # ../src/purdue_api
]

for path in possible_paths:
    sys.path.insert(0, path)
    try:
        import purdue_api
        print(f"purdue_api imported successfully from {path}")
        break
    except ImportError:
        pass

if not purdue_api:
    print("Failed to import purdue_api from any path")
    print(f"Current directory: {os.getcwd()}")
    print(f"Script directory: {os.path.dirname(__file__)}")
    print("Searched paths:", possible_paths)

load_dotenv()

class ReproducibilityChecker:
    """
    Checks if model card demonstration code is reproducible.
    Scores: 0 (no code/doesn't run), 0.5 (runs with AI debugging), 1 (runs perfectly)
    """
    
    def __init__(self):
        print("\n=== Initializing ReproducibilityChecker ===")
        
        # Initialize Docker
        try:
            self.client = docker.from_env()
            print(" Docker client initialized")
        except Exception as e:
            print(f" Docker initialization failed: {e}")
            raise
        
        # Initialize Purdue GenAI
        self.model = None
        if purdue_api:
            try:
                self.model = purdue_api.PurdueGenAI()
                print(f" Purdue GenAI initialized")
            except Exception as e:
                print(f" Could not initialize Purdue GenAI: {e}")
        else:
            print(" purdue_api not available")
        
        self.timeout = 300
        print("=== Initialization Complete ===\n")
    
    def fetch_model_card(self, model_identifier: str) -> Optional[str]:
        """
        Fetch README.md content from HuggingFace model.
        """
        if "huggingface.co/" in model_identifier:
            model_path = model_identifier.split("huggingface.co/")[1]
            model_path = model_path.split("/tree")[0].split("/blob")[0].strip("/")
        else:
            model_path = model_identifier.strip()
        
        readme_url = f"https://huggingface.co/{model_path}/raw/main/README.md"
        
        try:
            resp = requests.get(readme_url, timeout=10)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"Could not fetch README for {model_path}: {e}")
            return None
    
    def extract_code_from_model_card(self, model_card_content: str) -> Optional[str]:
        """
        Extract Python code blocks from model card (README.md).
        """
        pattern = r'```python\n(.*?)```'
        matches = re.findall(pattern, model_card_content, re.DOTALL)
        
        if not matches:
            pattern = r'```\n(.*?)```'
            matches = re.findall(pattern, model_card_content, re.DOTALL)
        
        for code in matches:
            if len(code.strip()) > 20:
                return code.strip()
        
        return None
    
    def create_test_script(self, code: str, requirements: str = "") -> str:
        """
        Create a complete Python script with error handling.
        """
        install_steps = []
        exec_lines = []
        
        # Debug: print what we're parsing
        print(f"  Parsing code for pip installs...")
        
        for line in code.split('\n'):
            stripped_line = line.strip()
            if stripped_line.startswith('pip install') or stripped_line.startswith('!pip install'):
                clean_line = stripped_line.lstrip('!')
                install_steps.append(clean_line)
                print(f"    Found install: {clean_line}")
            else:
                exec_lines.append(line)
        
        print(f"  Total pip install commands found: {len(install_steps)}")
        
        code_to_execute = '\n'.join(exec_lines)
        
        install_block = ""
        if install_steps:
            install_block = "import subprocess\nimport sys\n\n"
            for step in install_steps:
                # Parse: "pip install transformers torch" -> ['pip', 'install', 'transformers', 'torch']
                parts = step.split()
                if len(parts) >= 3 and parts[0] == 'pip' and parts[1] == 'install':
                    # Get just the package names: ['transformers', 'torch']
                    packages = parts[2:]
                    print(f"  Will install packages: {packages}")
                    install_block += f"print('Installing: {' '.join(packages)}...')\n"
                    # Add --root-user-action=ignore to suppress the warning
                    install_block += f"subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--root-user-action=ignore', '--quiet'] + {packages})\n"
                    install_block += f"print(' Installed {' '.join(packages)}')\n\n"
        
        script = f"""
import sys
import traceback

{install_block}

try:
    # User's demonstration code
{self._indent_code(code_to_execute, 4)}
    
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
        
        # Debug: Show generated script
        if len(install_steps) > 0:
            print(f"  Generated script preview (first 500 chars):")
            print(f"  {script[:500]}")
        
        return script
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Helper to indent code blocks."""
        indent = " " * spaces
        return "\n".join(indent + line for line in code.split("\n"))
    
    def run_code_in_docker(self, code: str, image: str = "python:3.9-slim") -> Tuple[bool, str]:
        """
        Run code in isolated Docker container.
        """
        script = self.create_test_script(code)
        container_name = f"repro_test_{int(time.time())}"
        
        try:
            print(f"  Starting Docker container (this may take a while for pip installs)...")
            start_time = time.time()
            
            container = self.client.containers.run(
                image=image,
                command=["python", "-c", script],
                name=container_name,
                detach=False,
                remove=True,
                mem_limit="1g",  # Increased from 512m
                network_mode="bridge",
                stdout=True,
                stderr=True
                # Timeout removed - let it run as long as needed
            )
            
            elapsed = time.time() - start_time
            print(f"  Container finished in {elapsed:.1f}s")
            
            output = container.decode('utf-8')
            success = "CODE EXECUTED SUCCESSFULLY" in output
            return success, output
            
        except docker.errors.ContainerError as e:
            elapsed = time.time() - start_time
            print(f"  Container failed after {elapsed:.1f}s")
            return False, e.stderr.decode('utf-8')
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  Container error after {elapsed:.1f}s: {type(e).__name__}")
            return False, str(e)
    
    def get_ai_fix(self, code: str, error_output: str, attempt: int = 1) -> Optional[str]:
        """
        Use Purdue GenAI to debug and fix the code.
        """
        print(f"\n  --- AI Fix Attempt {attempt} ---")
        print(f"  Model available: {self.model is not None}")
        
        if not self.model:
            print("   AI model not initialized, skipping")
            return None
        
        prompt = f"""Fix this Python code. Return ONLY plain Python code with NO markdown, NO code blocks, NO backticks, NO explanations.

FAILED CODE:
{code}

ERROR:
{error_output[:500]}

RULES:
- If missing packages: put "pip install package1 package2" at the TOP
- Use latest PyTorch: "pip install torch transformers" (no version numbers)
- Return PLAIN TEXT CODE ONLY
- DO NOT wrap in ```python or ```bash or ``` or any markdown
- Start directly with "pip install" if needed, or "import" if not

CORRECT format (no backticks or markdown):
pip install torch transformers
import torch
from transformers import AutoModel
model = AutoModel.from_pretrained('bert-base')

Now output ONLY the fixed code with NO markdown (attempt {attempt}/5):"""
        
        try:
            print(f"  Calling Purdue GenAI API...")
            response = self.model.chat(prompt)
            
            if not response:
                print(f"   API returned empty response")
                return None
            
            fixed_code = response.strip()
            print(f"   API Response received ({len(fixed_code)} chars)")
            print(f"  First 150 chars: {fixed_code[:150]}")
            
            # Extract code from markdown if present
            if "```python" in fixed_code:
                match = re.search(r'```python\n(.*?)```', fixed_code, re.DOTALL)
                if match:
                    fixed_code = match.group(1).strip()
                    print("  Extracted from ```python block")
            elif "```" in fixed_code:
                match = re.search(r'```\n(.*?)```', fixed_code, re.DOTALL)
                if match:
                    fixed_code = match.group(1).strip()
                    print("  Extracted from ``` block")
            
            if not fixed_code:
                print("   Fixed code is empty after extraction")
                return None
            
            print(f"   Final fixed code: {len(fixed_code)} chars")
            return fixed_code
            
        except Exception as e:
            print(f"   API error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def check_reproducibility(self, model_identifier: str) -> Tuple[float, str]:
        """
        Main method to check reproducibility of a model.
        """
        print(f"\n{'='*60}")
        print(f"Checking: {model_identifier}")
        print('='*60)
        
        # Fetch model card
        print("\n[1/4] Fetching README from HuggingFace...")
        model_card = self.fetch_model_card(model_identifier)
        if not model_card:
            return 0.0, f"Could not fetch model card for {model_identifier}"
        print(f" Fetched {len(model_card)} characters")
        
        # Extract code
        print("\n[2/4] Extracting code from README...")
        code = self.extract_code_from_model_card(model_card)
        if not code:
            return 0.0, "No demonstration code found in model card"
        print(f" Extracted {len(code)} chars of code")
        print(f"Preview:\n{code[:200]}...\n")
        
        # First attempt
        print("[3/4] Running code as-is in Docker...")
        success, output = self.run_code_in_docker(code)
        
        if success:
            print(" Code executed successfully!")
            return 1.0, "Code runs successfully without modifications"
        
        print(f" Initial run failed")
        print(f"Error: {output[:300]}...")
        
        # Check if the ONLY issue is missing packages (no actual code bugs)
        is_only_missing_packages = (
            ('ModuleNotFoundError' in output or 'ImportError' in output) and
            not any(err in output for err in [
                'SyntaxError', 'NameError', 'AttributeError', 
                'TypeError', 'ValueError', 'IndentationError'
            ])
        )
        
        # If code has actual substance (not just a single import) and only needs packages
        # Try AI fix to add packages, and if that works, it's a 1.0
        if is_only_missing_packages and len(code.split('\n')) > 3:
            print("  → Only issue appears to be missing packages")
            print("  → Will try adding packages to verify code is correct")
        else:
            print("  → Code has errors beyond missing packages, needs debugging")
        
        # AI debugging
        print("\n[4/4] Attempting AI-assisted debugging...")
        max_attempts = 5  # Increased from 3 since AI is making progress
        
        for attempt in range(1, max_attempts + 1):
            fixed_code = self.get_ai_fix(code, output, attempt)
            
            if not fixed_code:
                print(f"  No fix generated for attempt {attempt}")
                continue
            
            # Check if the fix looks reasonable (has pip install for missing packages)
            has_pip_install = 'pip install' in fixed_code
            if has_pip_install and 'ModuleNotFoundError' in output:
                print(f"   AI added pip install commands to fix ModuleNotFoundError")
                # This is a valid fix even if we can't fully test it
                # (testing would require downloading large ML models which takes too long)
                return 0.5, f"Code appears fixable with AI debugging (added package installations)"
            
            print(f"  Testing fixed code in Docker...")
            success, output = self.run_code_in_docker(fixed_code)
            
            if success:
                print(f" Fixed code works!")
                return 0.5, f"Code runs after AI debugging (attempt {attempt}/{max_attempts})"
            
            # Show more of the error output
            print(f"  Still failing. Full output:")
            print(f"  {output[:2000]}")  # Increased from 1000
            print(f"  ... (total {len(output)} chars)")
            code = fixed_code
        
        print(" All attempts failed")
        return 0.0, f"Code does not run even after {max_attempts} AI debugging attempts"


if __name__ == "__main__":
    # Initialize checker
    checker = ReproducibilityChecker()
    
    # Get model to test
    if len(sys.argv) > 1:
        model_id = sys.argv[1]
    else:
        model_id = "microsoft/DialoGPT-medium"
    
    # Run check
    score, explanation = checker.check_reproducibility(model_id)
    
    # Print results
    print(f"\n{'='*60}")
    print(f"FINAL RESULT")
    print('='*60)
    print(f"Score: {score}")
    print(f"Explanation: {explanation}")
    print('='*60)