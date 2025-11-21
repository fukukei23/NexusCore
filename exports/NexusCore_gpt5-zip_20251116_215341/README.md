# NexusCore

**NexusCore** は、自律型 AI エージェント群を活用した  
ソフトウェア開発支援／BUYMA 無在庫転売支援エコシステムです。  

- 🧠 **AIコード修復支援 / 開発支援**  
- 🛒 **BUYMA 無在庫転売自動化ツール**  
- ☁️ **SaaS 展開を意識した分離設計**  

---

## 📂 プロジェクト構成

- `src/nexuscore/` … AIエージェント群・Orchestrator・LLM Router
- `tools/` … 補助ツール (構造エクスポート, ダッシュボード, 解析)
- `exports/` … エクスポート済み成果物
- `output/` … 実行ログや集計ファイル
- `tests/` … pytest ベースのテスト群
- `pyproject.toml` … **依存定義の正本**
- `requirements.lock.txt` … **ロックファイル（CI/CD もこれを使用）**

---

## 🚀 Quick Start

### 🔧 前提条件

- Python **3.11+**
- Git
- Docker (任意、サービス統合用)
- **pip-tools** (`pip install pip-tools`)

---

### 1. 環境変数設定

```powershell
cp .env.template .env
# APIキーなどを記入
