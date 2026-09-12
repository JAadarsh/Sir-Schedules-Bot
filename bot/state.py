from dataclasses import dataclass, field
import datetime
import asyncio


@dataclass
class AppState:
    full_deletion_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    daily_messages_sent: set[tuple[int, str, datetime.date]] = field(default_factory=set)
    group_messages_sent: set[tuple[int, str, datetime.datetime]] = field(default_factory=set)
    pending_full_deletions: dict[int, tuple[str, float]] = field(default_factory=dict)
    database_health: dict[str, dict[str, str | bool | None]] = field(default_factory=lambda: {
        "db1": {"healthy": False, "error": "Not checked yet."},
        "db2": {"healthy": False, "error": "Not checked yet."},
        "db3": {"healthy": False, "error": "Not checked yet."},
    })
