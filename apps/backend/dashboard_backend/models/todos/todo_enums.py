"""Enums for the to-do (Aufgaben) feature.

Used for column defaults and validation. The API schemas use ``Literal[...]``
mirrors of these values for clean TypeScript codegen (see ``schemas/todos``).
"""

from __future__ import annotations

from enum import Enum


class TodoStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class TodoPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
