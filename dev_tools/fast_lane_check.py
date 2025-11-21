"""
Fast lane regression gate:
- Measures git diff size (files / lines) against base branch.
- Blocks large changes unless FAST_LANE_FORCE is set.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass
class FastLaneConfig:
    base_branch: str = "origin/main"
    max_changed_files: int = 30
    max_total_changed_lines: int = 800
    max_per_file_changed_lines: int = 400
    allow_override_env: str = "FAST_LANE_FORCE"


@dataclass
class FileChangeStat:
    path: str
    added: int
    deleted: int

    @property
    def total(self) -> int:
        return self.added + self.deleted


@dataclass
class FastLaneResult:
    is_fast_lane_eligible: bool
    reason: str
    details: List[FileChangeStat]


def run_cmd(cmd: Sequence[str]) -> Tuple[int, str, str]:
    proc = subprocess.Popen(
        list(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    out, err = proc.communicate()
    return proc.returncode, (out or "").strip(), (err or "").strip()


def detect_merge_base(base_branch: str) -> Optional[str]:
    code, out, _ = run_cmd(["git", "merge-base", base_branch, "HEAD"])
    if code != 0 or not out:
        return None
    return out.strip()


def _parse_numstat(lines: Iterable[str]) -> List[FileChangeStat]:
    stats: List[FileChangeStat] = []
    for line in lines:
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added_s, deleted_s, path = parts
        if added_s == "-" or deleted_s == "-":
            added = deleted = 0
        else:
            try:
                added = int(added_s)
                deleted = int(deleted_s)
            except ValueError:
                added = deleted = 0
        stats.append(FileChangeStat(path=path, added=added, deleted=deleted))
    return stats


def collect_diff_stats(base_ref: str) -> List[FileChangeStat]:
    code, out, err = run_cmd(["git", "diff", "--numstat", f"{base_ref}...HEAD"])
    if code != 0:
        raise RuntimeError(f"git diff failed: {err or 'unknown error'}")
    if not out:
        return []
    return _parse_numstat(out.splitlines())


def evaluate_fast_lane(
    config: FastLaneConfig, stats: Optional[List[FileChangeStat]] = None
) -> FastLaneResult:
    override_flag = os.getenv(config.allow_override_env, "").lower()
    if override_flag in {"1", "true", "yes"}:
        return FastLaneResult(
            is_fast_lane_eligible=True,
            reason=f"Override by {config.allow_override_env}",
            details=[],
        )

    if stats is None:
        base_ref = detect_merge_base(config.base_branch) or config.base_branch
        stats = collect_diff_stats(base_ref)

    if not stats:
        return FastLaneResult(
            is_fast_lane_eligible=True,
            reason="No diff against base",
            details=[],
        )

    file_count = len(stats)
    total_changed_lines = sum(s.total for s in stats)
    worst_per_file = max((s.total for s in stats), default=0)

    if file_count > config.max_changed_files:
        return FastLaneResult(
            is_fast_lane_eligible=False,
            reason=f"Too many changed files: {file_count} > {config.max_changed_files}",
            details=stats,
        )

    if total_changed_lines > config.max_total_changed_lines:
        return FastLaneResult(
            is_fast_lane_eligible=False,
            reason=(
                "Too many changed lines in total: "
                f"{total_changed_lines} > {config.max_total_changed_lines}"
            ),
            details=stats,
        )

    if worst_per_file > config.max_per_file_changed_lines:
        return FastLaneResult(
            is_fast_lane_eligible=False,
            reason=(
                "A file has too many changed lines: "
                f"{worst_per_file} > {config.max_per_file_changed_lines}"
            ),
            details=stats,
        )

    return FastLaneResult(
        is_fast_lane_eligible=True,
        reason="Within fast lane thresholds",
        details=stats,
    )


def format_human_readable(result: FastLaneResult) -> str:
    lines: List[str] = []
    status = "ELIGIBLE" if result.is_fast_lane_eligible else "NOT ELIGIBLE"
    lines.append(f"Fast lane status: {status}")
    lines.append(f"Reason: {result.reason}")
    if result.details:
        lines.append("")
        lines.append("Changed files (added, deleted, total):")
        for s in result.details:
            lines.append(f"  {s.path}: +{s.added} -{s.deleted} (total {s.total})")
    return "\n".join(lines)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fast lane regression check based on git diff size."
    )
    parser.add_argument(
        "--base",
        dest="base",
        default=None,
        help="Base branch/ref to compare against (default: config.base_branch).",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Output result as JSON for CI integration.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Override max allowed changed files.",
    )
    parser.add_argument(
        "--max-lines-total",
        type=int,
        default=None,
        help="Override max allowed total changed lines.",
    )
    parser.add_argument(
        "--max-lines-per-file",
        type=int,
        default=None,
        help="Override max allowed changed lines per file.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config = FastLaneConfig()
    if args.base:
        config.base_branch = args.base
    if args.max_files is not None:
        config.max_changed_files = args.max_files
    if args.max_lines_total is not None:
        config.max_total_changed_lines = args.max_lines_total
    if args.max_lines_per_file is not None:
        config.max_per_file_changed_lines = args.max_lines_per_file

    try:
        result = evaluate_fast_lane(config)
    except RuntimeError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1

    if args.as_json:
        payload = {
            "fast_lane_eligible": result.is_fast_lane_eligible,
            "reason": result.reason,
            "files": [
                {
                    "path": s.path,
                    "added": s.added,
                    "deleted": s.deleted,
                    "total": s.total,
                }
                for s in result.details
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(format_human_readable(result))
    return 0 if result.is_fast_lane_eligible else 2


if __name__ == "__main__":
    raise SystemExit(main())
