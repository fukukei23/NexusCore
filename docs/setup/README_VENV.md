# 仮想環境の使い方（簡単版）

## 🚀 超簡単な方法

プロジェクトルートで以下を実行するだけ：

```bash
source activate
```

または

```bash
. activate
```

または

```bash
source activate_venv.sh
```

または（直接的な方法）

```bash
source venv/bin/activate
```

これだけで仮想環境が有効化されます！

**推奨**: `source activate` が最も簡単です。

## 📝 使い方の例

```bash
# プロジェクトディレクトリに移動
cd /home/yn441611/NexusCore

# 仮想環境を有効化（これだけ！）
source activate

# これで開発ツールが使えます
black src tests
ruff check src tests
mypy src
```

## 💡 覚え方

- `activate` = 「有効化する」という意味
- `source` = スクリプトを現在のシェルで実行
- プロジェクトルートに `activate` ファイルがあるので、それを `source` するだけ

## 🔄 仮想環境を無効化する

```bash
deactivate
```

## ⚠️ 注意

- 新しいターミナルを開くたびに `source activate` を実行する必要があります
- ターミナルのプロンプトに `(venv)` が表示されていれば有効化されています
- **重要**: `source venv` は動作しません（`venv` はディレクトリ名です）

