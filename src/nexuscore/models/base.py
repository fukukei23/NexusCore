"""DB インスタンスの定義（層の最下流・他の nexuscore パッケージに依存しない）。

`db` を webapp から切り離してここに置くことで、models が webapp へ依存しなくなり、
api / integration が「モデルを使うためだけに webapp を import する」構造を解消する。

依存方向:
    models  ←  webapp / api / integration / services / cli
    （models はどの nexuscore パッケージにも依存しない）

初期化は従来どおり `webapp.create_app()` の `db.init_app(app)` が行う。
定義場所が変わるだけで、Flask-SQLAlchemy の利用方法は変わらない。
"""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

# グローバルな DB インスタンス（models/entities.py と各層が共有する）
db = SQLAlchemy()

__all__ = ["db"]
