"""
Quick test script to verify OpenAI API key is working.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[OK] Loaded .env file from: {env_path}")
    else:
        print(f"[WARN] .env file not found at: {env_path}")
except ImportError:
    print("[WARN] python-dotenv not installed. Install with: pip install python-dotenv")

# Check API key
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    # Show first and last few characters
    masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 11 else "***"
    print(f"[OK] OPENAI_API_KEY found: {masked_key}")
    print(f"     Length: {len(api_key)} characters")
    
    # Test API connection
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Simple test call
        print("\n[TEST] Testing API connection...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use cheaper model for test
            messages=[{"role": "user", "content": "Say 'API key is working'"}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        print(f"[SUCCESS] API key is working! Response: {result}")
        print("\n[OK] Ready to run SQL generation tests!")
        
    except Exception as e:
        print(f"[ERROR] API test failed: {e}")
        print("\n[INFO] Check your API key at: https://platform.openai.com/account/api-keys")
else:
    print("[ERROR] OPENAI_API_KEY not found in environment")
    print("\n[INFO] To set up:")
    print("1. Create .env file in SafeSQL_Research folder")
    print("2. Add: OPENAI_API_KEY=your_key_here")
    print("3. Or set environment variable: $env:OPENAI_API_KEY='your_key_here'")
