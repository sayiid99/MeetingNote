from __future__ import annotations

import argparse
import sys
from pathlib import Path

from meeting_note.core.model_preparation import LocalModelPreparationService, format_model_availability


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check and prepare local models for MeetingNote.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show the local model status.")
    status_parser.add_argument("--project-root", default=None)

    prepare_parser = subparsers.add_parser("prepare", help="Download missing default models.")
    prepare_parser.add_argument("--project-root", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd().resolve()
    service = LocalModelPreparationService(project_root / "models")

    try:
        if args.command == "status":
            _print_summary(service.inspect())
            return 0

        if args.command == "prepare":
            summary = service.inspect()
            _print_summary(summary)
            missing = summary.missing_required()
            if not missing:
                print("All required model categories are already present.")
                return 0
            print("")
            for spec in missing:
                print(f"Downloading {spec.label} to {spec.target_path(service.models_dir)}")
                ready_path = service.download(spec)
                print(f"Ready: {ready_path}")
            print("")
            _print_summary(service.inspect())
            return 0
    except Exception as exc:  # pragma: no cover - CLI surface
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _print_summary(summary) -> None:
    print("Local model status")
    print("------------------")
    for line in format_model_availability(summary):
        print(line)


if __name__ == "__main__":
    raise SystemExit(main())
