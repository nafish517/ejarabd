"""
EjaraBD (ইজারাবিডি) — Master Workflow Test Runner.

Executes all automated test suites across every system workflow in order,
recording execution status, timing, and details.
"""

import os
import sys
import time
import subprocess
from datetime import datetime

# Windows কনসোলে UTF-8 এনকোডিং
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure workspace root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, ROOT_DIR)

TEST_SUITES = [
    {
        "id": "phase1_verification",
        "name": "Phase 1 Core Acceptance & Architecture Verification",
        "script": "test_phase1_verification.py",
        "category": "Phase 1 Acceptance"
    },
    {
        "id": "client_endpoints",
        "name": "Client Onboarding, 19-Field CRUD & Lifecycles",
        "script": "test_client_endpoints.py",
        "category": "Client Management"
    },
    {
        "id": "db_verify",
        "name": "Database Schema & Multi-Model Integrity",
        "script": "verify_db.py",
        "category": "Data & Models"
    },
    {
        "id": "egp_source",
        "name": "e-GP Source Discovery & Architecture Mapping",
        "script": "test_egp_source_discovery.py",
        "category": "e-GP Discovery"
    },
    {
        "id": "egp_client",
        "name": "e-GP Live Client, Scraper & Resilient Crawling",
        "script": "test_egp_client.py",
        "category": "e-GP Integration"
    },
    {
        "id": "ingestion",
        "name": "Tender Ingestion, Parsing & Deduplication",
        "script": "test_ingestion.py",
        "category": "Ingestion"
    },
    {
        "id": "matching",
        "name": "Deterministic Rule-Based Matching Engine",
        "script": "test_matching.py",
        "category": "Matching"
    },
    {
        "id": "email_service",
        "name": "Email Provider Abstraction & Templating",
        "script": "test_email_service.py",
        "category": "Communications"
    },
    {
        "id": "email_smoke",
        "name": "Real SMTP Delivery Verification",
        "script": "test_email_smoke.py",
        "category": "Communications"
    },
    {
        "id": "operations",
        "name": "Operations Platform, Deduplication & Customer Isolation",
        "script": "test_operations_platform.py",
        "category": "Operations Platform"
    },
    {
        "id": "api_endpoints",
        "name": "FastAPI Core Endpoints & Route Contracts",
        "script": "test_api.py",
        "category": "API Gateway"
    }
]

def run_suite(suite: dict, python_exe: str) -> dict:
    script_path = os.path.join(BASE_DIR, suite["script"])
    print(f"\n{'='*75}")
    print(f"▶ RUNNING: [{suite['category']}] {suite['name']}")
    print(f"  Script: {suite['script']}")
    print(f"{'='*75}")

    start_time = time.time()
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT_DIR
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [python_exe, script_path],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    elapsed = time.time() - start_time

    success = result.returncode == 0
    status_str = "PASSED ✓" if success else "FAILED ✗"
    print(f"\nResult: {status_str} in {elapsed:.2f}s")
    if not success:
        print("\n--- STDOUT ---")
        print(result.stdout[-1500:] if len(result.stdout) > 1500 else result.stdout)
        print("\n--- STDERR ---")
        print(result.stderr[-1500:] if len(result.stderr) > 1500 else result.stderr)

    return {
        "suite": suite,
        "success": success,
        "elapsed": elapsed,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

def main():
    python_exe = sys.executable
    print("\n" + "#"*75)
    print("  EJARABD (ইজারাবিডি) — COMPREHENSIVE WORKFLOW TEST SUITE")
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p BST')}")
    print(f"  Python executable: {python_exe}")
    print(f"  Total test suites to execute: {len(TEST_SUITES)}")
    print("#"*75)

    results = []
    overall_start = time.time()

    for suite in TEST_SUITES:
        res = run_suite(suite, python_exe)
        results.append(res)

    overall_elapsed = time.time() - overall_start
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    print("\n" + "="*75)
    print("                     WORKFLOW TEST REPORT SUMMARY")
    print("="*75)
    print(f"{'Category':<20} | {'Workflow Test':<38} | {'Status':<8} | {'Duration'}")
    print("-" * 75)

    for r in results:
        s = r["suite"]
        stat = "PASS ✓" if r["success"] else "FAIL ✗"
        print(f"{s['category']:<20} | {s['name'][:38]:<38} | {stat:<8} | {r['elapsed']:.2f}s")

    print("-" * 75)
    print(f"Total Suites: {total} | Passed: {passed} | Failed: {failed} | Total Time: {overall_elapsed:.2f}s")
    print("="*75)

    if failed == 0:
        print("\n🎉 ALL EJARABD WORKFLOWS TESTED AND PASSED WITH 100% SUCCESS!\n")
        sys.exit(0)
    else:
        print(f"\n⚠️  {failed} TEST SUITE(S) FAILED. Please review the logs above.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
