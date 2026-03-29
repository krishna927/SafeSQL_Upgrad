"""Verification script to test SafeSQL installation and setup."""

import sys
import os
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_imports():
    """Check if all core modules can be imported."""
    print("Checking imports...")
    try:
        from src.utils import ConfigLoader, get_logger, DatabaseManager, SQLParser
        from src.models import BaseModel
        print("Status: All core modules imported successfully")
        return True
    except ImportError as e:
        print(f"Error: Import error: {e}")
        return False

def check_config():
    """Check if configuration files exist and can be loaded."""
    print("\nChecking configuration...")
    try:
        from src.utils import ConfigLoader
        config = ConfigLoader()
        print("Status: Configuration loaded successfully")
        
        # Check some key settings
        gpt4_temp = config.get("models.gpt4.temperature")
        print(f"   Model temperature: {gpt4_temp}")
        
        safety_policies = config.get_safety_policies()
        print(f"   Safety policies loaded: {len(safety_policies) > 0}")
        return True
    except Exception as e:
        print(f"Error: Configuration error: {e}")
        return False

def check_sql_parser():
    """Test SQL parser functionality."""
    print("\nTesting SQL parser...")
    try:
        from src.utils import SQLParser
        parser = SQLParser()
        
        # Test cases
        test_sql = "SELECT * FROM users WHERE id = 1"
        operation = parser.get_operation_type(test_sql)
        assert operation == "SELECT", f"Expected SELECT, got {operation}"
        
        has_where = parser.is_destructive_operation(test_sql)
        assert not has_where, "SELECT query should not be destructive"
        
        print("Status: SQL parser working correctly")
        return True
    except Exception as e:
        print(f"Error: SQL parser error: {e}")
        return False

def check_logger():
    """Test logger setup."""
    print("\nTesting logger...")
    try:
        from src.utils import setup_logger, get_logger
        logger = setup_logger("test_logger", level="INFO", console=True)
        logger.info("Test log message")
        print("Status: Logger working correctly")
        return True
    except Exception as e:
        print(f"Error: Logger error: {e}")
        return False

def check_project_structure():
    """Verify project structure exists."""
    print("\nChecking project structure...")
    required_dirs = [
        "config",
        "src/guardrails",
        "src/verification",
        "src/models",
        "src/preprocessing",
        "src/evaluation",
        "src/utils",
        "tests/unit",
        "data/datasets",
    ]
    
    project_root = Path(__file__).parent.parent
    all_exist = True
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"   Status: {dir_path} exists")
        else:
            print(f"   Missing: {dir_path}")
            all_exist = False
    
    return all_exist

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("SafeSQL Installation Verification")
    print("=" * 60)
    
    checks = [
        ("Project Structure", check_project_structure),
        ("Imports", check_imports),
        ("Configuration", check_config),
        ("SQL Parser", check_sql_parser),
        ("Logger", check_logger),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"Error: {name} failed with exception: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\nStatus: All checks passed - SafeSQL is ready to use")
        return 0
    else:
        print("\nWarning: Some checks failed - Please review the errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
