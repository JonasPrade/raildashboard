"""Utility script to change a user's password.

Usage:
    python scripts/change_password.py --username admin
"""

from __future__ import annotations

import argparse
import getpass
import sys

from dashboard_backend.core.security import hash_password
from dashboard_backend.crud import users as users_crud
from dashboard_backend.database import Session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Change the password of an existing dashboard user")
    parser.add_argument("--username", required=True, help="Login name of the user")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password = getpass.getpass(prompt="New password: ")
    password_confirm = getpass.getpass(prompt="Repeat new password: ")
    if password != password_confirm:
        print("Passwords do not match", file=sys.stderr)
        return 1

    with Session() as db:
        user = users_crud.get_user_by_username(db, args.username)
        if user is None:
            print(f"User '{args.username}' not found", file=sys.stderr)
            return 1
        users_crud.update_password(db, user, hash_password(password))

    print(f"Password updated for user '{args.username}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
