# ==============================================================================
# フォルダ: tools/
# ファイル名: streamlit_dashboard.py
# メモ: 【エンジン・コックピット分離版】
#      - あなたが作成した `dashboard.py` をデータ処理の「エンジン」としてインポート。
#      - このファイルは、そのエンジンから受け取ったデータを表示することに特化した
#        「コックピTピット」の役割を担う。
#      - これにより、ロジックとUIが完全に分離され、保守性が劇的に向上する。
#
# 使い方:
# 1. ターミナルでプロジェクトルートに移動する。
#    cd C:\Users\USER\tools\NexusCore
# 2. 以下のコマンドを実行する。
#    streamlit run tools/streamlit_dashboard.py
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pathlib import Path

# --- あなたが作成したエンジン（dashboard.py）をインポート ---
try:
    # toolsフォルダをPythonの検索パスに追加
    import sys
    tools_path = str(Path(__file__).parent.absolute())
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
    
    from dashboard import ProjectDashboard
except ImportError as e:
    st.error(f"エラー: `dashboard.py` のインポートに失敗しました。同じフォルダに存在することを確認してください。: {e}")
    st.stop()

# --- 定数 ---
# このスクリプトから見たプロジェクトルートのパス
PROJECT_ROOT_PATH = str(Path(__file__).parent.parent.absolute())

def main_dashboard():
    """
    StreamlitのUIを構築するメイン関数
    """
    st.set_page_config(page_title="NexusCore Evolution Cockpit", layout="wide")
    st.title("🚀 NexusCore Evolution Cockpit")
    st.caption("プロジェクトの進化の軌跡を可視化・分析します。")

    # --- エンジンを初期化し、データをロード ---
    engine = ProjectDashboard(PROJECT_ROOT_PATH)
    project_data = engine.load_project_data()

    if not project_data or not project_data.get("total_records"):
        st.warning("年代記ファイルに分析可能なデータがありません。")
        st.info("先に `tools/genesis_analyzer.py` を実行してデータを生成してください。")
        st.stop()

    # --- KPIメトリクスの表示 ---
    st.header("最新の状態 (KPIs)")
    col1, col2, col3 = st.columns(3)
    last_updated = project_data.get('last_updated', 'N/A')
    if last_updated != 'N/A':
        last_updated = engine.format_timestamp(last_updated)
    
    col1.metric("最終更新日時", last_updated.replace(" UTC", ""))
    col2.metric("総レコード数", project_data.get('total_records', 0))
    col3.metric("スナップショット数", len(project_data.get('snapshots', [])))

    # --- データフレームの作成 ---
    # ここでは可視化のために簡易的なデータフレームを作成
    snapshot_df = pd.DataFrame(project_data.get('snapshots', []))
    if not snapshot_df.empty:
        snapshot_df['timestamp_dt'] = pd.to_datetime(snapshot_df['timestamp'])
        
        # 仮のメトリクス（将来的に構造化データに置き換える）
        snapshot_df['agent_count'] = snapshot_df['data'].apply(
            lambda d: len(d.get('integrated_summary', {}).get('architecture_and_agents', '').split('*')) - 1
        )

        # --- メインチャートの表示 ---
        st.header("進化の軌跡")
        fig = px.line(snapshot_df, x='timestamp_dt', y=['agent_count'],
                      title='エージェント数の推移（仮）', markers=True,
                      labels={'timestamp_dt': '日時', 'value': 'エージェント数', 'variable': '指標'})
        st.plotly_chart(fig, use_container_width=True)

    # --- Genesis Block の詳細表示 ---
    st.header("🌟 Genesis Block Summary")
    genesis_record = project_data.get('genesis')
    if genesis_record:
        summary = genesis_record.get('data', {}).get('integrated_summary', {})
        with st.expander("プロジェクトの創世記（サマリー）を表示"):
            st.json(summary)
    else:
        st.info("Genesis Blockが見つかりません。")

if __name__ == "__main__":
    main_dashboard()
