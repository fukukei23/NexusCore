# ==============================================================================
# brownfield/__main__.py — エントリポイント（リファクタ v3 P1 / Task6）
# ==============================================================================
# 転記元: tools/brownfield_orchestrator.py L445-485 (parse_args, main)
# 変更点: シグネチャ parse_args(argv=None) / main(argv=None)->int
#         main 本体ロジック不改
# ==============================================================================
from __future__ import annotations
import os
import argparse
from pathlib import Path
from typing import Optional

from .ui import build_ui, auto_launch_with_increment
from .core import run_brownfield_stream
from .utils import (
    PICKER_ROOT,
    PHASE_KEYS,
    DEFAULT_PROFILES,
    DEFAULT_OUT,
    load_policy_meta,
)


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Brownfield Orchestrator — 構造 & 履歴の見える化 (UI/CLI)"
    )
    p.add_argument(
        "--project-root",
        type=str,
        default=str(PICKER_ROOT),
        help="解析対象のプロジェクトルート（CLI時）",
    )
    p.add_argument(
        "--out", type=str, default=str(DEFAULT_OUT), help="スナップショット出力先（親）"
    )
    p.add_argument(
        "--profiles",
        type=str,
        default=",".join(DEFAULT_PROFILES),
        help="AIエクスポートプロフィール（CSV）",
    )
    p.add_argument("--skip", type=str, default="", help="スキップするフェーズ（CSV）")
    p.add_argument(
        "--policy-profile",
        type=str,
        default="",
        help="manifest へ注入する policy_profile（任意）",
    )
    p.add_argument(
        "--policy-version",
        type=str,
        default="",
        help="manifest へ注入する policy_version（任意）",
    )
    p.add_argument(
        "--policy-icon",
        type=str,
        default="",
        help="manifest へ注入する policy_icon（任意）",
    )
    p.add_argument(
        "--richness",
        type=str,
        default="Light (fast)",
        choices=["Light (fast)", "Code-Rich (more .py)"],
        help="収集するコードの量を調整",
    )
    p.add_argument(
        "--full-archive",
        action="store_true",
        help="ソースコード全体のアーカイブをZIPで同梱する",
    )
    p.add_argument("--ui", action="store_true", help="Gradio UI を起動")
    return p.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)
    if args.ui:
        base_port = int(os.getenv("NEXUS_BROWNFIELD_UI_PORT", "7862"))
        share = os.getenv("NEXUS_BROWNFIELD_UI_SHARE", "0") == "1"
        demo = build_ui()
        auto_launch_with_increment(demo, base_port, share)
        return 0
    else:
        target = Path(args.project_root).resolve()
        if target.is_file():
            target = target.parent
        out_root = Path(args.out).resolve()
        out_root.mkdir(parents=True, exist_ok=True)
        profiles = (
            [s.strip() for s in (args.profiles or "").split(",") if s.strip()]
            or DEFAULT_PROFILES
        )
        skip = [s.strip() for s in (args.skip or "").split(",") if s.strip()]
        selected_phases = [p for p in PHASE_KEYS if p not in set(skip)]
        meta = load_policy_meta()
        if args.policy_profile:
            meta["policy_profile"] = args.policy_profile
        if args.policy_version:
            meta["policy_version"] = args.policy_version
        if args.policy_icon:
            meta["policy_icon"] = args.policy_icon
        summary, zip_path = "", None
        gen = run_brownfield_stream(
            str(target),
            str(out_root),
            profiles,
            selected_phases,
            meta.get("policy_profile", ""),
            meta.get("policy_version", ""),
            meta.get("policy_icon", ""),
            args.richness,
            args.full_archive,
        )
        if gen:
            for _, summary, zip_path in gen:
                pass
        print(summary)
        if zip_path:
            print(f"[ZIP] {zip_path}")
        return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
