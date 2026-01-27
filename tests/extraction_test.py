import re
import json
import os

def extract_json(text: str) -> dict:
    """
    Robust extraction logic to find the LAST valid JSON block in the text.
    Now includes a pre-processing step to handle double-encoded JSON strings.
    """
    print(f"--- Debugging Extraction ---")
    print(f"Raw Input text length: {len(text)}")
    
    # 0. PRE-PROCESSING: Handle Double-Encoded JSON Strings
    # The input text might be a JSON string literal (e.g., '"```json\\n{\\n...').
    # We attempt to unwrap it first to get the actual Markdown content.
    try:
        stripped = text.strip()
        # Check if it looks like a string literal (starts and ends with quotes)
        if stripped.startswith('"') and stripped.endswith('"'):
            unwrapped = json.loads(text)
            if isinstance(unwrapped, str):
                text = unwrapped
                print("  -> DETECTED JSON-encoded string input. Unwrapped successfully.")
                print(f"  -> Unwrapped text length: {len(text)}")
    except (json.JSONDecodeError, TypeError):
        # Not a valid JSON string or simple text, proceed with original text
        print("  -> Input is not a JSON-encoded string. Proceeding with raw text.")
        pass

    # 1. Regex Match for Markdown Code Blocks
    matches = re.findall(r"```\w*(.*?)```", text, re.DOTALL)
    print(f"Found {len(matches)} markdown code blocks.")
    
    # Iterate REVERSE to find the last valid JSON block
    for i, match in enumerate(reversed(matches)):
        print(f"\nChecking Block #{len(matches) - i} (Reverse index {i})...")
        
        # Clean up potential comments in JSON (e.g. // comments)
        # Note: We anchor to start of line to avoid stripping http:// URLs inside strings
        clean_text = re.sub(r"^\s*//.*$", "", match, flags=re.MULTILINE)
        
        try:
            data = json.loads(clean_text.strip())
            print("  -> VALID JSON parsed successfully.")
            
            # HEURISTIC: Check for placeholder templates
            if "corrected_python_code" in data:
                code_val = data["corrected_python_code"]
                if "The complete, runnable Python code" in code_val and len(code_val) < 200:
                    print("  -> DETECTED TEMPLATE/PLACEHOLDER text. Skipping...")
                    continue
            
            # If we pass the heuristic, this is the one!
            print("  -> ACCEPTED as valid content.")
            return data
            
        except json.JSONDecodeError as e:
            print(f"  -> INVALID JSON in block: {e}")
            continue
    
    print("\nNo valid JSON found in markdown blocks. Trying fallback...")
    
    # 2. Fallback: Find outermost braces if no markdown blocks
    # This handles cases where the LLM forgets the ```json wrapper
    s = text.find('{')
    e = text.rfind('}') + 1
    if s != -1 and e != -1:
        print(f"Found potential JSON braces at {s}:{e}")
        candidate = text[s:e]
        clean_text = re.sub(r"^\s*//.*$", "", candidate, flags=re.MULTILINE)
        try: 
            return json.loads(clean_text.strip())
        except Exception as e:
            print(f"Fallback parse failed: {e}")
            
    return None

def main():
    filename = 'cgen.txt'
    
    # Load the problematic response text
    try:
        if not os.path.exists(filename):
            print(f"Error: '{filename}' not found. Please ensure the file exists.")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            response_text = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Run Extraction
    result = extract_json(response_text)
    
    print("\n" + "="*40)
    print("FINAL EXTRACTION RESULT:")
    print("="*40)
    
    if result:
        print("[SUCCESS] JSON parsed successfully.")
        print(f"Keys found: {list(result.keys())}")
        
        # Check for the specific biology keys in your file
        if "model_name" in result:
            print(f"\nModel Name: {result['model_name']}")
            print(f"Explanation Preview: {result.get('explanation', '')[:100]}...")
            
        # Check for Python code (legacy check)
        elif "corrected_python_code" in result:
            code = result["corrected_python_code"]
            print(f"Python Code Length: {len(code)} chars")
        else:
            print("Unknown JSON structure extracted.")
    else:
        print("[FAIL] Could not extract any JSON.")

if __name__ == "__main__":
    main()