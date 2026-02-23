import asyncio
from unittest.mock import Mock, patch

from nexuscore.workflows import multi_llm_review as workflow


# ============================================================================
# データクラステスト
# ============================================================================
class TestDataClasses:
    def test_review_item_creation(self):
        """ReviewItemの作成と属性"""
        item = workflow.ReviewItem(path="test.py", content="def test(): pass", error="SyntaxError")
        assert item.path == "test.py"
        assert item.content == "def test(): pass"
        assert item.error == "SyntaxError"

    def test_review_item_default_error(self):
        """ReviewItemのデフォルトerror値"""
        item = workflow.ReviewItem(path="file.py", content="code")
        assert item.error == ""

    def test_model_review_creation(self):
        """ModelReviewの作成"""
        review = workflow.ModelReview(
            model="gpt-4",
            summary={"issues": [{"title": "bug"}], "confidence": 0.8},
            raw='{"issues":[]}',
            ok=True,
            error="",
        )
        assert review.model == "gpt-4"
        assert review.summary["confidence"] == 0.8
        assert review.ok is True

    def test_model_review_default_values(self):
        """ModelReviewのデフォルト値"""
        review = workflow.ModelReview(model="test-model", summary={})
        assert review.raw == ""
        assert review.ok is True
        assert review.error == ""

    def test_consensus_result_creation(self):
        """ConsensusResultの作成"""
        result = workflow.ConsensusResult(
            issues=["issue1", "issue2"],
            file_fixes={"file.py": "fix"},
            confidence=0.95,
            contributing_models=["model1", "model2"],
        )
        assert len(result.issues) == 2
        assert result.confidence == 0.95
        assert "model1" in result.contributing_models

    def test_consensus_result_default_factory(self):
        """ConsensusResultのdefault_factory"""
        result = workflow.ConsensusResult()
        assert result.issues == []
        assert result.file_fixes == {}
        assert result.confidence == 0.0
        assert result.contributing_models == []


# ============================================================================
# プロンプトテスト
# ============================================================================
class TestPrompts:
    def test_make_summary_prompt_includes_task(self):
        """make_summary_promptがタスクを含む"""
        prompt = workflow.make_summary_prompt("レビュー", "コード内容")
        assert "レビュー" in prompt
        assert "コード内容" in prompt

    def test_make_summary_prompt_includes_constraints(self):
        """プロンプトに出力制約が含まれる"""
        prompt = workflow.make_summary_prompt("task", "batch")
        assert "300文字以内" in prompt or "JSON" in prompt

    def test_review_agent_has_system_prompt(self):
        """ReviewAgentがSYSTEM_PROMPTを持つ"""
        agent = workflow.ReviewAgent()
        assert hasattr(agent, "SYSTEM_PROMPT")
        assert "JSON" in agent.SYSTEM_PROMPT


# ============================================================================
# 既存テスト
# ============================================================================
def test_merge_consensus_aggregates_issues():
    reviews = [
        workflow.ModelReview(
            model="m1", summary={"issues": [{"title": "A"}], "confidence": 0.6}, raw=""
        ),
        workflow.ModelReview(
            model="m2",
            summary={"issues": [{"title": "B"}, {"title": "A"}], "confidence": 0.8},
            raw="",
        ),
    ]
    consensus = workflow._merge_consensus(reviews)
    assert consensus.issues == ["A", "B"]
    assert consensus.contributing_models[1].startswith("m2")


def test_parse_models_splits_list():
    assert workflow._parse_models("a,b , c") == ["a", "b", "c"]


def test_run_consensus_review_uses_threshold(monkeypatch):
    async def fake_run_one(model_name, prompt, max_tokens):
        confidence = 0.95 if model_name == "strong" else 0.1
        return workflow.ModelReview(
            model=model_name,
            summary={"issues": [{"title": f"Issue-{model_name}"}], "confidence": confidence},
            raw="",
        )

    monkeypatch.setattr(workflow, "_run_one_model", fake_run_one)

    items = [workflow.ReviewItem(path="file.py", content="print('hi')")]
    result = asyncio.run(
        workflow.run_consensus_review(
            task="test",
            items=items,
            models=["strong"],
            confidence_threshold=0.9,
            max_extra_validations=1,
            max_output_tokens=100,
        )
    )
    assert result.confidence >= 0.9
    assert "Issue-strong" in result.issues[0]


# ============================================================================
# _merge_consensus 拡張テスト
# ============================================================================
class TestMergeConsensus:
    def test_merge_consensus_empty_reviews(self):
        """空のレビューリスト"""
        consensus = workflow._merge_consensus([])
        assert consensus.issues == []
        assert consensus.confidence == 0.0
        assert consensus.contributing_models == []

    def test_merge_consensus_deduplicates_issues(self):
        """重複するissueを除去"""
        reviews = [
            workflow.ModelReview(
                model="m1",
                summary={"issues": [{"title": "A"}, {"title": "B"}], "confidence": 0.5},
                raw="",
            ),
            workflow.ModelReview(
                model="m2",
                summary={"issues": [{"title": "A"}, {"title": "C"}], "confidence": 0.7},
                raw="",
            ),
        ]
        consensus = workflow._merge_consensus(reviews)
        assert len(consensus.issues) == 3  # A, B, C
        assert "A" in consensus.issues
        assert "B" in consensus.issues
        assert "C" in consensus.issues

    def test_merge_consensus_limits_to_five_issues(self):
        """issueを最大5つに制限"""
        issues_list = [{"title": f"Issue{i}"} for i in range(10)]
        reviews = [
            workflow.ModelReview(
                model="m1", summary={"issues": issues_list, "confidence": 0.8}, raw=""
            )
        ]
        consensus = workflow._merge_consensus(reviews)
        assert len(consensus.issues) <= 5

    def test_merge_consensus_averages_confidence(self):
        """自信度の平均を計算"""
        reviews = [
            workflow.ModelReview(model="m1", summary={"issues": [], "confidence": 0.6}, raw=""),
            workflow.ModelReview(model="m2", summary={"issues": [], "confidence": 0.8}, raw=""),
            workflow.ModelReview(model="m3", summary={"issues": [], "confidence": 1.0}, raw=""),
        ]
        consensus = workflow._merge_consensus(reviews)
        # (0.6 + 0.8 + 1.0) / 3 = 0.8
        assert abs(consensus.confidence - 0.8) < 0.01

    def test_merge_consensus_marks_failed_models(self):
        """失敗したモデルに (fail) マーク"""
        reviews = [
            workflow.ModelReview(model="ok", summary={}, raw="", ok=True),
            workflow.ModelReview(model="bad", summary={}, raw="", ok=False),
        ]
        consensus = workflow._merge_consensus(reviews)
        assert "ok" in consensus.contributing_models[0]
        assert "bad (fail)" in consensus.contributing_models[1]

    def test_merge_consensus_handles_malformed_issues(self):
        """不正なissue形式を処理"""
        reviews = [
            workflow.ModelReview(
                model="m1", summary={"issues": [{"title": "Valid"}], "confidence": 0.5}, raw=""
            ),
        ]
        consensus = workflow._merge_consensus(reviews)
        # Validなissueが含まれる
        assert "Valid" in consensus.issues


# ============================================================================
# _run_one_model テスト
# ============================================================================
class TestRunOneModel:
    @patch("nexuscore.workflows.multi_llm_review._make_client_forced")
    def test_run_one_model_success(self, mock_make_client):
        """正常なモデル実行"""
        mock_client = Mock()
        mock_client.execute.return_value = (
            '{"issues":[{"title":"Bug"}],"severity":"high","confidence":0.9}'
        )
        mock_make_client.return_value = mock_client

        result = asyncio.run(workflow._run_one_model("gpt-4", "test prompt", 100))

        assert result.ok is True
        assert result.model == "gpt-4"
        assert result.summary["confidence"] == 0.9
        assert result.summary["severity"] == "high"

    @patch("nexuscore.workflows.multi_llm_review._make_client_forced")
    def test_run_one_model_json_parse_error(self, mock_make_client):
        """JSON解析エラー時のフォールバック"""
        mock_client = Mock()
        mock_client.execute.return_value = "This is not JSON"
        mock_make_client.return_value = mock_client

        result = asyncio.run(workflow._run_one_model("model", "prompt", 100))

        assert result.ok is True
        assert result.summary["issues"] == []
        assert result.summary["confidence"] == 0.0

    @patch("nexuscore.workflows.multi_llm_review._make_client_forced")
    def test_run_one_model_client_error(self, mock_make_client):
        """クライアントエラー時の処理"""
        mock_make_client.side_effect = Exception("API Error")

        result = asyncio.run(workflow._run_one_model("bad-model", "prompt", 100))

        assert result.ok is False
        assert "API Error" in result.error
        assert result.summary["confidence"] == 0.0

    @patch("nexuscore.workflows.multi_llm_review._make_client_forced")
    def test_run_one_model_empty_response(self, mock_make_client):
        """空のレスポンス処理"""
        mock_client = Mock()
        mock_client.execute.return_value = None
        mock_make_client.return_value = mock_client

        result = asyncio.run(workflow._run_one_model("model", "prompt", 100))

        assert result.ok is True
        assert result.summary["issues"] == []


# ============================================================================
# run_consensus_review 統合テスト
# ============================================================================
class TestRunConsensusReview:
    def test_run_consensus_review_two_waves(self, monkeypatch):
        """2波での実行（最初の2モデル + 追加検証）"""
        call_order = []

        async def fake_run_one(model_name, prompt, max_tokens):
            call_order.append(model_name)
            # 最初の2つは低自信度、3つ目で高自信度
            confidence = 0.95 if model_name == "model3" else 0.4
            return workflow.ModelReview(
                model=model_name,
                summary={"issues": [{"title": f"Issue-{model_name}"}], "confidence": confidence},
                raw="",
            )

        monkeypatch.setattr(workflow, "_run_one_model", fake_run_one)

        items = [workflow.ReviewItem(path="f.py", content="code")]
        result = asyncio.run(
            workflow.run_consensus_review(
                task="test",
                items=items,
                models=["model1", "model2", "model3", "model4"],
                confidence_threshold=0.9,
                max_extra_validations=2,
                max_output_tokens=100,
            )
        )

        # 最初の2モデルは並列、その後追加モデルが実行される
        assert "model1" in call_order[:2]
        assert "model2" in call_order[:2]
        assert "model3" in call_order
        # 自信度は全モデルの平均（高自信度モデルが含まれていても平均化される）
        assert result.confidence > 0.4  # 少なくとも最低値より高い

    def test_run_consensus_review_stops_early_on_high_confidence(self, monkeypatch):
        """高自信度で早期終了"""
        call_count = 0

        async def fake_run_one(model_name, prompt, max_tokens):
            nonlocal call_count
            call_count += 1
            return workflow.ModelReview(
                model=model_name,
                summary={"issues": [], "confidence": 0.95},
                raw="",
            )

        monkeypatch.setattr(workflow, "_run_one_model", fake_run_one)

        items = [workflow.ReviewItem(path="f.py", content="code")]
        result = asyncio.run(
            workflow.run_consensus_review(
                task="test",
                items=items,
                models=["m1", "m2", "m3", "m4"],
                confidence_threshold=0.9,
            )
        )

        # 最初の2モデルで自信度到達、残りは実行されない
        assert call_count == 2
        assert result.confidence >= 0.9

    def test_run_consensus_review_respects_max_extra_validations(self, monkeypatch):
        """max_extra_validations制限を尊重"""
        call_order = []

        async def fake_run_one(model_name, prompt, max_tokens):
            call_order.append(model_name)
            return workflow.ModelReview(
                model=model_name,
                summary={"issues": [], "confidence": 0.3},  # 常に低自信度
                raw="",
            )

        monkeypatch.setattr(workflow, "_run_one_model", fake_run_one)

        items = [workflow.ReviewItem(path="f.py", content="code")]
        result = asyncio.run(
            workflow.run_consensus_review(
                task="test",
                items=items,
                models=["m1", "m2", "m3", "m4", "m5"],
                confidence_threshold=0.9,
                max_extra_validations=1,  # 2波後は1つだけ
            )
        )

        # 最初2つ + 追加1つ = 合計3つ
        assert len(call_order) == 3

    def test_run_consensus_review_single_model(self, monkeypatch):
        """単一モデルでの実行"""

        async def fake_run_one(model_name, prompt, max_tokens):
            return workflow.ModelReview(
                model=model_name,
                summary={"issues": [{"title": "Issue"}], "confidence": 0.5},
                raw="",
            )

        monkeypatch.setattr(workflow, "_run_one_model", fake_run_one)

        items = [workflow.ReviewItem(path="f.py", content="code")]
        result = asyncio.run(
            workflow.run_consensus_review(
                task="test",
                items=items,
                models=["solo"],
            )
        )

        assert len(result.contributing_models) == 1
        assert "solo" in result.contributing_models[0]


# ============================================================================
# ユーティリティ関数テスト
# ============================================================================
class TestUtilities:
    def test_parse_models_empty_string(self):
        """空文字列のパース"""
        assert workflow._parse_models("") == []

    def test_parse_models_extra_whitespace(self):
        """余分な空白の処理"""
        assert workflow._parse_models("  a  ,  b  ,  c  ") == ["a", "b", "c"]

    def test_parse_models_single_model(self):
        """単一モデル"""
        assert workflow._parse_models("gpt-4") == ["gpt-4"]
