"""Very simple API key test - just paste your key and run."""

from openai import OpenAI

# ============================================
# STEP 1: Paste your API key here (replace the text below)
# ============================================
YOUR_API_KEY = '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'

# ============================================
# STEP 2: Run this script: python scripts/test_api_key_simple.py
# ============================================

print("Testing OpenAI API Key...")
print("-" * 50)
"""
if "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" in YOUR_API_KEY:
    print("ERROR: Please paste your API key in the script!")
    print("\nEdit line 7: YOUR_API_KEY = \"your-actual-key\"")
    exit(1)
"""
try:
    client = OpenAI(api_key=YOUR_API_KEY)
    
    # Simple test
    print("Connecting to OpenAI...")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=5
    )
    
    print("SUCCESS! API key is valid.")
    print(f"Response: {response.choices[0].message.content}")
    print("\nYour API key works! You can now use it in .env file.")
    
except Exception as e:
    print(f"ERROR: {e}")
    print("\nThe API key is invalid. Please check:")
    print("1. Is the key correct?")
    print("2. Does it have credits?")
    print("3. Is it active?")
    print("\nGet a new key at: https://platform.openai.com/account/api-keys")
