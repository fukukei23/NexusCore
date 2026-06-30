"""brownfield オーケストレーション共通コア（run_brownfield_stream）。

旧 brownfield_orchestrator.py (commit 206fc75a 時点) L131-233 の
run_brownfield_stream をロジック不改で転記したもの（振る舞い保存）。
変更点は import 文の再編成のみ。関数本体は 1 文字も変更していない。

※ 既知の挙動: 本関数内で _do_phase(...) が yield from 無しで呼ばれており、
   各フェーズスクリプトが実行されない（イベント列に現れない）。これはバグだが
   「振る舞い保存」のためそのまま保持する（別 Issue 化）。baseline イベント列も
   この挙動を含むため、本モジュールが同一ロジックなら baseline と一致する。
"""
from __future__ import annotations
import os, json, shlex, shutil, zipfile, traceback
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Callable, Generator, Optional

from .utils import (
    stream_run,            # ★ from .utils import（mock 境界・N1対策）
    load_policy_meta,
    inject_policy_meta_to_manifest,
    candidate_paths,
    phase_cmd,
    now_tag,
    PROJECT_TOP,
    PHASE_KEYS,
    DEFAULT_PROFILES,
    JST,
)


# ---------- オーケストレーション（共通コア） ----------------------------------
def run_brownfield_stream(
    project_root: str, out_root: str, profiles: List[str], selected_phases: List[str],
    policy_profile_ui: str, policy_version_ui: str, policy_icon_ui: str,
    richness_mode: str, include_full_archive: bool,
) -> Generator[Tuple[str, str, Optional[str]], None, None]:
    """Brownfield スナップショットをストリーミング実行。

    Yields: (log_text: str, summary: str, zip_path: str | None)
      ※ log_text は「それまでの全行を結合した文字列」
    Returns: なし（yield のみ）
    """
    log_buf: List[str] = []; snap_dir: Optional[Path] = None; emitted = False
    def emit(line: str, summary: str = "", zip_path: Optional[str] = None):
        print(line, end='', flush=True)
        nonlocal emitted; log_buf.append(line); emitted = True
        yield ("".join(log_buf), summary, zip_path)
    try:
        project_root_path = Path(project_root).resolve()
        if project_root_path.is_file(): project_root_path = project_root_path.parent
        out_root_path = Path(out_root).resolve(); out_root_path.mkdir(parents=True, exist_ok=True)
        base_meta = load_policy_meta()
        if policy_profile_ui.strip(): base_meta["policy_profile"] = policy_profile_ui.strip()
        if policy_version_ui.strip(): base_meta["policy_version"] = policy_version_ui.strip()
        if policy_icon_ui.strip():    base_meta["policy_icon"] = policy_icon_ui.strip()
        tag = now_tag(); snap_dir = out_root_path / tag
        for sub in PHASE_KEYS: (snap_dir / sub).mkdir(parents=True, exist_ok=True)
        manifest = {"snapshot_tag": tag, "project_root": str(project_root_path), "generated_at": datetime.now(JST).isoformat(), "phases": {}, "tool_root": str(PROJECT_TOP), "orchestrator": f"brownfield_orchestrator.py@v2.13", "richness_mode": richness_mode, "full_source_archive_included": include_full_archive}
        (snap_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        run_set = set(selected_phases or PHASE_KEYS)
        richness_arg = ["--richness-level", richness_mode] if richness_mode != "Light (fast)" else []
        def _do_phase(key: str, script_name: str, args_builder: Callable[[Path], List[str]]):
            if key not in run_set:
                manifest["phases"][key] = {"status": "skipped", "reason": "user-specified"}
            else:
                paths = candidate_paths(script_name)
                if not paths:
                    manifest["phases"][key] = {"status":"skipped","reason":f"{script_name} not found"}
                else:
                    save_dir = snap_dir / key
                    log_path = save_dir / f"{script_name.replace('.py','')}.log"
                    final_args = args_builder(save_dir) + richness_arg
                    cmd_list = phase_cmd(paths[0], final_args)
                    yield from emit(f"\n--- [{key}] {' '.join(shlex.quote(x) for x in cmd_list)}\n")
                    gen = stream_run(cmd_list, cwd=PROJECT_TOP); ok, out_text = False, ""
                    try:
                        while True: yield from emit(next(gen))
                    except StopIteration as si: ok, out_text = si.value
                    except Exception as e:
                        tb_str = f"[phase-exception] {e}\n{traceback.format_exc()}"
                        ok, out_text = False, tb_str; yield from emit(out_text)
                    log_path.write_text(out_text, encoding="utf-8")
                    manifest["phases"][key] = {"status": "ok" if ok else "error", "script": str(paths[0]), "output_dir": str(save_dir), "log": str(log_path)}
            (snap_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        yield from emit("スナップショット作成を開始します...\n")
        _do_phase("structure", "export_structure.py", lambda s: [str(project_root_path)])
        _do_phase("snapshot", "project_structure_and_code_export.py", lambda s: ["--root", str(project_root_path), "--out", str(s)])
        _do_phase("unified", "unified_analyzer.py", lambda s: ["--root", str(project_root_path), "--out", str(s)])
        _do_phase("graphs", "graph_builder.py", lambda s: ["--root", str(project_root_path), "--out", str(s)])
        _do_phase("history", "genesis_analyzer.py", lambda s: ["--root", str(project_root_path), "--out", str(s)])
        _do_phase("quality", "code_analyzer.py", lambda s: ["--root", str(project_root_path), "--out", str(s)])
        _do_phase("ai_export", "code_export_for_ai.py", lambda s: sum([["--root", str(project_root_path), "--out", str(s / p), "--profile", p] for p in (profiles or DEFAULT_PROFILES)], []))
    except Exception as e:
        yield from emit(f"\n[CRITICAL ERROR] 解析プロセスで重大な例外が発生しました:\n{e}\n{traceback.format_exc()}")
    finally:
        if snap_dir and snap_dir.exists():
            if include_full_archive:
                yield from emit("\nソースコード全体のアーカイブを作成しています...（時間がかかる場合があります）\n")
                archive_path = snap_dir / "_source_archive.zip"
                exclude_dirs = {'.git', '.idea', '.vscode', '__pycache__', 'venv', 'node_modules', 'dist', 'build'}
                try:
                    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for root, dirs, files in os.walk(project_root_path):
                            dirs[:] = [d for d in dirs if d not in exclude_dirs]
                            for file in files:
                                file_path = Path(root) / file
                                zf.write(file_path, file_path.relative_to(project_root_path))
                    manifest_path = snap_dir / "manifest.json"
                    if manifest_path.exists():
                        data = json.loads(manifest_path.read_text(encoding="utf-8"))
                        data["full_source_archive"] = {"path": str(archive_path.relative_to(snap_dir)), "size_bytes": archive_path.stat().st_size}
                        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    yield from emit(f"ソースコードのアーカイブが完了しました: {archive_path}\n")
                except Exception as e:
                    yield from emit(f"[ERROR] ソースコードのアーカイブ作成に失敗しました: {e}\n")
            def summarize_snapshot(p: Path) -> str:
                m = p / "manifest.json"; r = p / "README.md"; lines: List[str] = [f"### 📁 Snapshot: `{p.name}`"]
                if m.exists():
                    try:
                        d = json.loads(m.read_text(encoding="utf-8"))
                        lines.extend([f"- richness_mode: `{d.get('richness_mode','N/A')}`"])
                        if d.get("full_source_archive_included"): lines.append(f"- full_source_archive: ✅ Included (`_source_archive.zip`)")
                        lines.extend([f"- generated_at: `{d.get('generated_at','')}`", f"- project_root: `{d.get('project_root','')}`"])
                        if d.get("policy_profile"): lines.append(f"- policy: {d['policy_profile']} ({d.get('policy_version','v?')}) {d.get('policy_icon','')}")
                        lines.append("- phases:"); [lines.append(f"  - {k}: {v.get('status','')}") for k, v in (d.get("phases") or {}).items()]
                    except Exception: lines.append("- manifest.json: 解析失敗")
                lines.append("\n#### 主要フォルダ"); [lines.append(f"- `{d}`") for s in PHASE_KEYS if (d := p / s).exists()]
                return "\n".join(lines)
            inject_policy_meta_to_manifest(snap_dir, load_policy_meta())
            (snap_dir / "README.md").write_text(f"# Brownfield Snapshot ({snap_dir.name})\n- generated_at: {datetime.now(JST).isoformat()}\n- project_root: {project_root}\nこのスナップショットは、既存システムの構造/履歴/品質/AIエクスポートをまとめたものです。", encoding="utf-8")
            summary_md = summarize_snapshot(snap_dir); zip_path: Optional[str] = None
            try:
                yield from emit("\nスナップショットをZIPファイルに圧縮しています...\n")
                zip_path = str(shutil.make_archive(str(snap_dir), "zip", root_dir=str(snap_dir)))
                yield from emit("圧縮が完了しました。\n", summary_md, zip_path)
            except Exception as e: yield from emit(f"\n[ERROR] ZIPファイルの作成に失敗しました:\n{e}\n", summary_md)
            yield from emit("\n[OK] 全ての処理が完了しました。\n", summary_md, zip_path)
        elif not emitted:
            yield from emit("\n[ERROR] 初期化に失敗し、処理を開始できませんでした。\n")
