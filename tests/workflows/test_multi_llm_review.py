import asyncio

import pytest

from nexuscore.workflows import multi_llm_review as workflow


def test_merge_consensus_aggregates_issues():
    reviews = [
        workflow.ModelReview(model="m1", summary={"issues": [{"title": "A"}], "confidence": 0.6}, raw=""),
        workflow.ModelReview(model="m2", summary={"issues": [{"title": "B"}, {"title": "A"}], "confidence": 0.8}, raw=""),
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
