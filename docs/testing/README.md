# Testing Documentation

NexusCore プロジェクトのテスト戦略とベストプラクティス

---

## 📚 ドキュメント一覧

### [Test Quality Guidelines](./test-quality-guidelines.md)
**対象**: 全開発者
**内容**: 効果的なテスト設計と「テストの為のテスト」の回避

- 良いテスト vs 悪いテストの違い
- モックの使い分け
- mutation_tester_agent リファクタリングの教訓
- ベストプラクティス
- チェックリスト

### [Mutation Testing Guide](./mutation-testing-guide.md)
**対象**: エージェント開発者
**内容**: mutmut を使った mutation testing の実践ガイド

- mutation testing の基礎
- mutmut v3.x の使い方
- 設定方法 (pyproject.toml, pytest.ini)
- survived mutant への対応
- トラブルシューティング

---

## 🎯 クイックスタート

### 1. 新しいエージェントのテストを書く

```python
# ✅ 良い例
def test_parse_logic(agent):
    """実際のロジックをテスト（モックなし）"""
    result = agent.parse("input data")
    assert result == expected

# ✅ 外部依存のみモック
def test_with_llm(agent):
    with patch.object(agent, "execute_llm_task", return_value="response"):
        result = agent.process()
        assert result == expected

# ✅ 実際のファイルI/O
def test_save_file(tmp_path):
    file_path = tmp_path / "test.json"
    save_data(file_path, {"key": "value"})
    assert file_path.exists()
```

[詳細はこちら →](./test-quality-guidelines.md)

### 2. Mutation Testing を実行

```bash
# pyproject.toml を設定
[tool.mutmut]
paths_to_mutate = ["src/nexuscore/agents/my_agent.py"]
tests_dir = ["tests/agents/test_my_agent.py", "-m", "not slow"]

# 実行
mutmut run --max-children 1

# 結果確認
mutmut results
```

[詳細はこちら →](./mutation-testing-guide.md)

---

## 📊 プロジェクト全体のテスト状況

### テストスイート

```
tests/agents/
├── 46 テストファイル
├── 215+ テスト
└── 98.1% 成功率 (211 passed, 4 failed)
```

### Mutation Testing

- **mutation_tester_agent.py**: v2.x/v3.x 両対応、30テスト (100% meaningful)
- **simple_math.py**: 100% mutation score (3/3 killed)
- **他のエージェント**: 適切なモック使用、問題なし

---

## ✅ テスト品質チェックリスト

新しいテストを書く前に：

- [ ] モックは外部依存のみ（LLM, DB, 時刻など）
- [ ] 自分のコードのロジックは実際にテスト
- [ ] tmp_path を使って実際のファイルI/Oをテスト
- [ ] 実装詳細（呼び出し回数など）ではなく、振る舞いをテスト
- [ ] parametrize で複数ケースを効率的に
- [ ] 時間のかかるテストには @pytest.mark.slow
- [ ] mutation testing で有効なテスト

---

## 🚀 推奨フロー

1. **テストを書く** (Test Quality Guidelines を参照)
2. **pytest で確認** (`pytest tests/agents/test_my_agent.py`)
3. **mutation testing** (`mutmut run --max-children 1`)
4. **80%以上を目指す** (survived mutant を修正)
5. **コミット**

---

## 🎓 学習リソース

### 内部ドキュメント
- [Test Quality Guidelines](./test-quality-guidelines.md) - 必読
- [Mutation Testing Guide](./mutation-testing-guide.md) - 実践ガイド

### 外部リソース
- [pytest documentation](https://docs.pytest.org/)
- [mutmut documentation](https://mutmut.readthedocs.io/)
- [Mutation Testing: A Complete Guide](https://www.guru99.com/mutation-testing.html)

---

## 📝 ケーススタディ

### mutation_tester_agent リファクタリング

**問題**: 10個のテストが「テストの為のテスト」状態

**解決策**:
1. モック重視のテスト10個を削除（298行削減）
2. 実際のロジックをテストする30個を維持
3. mutation testing から除外するテストを90%削減

**結果**:
- コード: 1059行 → 719行 (-32%)
- 実行時間: 0.47s → 0.40s (-15%)
- 意味のあるテスト: 75% → 100% (+33%)

[詳細はこちら →](./test-quality-guidelines.md#-mutation_tester_agent-リファクタリング結果)

---

## 🤝 コントリビューション

テスト品質の改善アイデアや、ドキュメントの改善提案は歓迎します：

1. Issue を作成
2. プルリクエストを提出
3. レビュー後マージ

---

## 📞 サポート

質問や問題がある場合：

1. [Test Quality Guidelines](./test-quality-guidelines.md) を確認
2. [Mutation Testing Guide](./mutation-testing-guide.md) のトラブルシューティングを確認
3. チームに相談

---

**最終更新**: 2025-12-30
**メンテナー**: NexusCore Team
