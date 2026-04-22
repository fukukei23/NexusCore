#!/usr/bin/env python3
"""
Tier 2 Mutation Testing - Manual Execution Script

This script uses the MutationTesterAgent directly to run mutation testing
on mutation_tester_agent.py, bypassing mutmut CLI issues.
"""
import sys
import os

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from nexuscore.agents.mutation_tester_agent import MutationTesterAgent

def main():
    """Run Tier 2 mutation testing manually"""
    print("=" * 80)
    print("Tier 2 Mutation Testing - Manual Execution")
    print("=" * 80)
    print()

    # MutationTesterAgent のインスタンスを作成
    agent = MutationTesterAgent()

    # テスト対象のソースファイルとテストファイル
    source_path = "src/nexuscore/agents/mutation_tester_agent.py"
    test_path = "tests/agents/test_mutation_tester_agent.py"

    print(f"Source: {source_path}")
    print(f"Test:   {test_path}")
    print()
    print("Running mutation testing...")
    print("-" * 80)

    # Mutation テストを実行
    # 簡易的な constitution（実際の値は不要）
    constitution = {"quality_gates": {"mutation_testing": {"enabled": True}}}

    result = agent.run_mutation_testing(
        source_path=source_path,
        test_path=test_path,
        constitution=constitution
    )

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    print(f"Status: {'PASSED' if result.passed else 'FAILED'}")
    print(f"Total Mutants: {result.total_mutants}")
    print(f"Killed: {result.killed}")
    print(f"Survived: {result.survived}")
    print(f"Timeout: {result.timeout}")
    print(f"Suspicious: {result.suspicious}")

    if result.total_mutants > 0:
        mutation_score = (result.killed / result.total_mutants) * 100
        print(f"Mutation Score: {mutation_score:.1f}%")
    else:
        print("Mutation Score: N/A (no mutants generated)")

    print()
    print("-" * 80)
    print("Feedback:")
    print("-" * 80)
    print(result.feedback)
    print()

    # 生き残った mutant がある場合
    if result.survived > 0 and result.survived_mutants:
        print("=" * 80)
        print(f"SURVIVED MUTANTS ({len(result.survived_mutants)})")
        print("=" * 80)
        for i, mutant in enumerate(result.survived_mutants, 1):
            print(f"\nMutant #{i}:")
            print(f"  File: {mutant.file_path}")
            print(f"  Line: {mutant.line_number}")
            print(f"  Mutator: {mutant.mutator}")
            if mutant.suggestion:
                print(f"  Suggestion: {mutant.suggestion}")

    print()
    print("=" * 80)
    print("Tier 2 mutation testing completed")
    print("=" * 80)

    return 0 if result.passed else 1

if __name__ == "__main__":
    sys.exit(main())
