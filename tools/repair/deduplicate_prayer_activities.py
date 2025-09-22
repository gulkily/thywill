#!/usr/bin/env python3
"""Cleanup utility to remove duplicate prayer activity rows.

The `--update-existing` single-prayer import path used minute-level timestamps,
which could recreate already-recorded marks/attributes/logs with seconds reset
to `:00`. This script removes those duplicates and restores the original rows as
the source of truth.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

# Ensure project root is on sys.path when invoked via CLI wrapper
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from sqlmodel import Session, select

from models import engine, PrayerAttribute, PrayerActivityLog, PrayerMark


@dataclass
class DeduplicationResult:
    table: str
    examined: int = 0
    groups_considered: int = 0
    rows_deleted: int = 0
    rows_updated: int = 0
    details: List[Dict[str, str]] | None = None


def truncate_to_minute(value: datetime) -> datetime:
    """Normalize a timestamp to the start of its minute."""
    return value.replace(second=0, microsecond=0)


def should_dedupe(records: Sequence) -> bool:
    """Return True when the group matches the archive-induced duplicate pattern."""
    if len(records) < 2:
        return False
    has_zero_seconds = any(r.created_at.second == 0 and r.created_at.microsecond == 0 for r in records)
    has_non_zero = any(r.created_at.second != 0 or r.created_at.microsecond != 0 for r in records)
    return has_zero_seconds and has_non_zero


def choose_primary(records: Sequence) -> Tuple[object, List[object]]:
    """Pick the record to keep and list the duplicates to delete."""
    sorted_records = sorted(records, key=lambda r: (r.created_at, r.id))
    primary = next((r for r in sorted_records if r.created_at.second != 0 or r.created_at.microsecond != 0), sorted_records[0])
    duplicates = [r for r in sorted_records if r is not primary]
    return primary, duplicates


def gather_best_path(records: Iterable) -> str | None:
    """Return the first non-empty text_file_path from the group."""
    for record in records:
        if record.text_file_path:
            return record.text_file_path
    return None


def dedupe_prayer_marks(session: Session, dry_run: bool, show_details: bool) -> DeduplicationResult:
    result = DeduplicationResult(table="PrayerMark", details=[] if show_details else None)
    marks = list(session.exec(select(PrayerMark)))
    result.examined = len(marks)
    groups: Dict[Tuple[str, str, datetime], List[PrayerMark]] = defaultdict(list)
    for mark in marks:
        groups[(mark.prayer_id, mark.username, truncate_to_minute(mark.created_at))].append(mark)
    for (prayer_id, username, minute), records in groups.items():
        if not should_dedupe(records):
            continue
        result.groups_considered += 1
        primary, duplicates = choose_primary(records)
        best_path = gather_best_path(records)
        if best_path and not dry_run and primary.text_file_path != best_path:
            primary.text_file_path = best_path
            session.add(primary)
            result.rows_updated += 1
        if show_details:
            result.details.append({
                "prayer_id": str(prayer_id),
                "username": username,
                "minute": minute.isoformat(),
                "kept": primary.id,
                "deleted": ",".join(record.id for record in duplicates)
            })
        for duplicate in duplicates:
            if dry_run:
                result.rows_deleted += 1
            else:
                session.delete(duplicate)
                result.rows_deleted += 1
    return result


def dedupe_prayer_attributes(session: Session, dry_run: bool, show_details: bool) -> DeduplicationResult:
    result = DeduplicationResult(table="PrayerAttribute", details=[] if show_details else None)
    attrs = list(session.exec(select(PrayerAttribute)))
    result.examined = len(attrs)
    groups: Dict[Tuple[str, str, str, datetime], List[PrayerAttribute]] = defaultdict(list)
    for attr in attrs:
        groups[(attr.prayer_id, attr.attribute_name, attr.created_by or "", truncate_to_minute(attr.created_at))].append(attr)
    for (prayer_id, attr_name, created_by, minute), records in groups.items():
        if not should_dedupe(records):
            continue
        result.groups_considered += 1
        primary, duplicates = choose_primary(records)
        best_path = gather_best_path(records)
        if best_path and not dry_run and primary.text_file_path != best_path:
            primary.text_file_path = best_path
            session.add(primary)
            result.rows_updated += 1
        if show_details:
            result.details.append({
                "prayer_id": str(prayer_id),
                "attribute": attr_name,
                "created_by": created_by or "",
                "minute": minute.isoformat(),
                "kept": primary.id,
                "deleted": ",".join(record.id for record in duplicates)
            })
        for duplicate in duplicates:
            if dry_run:
                result.rows_deleted += 1
            else:
                session.delete(duplicate)
                result.rows_deleted += 1
    return result


def dedupe_prayer_activity_logs(session: Session, dry_run: bool, show_details: bool) -> DeduplicationResult:
    result = DeduplicationResult(table="PrayerActivityLog", details=[] if show_details else None)
    logs = list(session.exec(select(PrayerActivityLog)))
    result.examined = len(logs)
    groups: Dict[Tuple[str, str, str, str | None, str | None, datetime], List[PrayerActivityLog]] = defaultdict(list)
    for log in logs:
        key = (
            log.prayer_id,
            log.user_id,
            log.action,
            log.old_value,
            log.new_value,
            truncate_to_minute(log.created_at),
        )
        groups[key].append(log)
    for (prayer_id, user_id, action, old_value, new_value, minute), records in groups.items():
        if not should_dedupe(records):
            continue
        result.groups_considered += 1
        primary, duplicates = choose_primary(records)
        best_path = gather_best_path(records)
        if best_path and not dry_run and primary.text_file_path != best_path:
            primary.text_file_path = best_path
            session.add(primary)
            result.rows_updated += 1
        if show_details:
            result.details.append({
                "prayer_id": str(prayer_id),
                "user_id": user_id,
                "action": action,
                "minute": minute.isoformat(),
                "kept": primary.id,
                "deleted": ",".join(record.id for record in duplicates)
            })
        for duplicate in duplicates:
            if dry_run:
                result.rows_deleted += 1
            else:
                session.delete(duplicate)
                result.rows_deleted += 1
    return result


def print_summary(results: Sequence[DeduplicationResult], dry_run: bool) -> None:
    mode = "DRY RUN" if dry_run else "EXECUTION"
    print(f"\n=== Prayer Activity Deduplication ({mode}) ===")
    for item in results:
        print(
            f"{item.table}: examined={item.examined}, groups_considered={item.groups_considered}, "
            f"rows_deleted={item.rows_deleted}, rows_updated={item.rows_updated}"
        )
        if item.details:
            preview = item.details[:5]
            print(f"  Sample groups ({len(preview)} shown):")
            for detail in preview:
                print(f"    - {detail}")
            if len(item.details) > len(preview):
                print(f"    ... {len(item.details) - len(preview)} more groups")


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove duplicate prayer activity rows created by minute-level imports.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without modifying data")
    parser.add_argument("--show-details", action="store_true", help="Print sample duplicate groups that were processed")
    args = parser.parse_args()

    with Session(engine) as session:
        results = [
            dedupe_prayer_marks(session, args.dry_run, args.show_details),
            dedupe_prayer_attributes(session, args.dry_run, args.show_details),
            dedupe_prayer_activity_logs(session, args.dry_run, args.show_details),
        ]
        if not args.dry_run:
            session.commit()
    print_summary(results, args.dry_run)


if __name__ == "__main__":
    main()
