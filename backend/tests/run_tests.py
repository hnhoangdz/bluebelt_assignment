#!/usr/bin/env python3
"""
Comprehensive test runner for Dextrends backend
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    end_time = time.time()
    
    print(f"Duration: {end_time - start_time:.2f} seconds")
    
    if result.returncode == 0:
        print("✅ SUCCESS")
        if result.stdout:
            print("Output:", result.stdout[-500:])  # Last 500 chars
    else:
        print("❌ FAILED")
        if result.stderr:
            print("Error:", result.stderr[-500:])  # Last 500 chars
        if result.stdout:
            print("Output:", result.stdout[-500:])  # Last 500 chars
    
    return result.returncode == 0

def run_unit_tests():
    """Run unit tests"""
    command = "python -m pytest backend/tests/backend/test_unit_services.py -v --tb=short -m unit"
    return run_command(command, "Unit Tests")

def run_integration_tests():
    """Run integration tests"""
    command = "python -m pytest backend/tests/backend/test_integration_api.py -v --tb=short -m integration"
    return run_command(command, "Integration Tests")

def run_database_tests():
    """Run database tests"""
    command = "python -m pytest backend/tests/backend/test_database.py -v --tb=short -m database"
    return run_command(command, "Database Tests")

def run_performance_tests():
    """Run performance tests"""
    command = "python -m pytest backend/tests/backend/test_performance.py -v --tb=short -m performance"
    return run_command(command, "Performance Tests")

def run_load_tests():
    """Run load tests with Locust"""
    print(f"\n{'='*60}")
    print("Load Tests with Locust")
    print("Run manually with:")
    print("locust -f backend/tests/backend/test_load_locust.py --host=http://localhost:8000")
    print("Then open http://localhost:8089 to configure and start the test")
    print(f"{'='*60}")
    return True

def run_coverage_tests():
    """Run tests with coverage"""
    command = "python -m pytest backend/tests/backend/ --cov=backend --cov-report=term-missing --cov-report=html:htmlcov --cov-report=xml:coverage.xml --cov-fail-under=70"
    return run_command(command, "Coverage Tests")

def run_all_tests():
    """Run all tests"""
    command = "python -m pytest backend/tests/backend/ -v --tb=short"
    return run_command(command, "All Tests")

def run_specific_test(test_path):
    """Run specific test"""
    command = f"python -m pytest {test_path} -v --tb=short"
    return run_command(command, f"Specific Test: {test_path}")

def check_environment():
    """Check if test environment is properly set up"""
    print("🔍 Checking test environment...")
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check required packages
    required_packages = [
        'pytest', 'pytest-asyncio', 'pytest-cov', 'locust', 'httpx', 'aiohttp'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install with: uv pip install " + " ".join(missing_packages))
        return False
    
    print("✅ Environment check passed")
    return True

def generate_test_report():
    """Generate comprehensive test report"""
    print(f"\n{'='*60}")
    print("GENERATING TEST REPORT")
    print(f"{'='*60}")
    
    # Create test report directory
    report_dir = project_root / "test_reports"
    report_dir.mkdir(exist_ok=True)
    
    # Generate HTML coverage report
    coverage_command = "python -m pytest backend/tests/backend/ --cov=backend --cov-report=html:test_reports/coverage_html --cov-report=xml:test_reports/coverage.xml --cov-report=json:test_reports/coverage.json"
    run_command(coverage_command, "Generate Coverage Report")
    
    # Generate JUnit XML report
    junit_command = "python -m pytest backend/tests/backend/ --junitxml=test_reports/junit.xml"
    run_command(junit_command, "Generate JUnit Report")
    
    print(f"\n📊 Test reports generated in: {report_dir}")
    print("- HTML Coverage: test_reports/coverage_html/index.html")
    print("- XML Coverage: test_reports/coverage.xml")
    print("- JSON Coverage: test_reports/coverage.json")
    print("- JUnit XML: test_reports/junit.xml")

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Dextrends Backend Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--database", action="store_true", help="Run database tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--load", action="store_true", help="Show load test instructions")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--report", action="store_true", help="Generate test reports")
    parser.add_argument("--check", action="store_true", help="Check test environment")
    parser.add_argument("--test", type=str, help="Run specific test file")
    
    args = parser.parse_args()
    
    # Set working directory to project root
    os.chdir(project_root)
    
    # Set environment variables for testing
    os.environ.update({
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite:///test.db",
        "REDIS_URL": "redis://localhost:6379/1",
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "OPENAI_API_KEY": "test-key",
        "MEM0_API_KEY": "test-mem0-key",
        "QDRANT_URL": "http://localhost:6333"
    })
    
    success = True
    
    if args.check or not any(vars(args).values()):
        success &= check_environment()
    
    if args.unit:
        success &= run_unit_tests()
    
    if args.integration:
        success &= run_integration_tests()
    
    if args.database:
        success &= run_database_tests()
    
    if args.performance:
        success &= run_performance_tests()
    
    if args.load:
        success &= run_load_tests()
    
    if args.coverage:
        success &= run_coverage_tests()
    
    if args.all:
        success &= run_all_tests()
    
    if args.test:
        success &= run_specific_test(args.test)
    
    if args.report:
        generate_test_report()
    
    # If no specific arguments, show help
    if not any(vars(args).values()):
        parser.print_help()
        print("\n🚀 Quick start:")
        print("python backend/tests/run_tests.py --check    # Check environment")
        print("python backend/tests/run_tests.py --unit     # Run unit tests")
        print("python backend/tests/run_tests.py --all      # Run all tests")
        print("python backend/tests/run_tests.py --coverage # Run with coverage")
        print("python backend/tests/run_tests.py --report   # Generate reports")
    
    # Final status
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
    else:
        print("💥 SOME TESTS FAILED!")
        sys.exit(1)
    print(f"{'='*60}")

if __name__ == "__main__":
    main()