#!/bin/bash
# mutmut 用の pytest runner スクリプト
# mutants ディレクトリ内で実行され、mutants ディレクトリ内のテストを実行します

# 現在のディレクトリ（mutants ディレクトリ）を取得
MUTANTS_DIR=$(pwd)

# PYTHONPATH を設定（mutants ディレクトリ内のソースコードを使用）
export PYTHONPATH="${MUTANTS_DIR}:${MUTANTS_DIR}/src"

# pytest を実行（mutants ディレクトリ内のテストを実行）
python -m pytest tests/agents/test_mutation_tester_agent.py --tb=no -q -p no:warnings

# 終了コードを返す
exit $?
