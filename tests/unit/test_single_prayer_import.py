#!/usr/bin/env python3
"""Unit tests for single prayer import deduplication helpers."""

from datetime import datetime

from sqlmodel import select

from app_helpers.services.import_service import ImportService
from models import Prayer, PrayerAttribute, PrayerActivityLog, PrayerMark, User


def _build_prayer(test_session, prayer_id: str, author: str, text_file_path: str) -> Prayer:
    user = User(display_name=author)
    prayer = Prayer(
        id=prayer_id,
        author_username=author,
        text="original",
        generated_prayer="generated",
        created_at=datetime(2024, 6, 1, 12, 0, 0),
        text_file_path=text_file_path,
    )
    test_session.add(user)
    test_session.add(prayer)
    test_session.commit()
    return prayer


def test_update_existing_prayer_does_not_duplicate_minute_level_activities(test_session):
    service = ImportService()
    prayer = _build_prayer(test_session, "prayer-duplicate", "Alice", "text_archives/prayer.txt")

    existing_mark = PrayerMark(
        prayer_id=prayer.id,
        username="Alice",
        created_at=datetime(2024, 6, 1, 12, 34, 56),
        text_file_path="old_path.txt",
    )
    existing_attr = PrayerAttribute(
        prayer_id=prayer.id,
        attribute_name="answered",
        attribute_value="true",
        created_by="Alice",
        created_at=datetime(2024, 6, 1, 12, 34, 58),
        text_file_path="old_path.txt",
    )
    existing_prayed_log = PrayerActivityLog(
        prayer_id=prayer.id,
        user_id="Alice",
        action="prayed",
        old_value=None,
        new_value="true",
        created_at=datetime(2024, 6, 1, 12, 34, 57),
        text_file_path="old_path.txt",
    )
    existing_answered_log = PrayerActivityLog(
        prayer_id=prayer.id,
        user_id="Alice",
        action="answered",
        old_value=None,
        new_value="true",
        created_at=datetime(2024, 6, 1, 12, 34, 20),
        text_file_path="old_path.txt",
    )
    test_session.add_all([existing_mark, existing_attr, existing_prayed_log, existing_answered_log])
    test_session.commit()

    activities = [
        {"action": "prayed", "user": "Alice", "timestamp": "June 01 2024 at 12:34"},
        {"action": "answered", "user": "Alice", "timestamp": "June 01 2024 at 12:34"},
    ]

    service._import_single_prayer_activities(test_session, prayer, activities)

    marks = test_session.exec(select(PrayerMark).where(PrayerMark.prayer_id == prayer.id)).all()
    attrs = test_session.exec(select(PrayerAttribute).where(PrayerAttribute.prayer_id == prayer.id)).all()
    logs = test_session.exec(select(PrayerActivityLog).where(PrayerActivityLog.prayer_id == prayer.id)).all()

    assert len(marks) == 1, "Duplicate prayer mark was created"
    assert len(attrs) == 1, "Duplicate prayer attribute was created"
    assert len(logs) == 2, "Duplicate prayer activity log was created"
    assert marks[0].text_file_path == prayer.text_file_path
    assert attrs[0].text_file_path == prayer.text_file_path
    assert all(log.text_file_path == prayer.text_file_path for log in logs)


def test_update_existing_prayer_inserts_new_minute_activity(test_session):
    service = ImportService()
    prayer = _build_prayer(test_session, "prayer-new", "Bob", "text_archives/new_prayer.txt")

    existing_mark = PrayerMark(
        prayer_id=prayer.id,
        username="Bob",
        created_at=datetime(2024, 6, 1, 12, 34, 56),
        text_file_path="legacy_path.txt",
    )
    test_session.add(existing_mark)
    test_session.commit()

    activities = [
        {"action": "prayed", "user": "Bob", "timestamp": "June 01 2024 at 12:35"},
    ]

    service._import_single_prayer_activities(test_session, prayer, activities)

    marks = test_session.exec(select(PrayerMark).where(PrayerMark.prayer_id == prayer.id)).all()
    assert len(marks) == 2
    minute_values = sorted(mark.created_at.minute for mark in marks)
    assert minute_values == [34, 35]
    latest = max(marks, key=lambda mark: mark.created_at)
    assert latest.text_file_path == prayer.text_file_path


def test_parse_single_timestamp_accepts_seconds_component():
    service = ImportService()
    parsed = service._parse_single_timestamp("June 01 2024 at 12:34:56")
    assert parsed == datetime(2024, 6, 1, 12, 34, 56)
