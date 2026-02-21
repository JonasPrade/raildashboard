"""Utility script to list all dashboard users.

Usage:
    python scripts/list_users.py
"""

from __future__ import annotations

from dashboard_backend.crud import users as users_crud
from dashboard_backend.database import Session


def main() -> int:
    with Session() as db:
        users = users_crud.get_users(db)

    if not users:
        print("No users found.")
        return 0

    col_w = max(len(u.username) for u in users)
    print(f"{'Username':<{col_w}}  Role")
    print(f"{'-' * col_w}  ----")
    for user in users:
        print(f"{user.username:<{col_w}}  {user.role}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
