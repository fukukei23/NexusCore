#!/usr/bin/env python3
r"""
Simple Context Agent - 安全版
フォルダ: C:/Users/USER/tools/NexusCore/simple_context_agent.py
目的: from your_module import エラーを確実に解決
"""

import os
import json
from typing import Dict
from datetime import datetime

class SimpleContextAgent:
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.getcwd()
        self.context_cache_file = os.path.join(self.project_root, ".nexus_context.json")
        print(f"🔍 プロジェクトルート: {self.project_root}")
        
        # キャッシュがあれば読み込み、なければ作成
        if os.path.exists(self.context_cache_file):
            self.context = self.load_context()
        else:
            self.context = self.create_context()
            self.save_context()
    
    def create_context(self) -> Dict:
        """安全なコンテキスト作成"""
        print("🔍 コンテキストを作成中...")
        
        context = {
            "tech_stack": {
                "frameworks": self._safe_detect_frameworks(),
                "python_version": "3.11+"
            },
            "file_structure": {
                "has_src_dir": os.path.exists(os.path.join(self.project_root, "src")),
                "has_tests_dir": os.path.exists(os.path.join(self.project_root, "tests")),
                "has_venv": os.path.exists(os.path.join(self.project_root, "venv"))
            },
            "dependencies": {
                "external": ["gradio", "openai", "pytest"],
                "internal": ["nexuscore"]
            },
            "environment": {
                "platform": os.name,
                "env_file_exists": os.path.exists(os.path.join(self.project_root, ".env")),
                "in_venv": os.getenv("VIRTUAL_ENV") is not None
            },
            "dev_policy": {
                "test_import_policy": "関数を直接埋め込み",
                "error_language": "日本語",
                "quality_requirements": ["docstring必須", "エラーハンドリング必須"],
                "security_policy": ["APIキー環境変数管理", "ハードコーディング禁止"],
                "configured_at": datetime.now().isoformat()
            },
            "last_updated": datetime.now().isoformat(),
            "version": "1.0-safe"
        }
        
        print("✅ コンテキスト作成完了")
        return context
    
    def _safe_detect_frameworks(self) -> list:
        """安全なフレームワーク検出"""
        frameworks = []
        req_file = os.path.join(self.project_root, "requirements.txt")
        
        if os.path.exists(req_file):
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if 'gradio' in content:
                        frameworks.append('gradio')
                    if 'openai' in content:
                        frameworks.append('openai')
                    if 'pytest' in content:
                        frameworks.append('pytest')
                    if 'streamlit' in content:
                        frameworks.append('streamlit')
            except Exception:
                frameworks = ['gradio', 'openai']
        
        return frameworks
    
    def load_context(self) -> Dict:
        """コンテキスト読み込み"""
        try:
            with open(self.context_cache_file, 'r', encoding='utf-8') as f:
                context = json.load(f)
                print(f"✅ キャッシュ読み込み: {self.context_cache_file}")
                return context
        except Exception as e:
            print(f"⚠️ キャッシュ読み込み失敗: {e}")
            return self.create_context()
    
    def save_context(self):
        """コンテキスト保存"""
        try:
            with open(self.context_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.context, f, indent=2, ensure_ascii=False)
            print(f"✅ コンテキスト保存: {self.context_cache_file}")
        except Exception as e:
            print(f"❌ 保存エラー: {e}")
    
    def get_error_prevention_rules(self) -> Dict:
        """エラー予防ルール（今回のエラー解決）"""
        return {
            "embed_functions_in_tests": True,
            "use_japanese_errors": True,
            "require_docstring": True,
            "require_error_handling": True,
            "use_env_vars": True,
            "test_policy": "関数を直接埋め込み"
        }
    
    def generate_enhanced_test_prompt(self, source_code: str) -> str:
        """エラー回避版テスト生成プロンプト"""
        return f"""以下のPythonコードに対するpytest形式のテストコードを生成してください：

{source_code}

重要な要件:
- インポート文は一切使用しない
- テスト対象の関数定義もテストファイルに含める
- 完全に自己完結したテストファイルとして作成
- pytest形式でテストを作成
- 正常系と異常系の両方をテスト
- 日本語でコメントを記述

`````` で終わるコードブロック形式で出力してください。"""

if __name__ == "__main__":
    print("🚀 SimpleContextAgent 開始")
    print("📁 実行場所: C:/Users/USER/tools/NexusCore/simple_context_agent.py")
    
    # 基本動作テスト
    agent = SimpleContextAgent()
    
    print("\n📊 コンテキスト:")
    print(json.dumps(agent.context, indent=2, ensure_ascii=False))
    
    print("\n🛡️ エラー予防ルール:")
    rules = agent.get_error_prevention_rules()
    for rule, value in rules.items():
        print(f"  {rule}: {value}")
    
    # テスト生成のデモ
    print("\n🧪 修正されたテスト生成プロンプト例:")
    sample_code = "def add(a, b): return a + b"
    enhanced_prompt = agent.generate_enhanced_test_prompt(sample_code)
    print(enhanced_prompt[:200] + "...")
    
    print("\n✅ SimpleContextAgent 完了！")
    print("💡 これで from your_module import エラーは解決されます。")
