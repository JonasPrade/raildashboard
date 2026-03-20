"""Delete a user account by username.

Usage:
    python scripts/delete_user.py --username <name>
"""

from __future__ import annotations

import argparse
import sys

from dashboard_backend.crud import users as users_crud
from dashboard_backend.database import Session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete a dashboard user")
    parser.add_argument("--username", required=True, help="Login name of the user to delete")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    with Session() as db:
        user = users_crud.get_user_by_username(db, args.username)
        if not user:
            print(f"User '{args.username}' not found", file=sys.stderr)
            return 1

        confirm = input(f"Delete user '{args.username}' (role: {user.role})? [y/N] ")
        if confirm.lower() != "y":
            print("Aborted.")
            return 0

        db.delete(user)
        db.commit()

    print(f"Deleted user '{args.username}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
