"""Check all .env files in the project and which one is being used."""

from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Error: python-dotenv not installed")

print("=" * 70)
print("Checking .env Files in Project")
print("=" * 70)

# Find all .env files
project_root = Path(__file__).parent.parent
env_files = list(project_root.rglob(".env"))

print(f"\nFound {len(env_files)} .env file(s):\n")

for i, env_file in enumerate(env_files, 1):
    rel_path = env_file.relative_to(project_root)
    print(f"{i}. {rel_path}")
    print(f"   Full path: {env_file}")
    print(f"   Exists: {env_file.exists()}")
    
    if env_file.exists():
        # Check if it has OPENAI_API_KEY
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'OPENAI_API_KEY' in content:
                # Extract key (masked)
                for line in content.split('\n'):
                    if 'OPENAI_API_KEY' in line and '=' in line and not line.strip().startswith('#'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            key = parts[1].strip()
                            if key:
                                masked = key[:7] + "..." + key[-4:] if len(key) > 11 else "***"
                                print(f"   Contains API key: {masked}")
                                print(f"   Key length: {len(key)} chars")
            else:
                print(f"   No OPENAI_API_KEY found")
    print()

# Check which .env file is being used
print("=" * 70)
print("Which .env File is Being Used?")
print("=" * 70)

# SQL Generator loads from: project_root / ".env"
# project_root = Path(__file__).parent.parent
# So it's: safesql/.env

expected_env = project_root / ".env"
print(f"\nSQL Generator loads from:")
print(f"  Expected: {expected_env}")
print(f"  Exists: {expected_env.exists()}")

if expected_env.exists():
    print(f"  Status: This is the file being used")
    
    # Load it
    if DOTENV_AVAILABLE:
        load_dotenv(expected_env)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            print(f"\n  API Key loaded: {api_key[:7]}...{api_key[-4:]}")
            print(f"  Length: {len(api_key)} characters")
        else:
            print(f"\n  Warning: API Key not found in this file")
else:
    print(f"  Error: File not found - API key won't be loaded")

# Check if there are other .env files that might interfere
other_env_files = [f for f in env_files if f != expected_env]
if other_env_files:
    print(f"\nWarning: Found {len(other_env_files)} other .env file(s):")
    for env_file in other_env_files:
        rel_path = env_file.relative_to(project_root)
        print(f"  - {rel_path}")
        print(f"    (Not used by SQL Generator, but might cause confusion)")

print("\n" + "=" * 70)
print("Recommendation:")
print("=" * 70)
print(f"Use: {expected_env.relative_to(project_root)}")
print("Make sure your API key is in this file!")
print("=" * 70)
