# ==============================================================================
# ファイル: tests/config/test_constitution_loader.py
# 目的  : ConstitutionLoader のテスト
# ==============================================================================
import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from src.nexuscore.config.constitution_loader import (
    ConstitutionLoader,
    get_constitution,
    get_tier1_config,
    get_tier2_config,
    reload_constitution
)


class TestConstitutionLoader:
    """ConstitutionLoader のテスト"""

    def test_singleton_pattern(self):
        """シングルトンパターンのテスト"""
        loader1 = ConstitutionLoader()
        loader2 = ConstitutionLoader()

        assert loader1 is loader2, "ConstitutionLoaderはシングルトンであるべき"

    def test_get_constitution_returns_dict(self):
        """憲法が辞書として返されることをテスト"""
        constitution = get_constitution()

        assert isinstance(constitution, dict)
        assert "quality_gates" in constitution
        assert "security" in constitution

    def test_get_tier1_config(self):
        """Tier 1設定の取得をテスト"""
        tier1 = get_tier1_config()

        assert isinstance(tier1, dict)
        assert "test_coverage_min" in tier1
        assert "pylint_score_min" in tier1

    def test_get_tier2_config(self):
        """Tier 2設定の取得をテスト"""
        tier2 = get_tier2_config()

        assert isinstance(tier2, dict)
        assert "mutation_score_min" in tier2

    def test_default_constitution_when_file_not_found(self):
        """ファイルが見つからない場合、デフォルト憲法を使用"""
        # ConstitutionLoaderをリセット
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

        with patch.object(ConstitutionLoader, '_find_constitution_file', return_value=None):
            loader = ConstitutionLoader()
            constitution = loader.get_constitution()

            assert constitution["project"]["name"] == "NexusCore"
            assert constitution["quality_gates"]["tier1"]["test_coverage_min"] == 90

    def test_environment_specific_config(self):
        """環境別設定のマージをテスト"""
        base = {
            "quality_gates": {
                "tier1": {
                    "test_coverage_min": 90
                }
            },
            "environments": {
                "development": {
                    "quality_gates": {
                        "tier1": {
                            "test_coverage_min": 80
                        }
                    }
                }
            }
        }

        loader = ConstitutionLoader()
        merged = loader._merge_environment_config(base, "development")

        assert merged["quality_gates"]["tier1"]["test_coverage_min"] == 80

    def test_deep_merge(self):
        """ディープマージのテスト"""
        base = {
            "a": {
                "b": {
                    "c": 1,
                    "d": 2
                },
                "e": 3
            },
            "f": 4
        }

        override = {
            "a": {
                "b": {
                    "c": 10  # 上書き
                },
                "g": 30  # 追加
            }
        }

        loader = ConstitutionLoader()
        result = loader._deep_merge(base, override)

        assert result["a"]["b"]["c"] == 10  # 上書きされている
        assert result["a"]["b"]["d"] == 2   # 保持されている
        assert result["a"]["e"] == 3        # 保持されている
        assert result["a"]["g"] == 30       # 追加されている
        assert result["f"] == 4             # 保持されている

    def test_validation_missing_required_section(self):
        """必須セクションが不足している場合、エラーを発生"""
        loader = ConstitutionLoader()

        invalid_constitution = {
            "project": {"name": "Test"}
            # quality_gates セクションが不足
        }

        with pytest.raises(ValueError, match="必須セクション"):
            loader._validate_constitution(invalid_constitution)

    def test_validation_invalid_coverage_range(self):
        """カバレッジが範囲外の場合、エラーを発生"""
        loader = ConstitutionLoader()

        invalid_constitution = {
            "quality_gates": {
                "tier1": {
                    "test_coverage_min": 150,  # 範囲外
                    "pylint_score_min": 8.0
                }
            },
            "security": {}
        }

        with pytest.raises(ValueError, match="0-100 の範囲"):
            loader._validate_constitution(invalid_constitution)

    def test_reload_constitution(self):
        """憲法の再読み込みをテスト"""
        # 初回読み込み
        constitution1 = get_constitution()

        # 再読み込み
        constitution2 = reload_constitution()

        assert isinstance(constitution2, dict)
        # 基本構造が同じであることを確認
        assert "quality_gates" in constitution2
        assert "tier1" in constitution2["quality_gates"]
        # カバレッジは環境によって異なるので、範囲チェックのみ
        coverage = constitution2["quality_gates"]["tier1"]["test_coverage_min"]
        assert 0 <= coverage <= 100, f"カバレッジは0-100の範囲: {coverage}"


class TestConstitutionIntegration:
    """実際の憲法ファイルを使用した統合テスト"""

    def test_actual_constitution_file_loads(self):
        """実際の憲法ファイルが読み込めることをテスト"""
        # プロジェクトルートの憲法ファイルを読み込み
        constitution = get_constitution()

        # 基本構造をチェック
        assert "project" in constitution
        assert "quality_gates" in constitution
        assert "security" in constitution
        assert "fkb" in constitution

        # Tier 1の値をチェック
        tier1 = constitution["quality_gates"]["tier1"]
        assert tier1["test_coverage_min"] >= 0
        assert tier1["test_coverage_min"] <= 100
        assert tier1["pylint_score_min"] >= 0
        assert tier1["pylint_score_min"] <= 10

        # Tier 2の値をチェック
        tier2 = constitution["quality_gates"]["tier2"]
        assert tier2["mutation_score_min"] >= 0
        assert tier2["mutation_score_min"] <= 100

    def test_npe_config_accessible(self):
        """NPE設定がアクセス可能であることをテスト"""
        loader = ConstitutionLoader()
        npe_config = loader.get_npe_config()

        assert isinstance(npe_config, dict)
        assert "enabled" in npe_config
        assert "detect_pem_keys" in npe_config

    def test_error_handling_config_accessible(self):
        """エラーハンドリング設定がアクセス可能であることをテスト"""
        loader = ConstitutionLoader()
        error_config = loader.get_error_handling_config()

        assert isinstance(error_config, dict)
        assert "retry" in error_config

    def test_fkb_config_accessible(self):
        """FKB設定がアクセス可能であることをテスト"""
        loader = ConstitutionLoader()
        fkb_config = loader.get_fkb_config()

        assert isinstance(fkb_config, dict)
        assert "learning" in fkb_config
