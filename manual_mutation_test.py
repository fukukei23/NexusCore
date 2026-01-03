#!/usr/bin/env python
"""
Manual mutation testing script to bypass mutmut's stats collection issue
"""
import subprocess
import shutil
import json
from pathlib import Path

def test_mutant(mutant_src, test_cmd):
    """Test a single mutant by copying it and running tests"""
    # Backup original
    original = Path("src/nexuscore/agents/mutation_tester_agent.py")
    backup = Path("src/nexuscore/agents/mutation_tester_agent.py.backup")
    shutil.copy(original, backup)

    try:
        # Copy mutant
        shutil.copy(mutant_src, original)

        # Run tests
        result = subprocess.run(
            test_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Restore original
        shutil.copy(backup, original)
        backup.unlink()

        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "killed": result.returncode != 0
        }
    except Exception as e:
        # Restore on error
        if backup.exists():
            shutil.copy(backup, original)
            backup.unlink()
        return {
            "exit_code": -1,
            "error": str(e),
            "killed": False
        }

# Test command
test_cmd = "python -m pytest tests/agents/test_mutation_tester_agent.py --tb=no -q -p no:warnings"

# Get mutants from mutants directory
mutants_src_dir = Path("mutants/src/nexuscore/agents")

if mutants_src_dir.exists():
    results = []

    # Test first 20 mutants
    for i in range(1, 21):
        mutant_file = mutants_src_dir / f"mutation_tester_agent_mutmut_{i}.py"
        if mutant_file.exists():
            print(f"Testing mutant {i}...")
            result = test_mutant(mutant_file, test_cmd)
            results.append({
                "mutant": i,
                "killed": result["killed"],
                "exit_code": result["exit_code"]
            })
            status = "KILLED" if result["killed"] else "SURVIVED"
            print(f"  Mutant {i}: {status} (exit code: {result['exit_code']})")

    # Summary
    killed = sum(1 for r in results if r["killed"])
    total = len(results)
    score = (killed / total * 100) if total > 0 else 0

    print(f"\n{'='*60}")
    print(f"Mutation Testing Results (Sample of {total} mutants)")
    print(f"{'='*60}")
    print(f"Killed: {killed}/{total}")
    print(f"Survived: {total - killed}/{total}")
    print(f"Mutation Score: {score:.1f}%")
    print(f"{'='*60}")

    # Save results
    with open("manual_mutation_results.json", "w") as f:
        json.dump(results, f, indent=2)
else:
    print("ERROR: mutants directory not found. Run 'mutmut run' first to generate mutants.")
