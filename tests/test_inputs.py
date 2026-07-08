"""
Two demonstration test inputs as required by the assignment.

Run:
    python -m tests.test_inputs

Test 1 — Standard request:
    A clear, well-defined business request.

Test 2 — Complex/ambiguous request:
    Missing information, conflicting requirements, multi-step — agent must
    make autonomous decisions and state its assumptions.
"""
import base64
import json
import sys
from pathlib import Path

# Add project root to path so imports resolve without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import pipeline

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

TEST_1_STANDARD = (
    "Create a project proposal for building a customer loyalty mobile app "
    "for a mid-sized retail chain. The app should include points tracking, "
    "reward redemption, and push notifications. Budget is $150,000 and the "
    "timeline is 6 months."
)

TEST_2_COMPLEX = (
    "We need some kind of document about expanding to new markets. "
    "Not sure if it should be a report or a plan. The CEO wants it ASAP "
    "but also wants it to be thorough. We're a SaaS company but I can't "
    "tell you which markets yet. Also legal said something about compliance "
    "but I don't know the details. Make it look professional."
)

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_test(label: str, request: str) -> None:
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"  {label}")
    print(separator)
    print(f"  Request: {request[:120]}{'...' if len(request) > 120 else ''}")
    print()

    result = pipeline.run(request)

    print(f"  [OK] Document Type  : {result.document_type}")
    print(f"  [OK] Document Title : {result.document_title}")
    print(f"  [OK] Objective      : {result.objective}")
    print(f"  [OK] Assumptions    : {len(result.assumptions)}")
    print(f"  [OK] Tasks executed : {len(result.tasks)}")
    print(f"  [OK] Quality Score  : {result.reflection['score']}/10")
    print(f"  [OK] Passed Review  : {result.reflection['passed']}")
    print(f"  [OK] Status         : {result.status}")
    print(f"  [OK] Document       : {result.document_filename}")
    print(f"  [OK] Doc size       : {len(base64.b64decode(result.document_base64)):,} bytes")

    if result.assumptions:
        print("\n  Assumptions made by agent:")
        for a in result.assumptions:
            print(f"    * {a}")

    if result.reflection.get("gaps"):
        print("\n  Gaps identified by reflector:")
        for g in result.reflection["gaps"]:
            print(f"    ! {g}")

    print()


if __name__ == "__main__":
    print("\n  Autonomous AI Agent - Test Suite")
    print("  Google Gemini | FastAPI | Multi-step Planning + Reflection")

    run_test("TEST 1 — Standard Business Request", TEST_1_STANDARD)
    run_test("TEST 2 — Complex / Ambiguous Request", TEST_2_COMPLEX)

    print("  All tests complete. Check ./outputs/ for generated documents.")
