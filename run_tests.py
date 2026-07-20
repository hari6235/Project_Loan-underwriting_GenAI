#!/usr/bin/env python3
"""
Test Execution Script - Runs all tests and generates a comprehensive report.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --coverage         # Include coverage report
    python run_tests.py --functional       # Only functional tests
    python run_tests.py --api              # Only API tests (requires backend)

Output: test_results/ directory with reports
"""
import subprocess
import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime


def create_output_dir():
    """Create test_results directory if it doesn't exist."""
    results_dir = Path("test_results")
    results_dir.mkdir(exist_ok=True)
    return results_dir


def run_command(cmd, description):
    """Run a shell command and return result."""
    print(f"\n{'='*70}")
    print(f"▶ {description}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            timeout=600
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Test execution timed out (10 minutes)")
        return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False


def run_tests(suite, coverage=False):
    """Run pytest with specified suite."""
    cmd = ["pytest", suite, "-v", "--tb=short"]
    
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])
    
    return run_command(cmd, f"Running {suite}")


def run_all_tests():
    """Run complete test suite."""
    results_dir = create_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    report = {
        "timestamp": timestamp,
        "results": {},
        "summary": {}
    }
    
    print("\n" + "="*70)
    print("🧪 LOAN UNDERWRITING ASSISTANT - TEST SUITE EXECUTION")
    print("="*70)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests_to_run = [
        ("tests/test_functional_suite.py", "Functional Test Suite (48 tests)"),
        ("tests/test_chains.py", "Chain Orchestration Tests"),
        ("tests/test_hitl_workflow.py", "HITL Workflow Tests"),
        ("tests/test_prompt_versioning.py", "Prompt Versioning Tests"),
        ("tests/test_mcp_integration.py", "MCP Integration Tests"),
        ("tests/test_role_based_rag.py", "Role-Based RAG Tests"),
        ("tests/test_langsmith_config.py", "LangSmith Config Tests"),
    ]
    
    passed_count = 0
    failed_count = 0
    
    for test_file, description in tests_to_run:
        if not Path(test_file).exists():
            print(f"⚠️  {test_file} not found, skipping...")
            report["results"][test_file] = "SKIPPED"
            continue
        
        success = run_command(
            ["pytest", test_file, "-v", "--tb=short"],
            description
        )
        
        report["results"][test_file] = "PASSED" if success else "FAILED"
        if success:
            passed_count += 1
        else:
            failed_count += 1
    
    # Generate coverage report
    print(f"\n{'='*70}")
    print("▶ Generating Coverage Report")
    print(f"{'='*70}\n")
    
    run_command(
        ["pytest", "tests/", "--cov=.", "--cov-report=html", "--cov-report=term-missing"],
        "Coverage Analysis"
    )
    
    # Summary
    report["summary"] = {
        "total_test_files": len(tests_to_run),
        "passed": passed_count,
        "failed": failed_count,
        "coverage_report": "htmlcov/index.html"
    }
    
    print(f"\n{'='*70}")
    print("📊 TEST EXECUTION SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Passed: {passed_count}/{len(tests_to_run)}")
    print(f"❌ Failed: {failed_count}/{len(tests_to_run)}")
    print(f"📈 Coverage Report: htmlcov/index.html")
    print(f"{'='*70}")
    
    # Save report
    report_path = results_dir / f"test_report_{timestamp}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"✔ Report saved to: {report_path}")
    
    return failed_count == 0


def run_api_tests():
    """Run API integration tests (requires backend running)."""
    print("\n" + "="*70)
    print("🔌 API INTEGRATION TESTS")
    print("="*70)
    print("⚠️  This requires the backend to be running on http://127.0.0.1:8000")
    print("\nStart backend with:")
    print("  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000\n")
    
    input("Press Enter when backend is ready...")
    
    results_dir = create_output_dir()
    success = run_command(
        ["pytest", "tests/test_api_integration.py", "-v", "--tb=short"],
        "API Integration Test Suite (25+ tests)"
    )
    
    print(f"\n{'='*70}")
    print("API TESTS RESULT: " + ("✅ PASSED" if success else "❌ FAILED"))
    print(f"{'='*70}")
    
    return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run test suite for Loan Underwriting Assistant"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Include coverage report"
    )
    parser.add_argument(
        "--functional",
        action="store_true",
        help="Run only functional tests"
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Run only API integration tests (requires backend)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick smoke tests"
    )
    
    args = parser.parse_args()
    
    try:
        if args.api:
            success = run_api_tests()
        elif args.functional:
            results_dir = create_output_dir()
            success = run_command(
                ["pytest", "tests/test_functional_suite.py", "-v", "--tb=short"],
                "Functional Test Suite"
            )
        elif args.quick:
            print("\n" + "="*70)
            print("⚡ QUICK SMOKE TESTS")
            print("="*70 + "\n")
            results_dir = create_output_dir()
            success = run_command(
                ["pytest", "tests/test_functional_suite.py::TestChatEndpoint", "-v"],
                "Smoke Test: Chat Endpoint"
            )
        else:
            # Default: run all tests
            success = run_all_tests()
        
        print("\n" + "="*70)
        if success:
            print("✅ ALL TESTS PASSED!")
            print("📁 Results saved to: test_results/")
            print("📊 Coverage report: htmlcov/index.html")
        else:
            print("❌ SOME TESTS FAILED")
            print("📁 Check test_results/ for details")
        print("="*70 + "\n")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
