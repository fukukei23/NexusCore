# ==============================================================================
# フォルダ: tools/
# ファイル名: dashboard.py
# メモ: 【JSONL形式対応・ダッシュボード】
#      - project_chronicle.jsonl を1行ずつ安全に読み込み、
#        プロジェクトの状態をダッシュボード形式で表示する。
#      - 正規表現を使わない堅牢な実装。
# ==============================================================================
import os
import json
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import argparse

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProjectDashboard:
    """プロジェクトダッシュボードクラス"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.chronicle_path = self.project_path / "project_chronicle.jsonl"
        self.chronicle_data: List[Dict[str, Any]] = []
        
    def read_chronicle_jsonl(self) -> List[Dict[str, Any]]:
        """JSONL形式のクロニクルファイルを安全に読み込む
        
        Returns:
            解析済みのJSONオブジェクトのリスト
        """
        chronicle_data = []
        
        if not self.chronicle_path.exists():
            logger.warning(f"クロニクルファイルが見つかりません: {self.chronicle_path}")
            return chronicle_data
        
        try:
            with open(self.chronicle_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:  # 空行をスキップ
                        continue
                        
                    try:
                        # 各行を個別のJSONオブジェクトとしてパース
                        json_obj = json.loads(line)
                        chronicle_data.append(json_obj)
                    except json.JSONDecodeError as e:
                        logger.error(f"Line {line_num}: JSON parse error - {e}")
                        logger.debug(f"Problematic line: {line[:100]}...")
                        continue
                        
        except Exception as e:
            logger.error(f"クロニクルファイル読み込みエラー: {e}")
        
        logger.info(f"✅ {len(chronicle_data)} 件のレコードを読み込みました")
        return chronicle_data
    
    def load_project_data(self) -> Dict[str, Any]:
        """プロジェクトデータを読み込む"""
        self.chronicle_data = self.read_chronicle_jsonl()
        
        # 最新のGENESISレコードを取得
        genesis_record = None
        for record in reversed(self.chronicle_data):
            if record.get("event") == "GENESIS":
                genesis_record = record
                break
        
        # 分析スナップショットを時系列順に取得
        snapshots = [
            record for record in self.chronicle_data 
            if record.get("event") == "ANALYSIS_SNAPSHOT"
        ]
        
        return {
            "genesis": genesis_record,
            "snapshots": snapshots,
            "total_records": len(self.chronicle_data),
            "last_updated": self.chronicle_data[-1].get("timestamp") if self.chronicle_data else None
        }
    
    def format_timestamp(self, timestamp_str: str) -> str:
        """タイムスタンプを読みやすい形式にフォーマット"""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            return timestamp_str
    
    def display_project_overview(self, project_data: Dict[str, Any]) -> None:
        """プロジェクト概要を表示"""
        print("=" * 80)
        print("🚀 NexusCore Project Dashboard")
        print("=" * 80)
        print()
        
        # 基本情報
        print("📊 **基本情報**")
        print(f"   プロジェクトパス: {self.project_path}")
        print(f"   総レコード数: {project_data['total_records']}")
        if project_data['last_updated']:
            print(f"   最終更新: {self.format_timestamp(project_data['last_updated'])}")
        print()
        
        # Genesis情報
        if project_data['genesis']:
            genesis = project_data['genesis']
            print("🌟 **Genesis Block**")
            print(f"   作成日時: {self.format_timestamp(genesis.get('timestamp', 'N/A'))}")
            print(f"   エージェント: {genesis.get('agent', 'N/A')}")
            print(f"   バージョン: {genesis.get('version', 'N/A')}")
            
            # 統合サマリーを表示
            summary = genesis.get('data', {}).get('integrated_summary', {})
            if summary and isinstance(summary, dict):
                print("\n   📝 **プロジェクトサマリー**")
                for key, value in summary.items():
                    if isinstance(value, str) and len(value) > 100:
                        display_value = value[:97] + "..."
                    else:
                        display_value = str(value)
                    print(f"   • {key.replace('_', ' ').title()}: {display_value}")
            print()
        
        # スナップショット情報
        snapshots = project_data['snapshots']
        print(f"📈 **分析スナップショット** ({len(snapshots)} 件)")
        if snapshots:
            for i, snapshot in enumerate(snapshots[-5:], 1):  # 最新5件を表示
                timestamp = self.format_timestamp(snapshot.get('timestamp', 'N/A'))
                agent = snapshot.get('agent', 'N/A')
                print(f"   {i}. {timestamp} - {agent}")
        else:
            print("   まだスナップショットはありません。")
        print()
    
    def display_detailed_analysis(self, project_data: Dict[str, Any]) -> None:
        """詳細分析を表示"""
        print("🔍 **詳細分析**")
        print("-" * 60)
        
        if not project_data['genesis']:
            print("Genesis ブロックが見つかりません。")
            return
        
        genesis_data = project_data['genesis'].get('data', {})
        summary = genesis_data.get('integrated_summary', {})
        
        if not summary or 'error' in summary:
            print("統合サマリーにエラーがあります:")
            if 'error' in summary:
                print(f"   エラー: {summary.get('error')}")
                print(f"   詳細: {summary.get('details', 'N/A')}")
            return
        
        # 各セクションを詳細表示
        sections = [
            ("mission_and_purpose", "🎯 ミッション・目的"),
            ("architecture_and_agents", "🏗️ アーキテクチャ・エージェント"),
            ("policies_and_rules", "📋 ポリシー・ルール"),
            ("knowledge_and_experience", "🧠 知識・経験"),
            ("dependencies_and_stack", "📦 依存関係・スタック"),
            ("testing_philosophy", "🧪 テスト哲学"),
            ("ui_ux_philosophy", "🎨 UI/UX哲学"),
            ("meta_capabilities", "🔮 メタ機能")
        ]
        
        for key, title in sections:
            if key in summary:
                print(f"\n{title}")
                content = summary[key]
                if isinstance(content, str):
                    # 長いテキストを適切に改行
                    lines = content.split('\n')
                    for line in lines:
                        if len(line) > 70:
                            words = line.split()
                            current_line = ""
                            for word in words:
                                if len(current_line + word) > 70:
                                    print(f"   {current_line}")
                                    current_line = word + " "
                                else:
                                    current_line += word + " "
                            if current_line:
                                print(f"   {current_line}")
                        else:
                            print(f"   {line}")
                elif isinstance(content, (dict, list)):
                    print(f"   {json.dumps(content, ensure_ascii=False, indent=2)}")
                else:
                    print(f"   {content}")
        print()
    
    def display_statistics(self, project_data: Dict[str, Any]) -> None:
        """統計情報を表示"""
        print("📊 **統計情報**")
        print("-" * 60)
        
        # イベント種別ごとの統計
        event_counts = {}
        agent_counts = {}
        
        for record in self.chronicle_data:
            event = record.get('event', 'UNKNOWN')
            agent = record.get('agent', 'UNKNOWN')
            
            event_counts[event] = event_counts.get(event, 0) + 1
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        print("イベント種別:")
        for event, count in sorted(event_counts.items()):
            print(f"   • {event}: {count} 件")
        
        print("\nエージェント別:")
        for agent, count in sorted(agent_counts.items()):
            print(f"   • {agent}: {count} 件")
        
        # 時系列統計
        if self.chronicle_data:
            first_record = self.chronicle_data[0]
            last_record = self.chronicle_data[-1]
            
            print(f"\n期間:")
            print(f"   • 開始: {self.format_timestamp(first_record.get('timestamp', 'N/A'))}")
            print(f"   • 最新: {self.format_timestamp(last_record.get('timestamp', 'N/A'))}")
        print()
    
    def export_summary_json(self, output_path: str = None) -> str:
        """サマリーをJSONファイルとして出力"""
        if output_path is None:
            output_path = str(self.project_path / "dashboard_summary.json")
        
        project_data = self.load_project_data()
        
        summary_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_path": str(self.project_path),
            "total_records": project_data['total_records'],
            "last_updated": project_data['last_updated'],
            "genesis_summary": project_data['genesis'].get('data', {}).get('integrated_summary', {}) if project_data['genesis'] else {},
            "snapshots_count": len(project_data['snapshots'])
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ サマリーをエクスポートしました: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"サマリーエクスポートエラー: {e}")
            return ""
    
    def run_dashboard(self, detailed: bool = False, export: bool = False) -> None:
        """ダッシュボードを実行"""
        try:
            project_data = self.load_project_data()
            
            # 基本情報表示
            self.display_project_overview(project_data)
            
            # 詳細分析表示（オプション）
            if detailed:
                self.display_detailed_analysis(project_data)
            
            # 統計情報表示
            self.display_statistics(project_data)
            
            # JSONエクスポート（オプション）
            if export:
                export_path = self.export_summary_json()
                if export_path:
                    print(f"📄 サマリーファイル: {export_path}")
            
        except Exception as e:
            logger.error(f"ダッシュボード実行エラー: {e}", exc_info=True)

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="NexusCore Project Dashboard")
    parser.add_argument("project_path", help="プロジェクトディレクトリのパス")
    parser.add_argument("--detailed", "-d", action="store_true", help="詳細分析を表示")
    parser.add_argument("--export", "-e", action="store_true", help="サマリーをJSONファイルに出力")
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).absolute()
    
    if not project_path.is_dir():
        print(f"エラー: 指定されたパスは有効なディレクトリではありません: {project_path}")
        sys.exit(1)
    
    dashboard = ProjectDashboard(str(project_path))
    dashboard.run_dashboard(detailed=args.detailed, export=args.export)

if __name__ == "__main__":
    main()
