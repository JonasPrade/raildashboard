"""Utility script to bootstrap the first administrator account.

Usage:
    python scripts/create_initial_user.py --username admin --role admin
"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy.exc import IntegrityError

from dashboard_backend.core.security import hash_password
from dashboard_backend.crud import users as users_crud
from dashboard_backend.database import Session
from dashboard_backend.schemas.users import UserCreate, UserRole


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an initial dashboard user")
    parser.add_argument("--username", required=True, help="Login name of the new user")
    parser.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        default=UserRole.admin.value,
        help="Role assigned to the new user (defaults to admin)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password = getpass.getpass(prompt="Password: ")
    password_confirm = getpass.getpass(prompt="Repeat password: ")
    if password != password_confirm:
        print("Passwords do not match", file=sys.stderr)
        return 1

    with Session() as db:
        if users_crud.get_user_by_username(db, args.username):
            print("A user with this username already exists", file=sys.stderr)
            return 1
        try:
            user = users_crud.create_user(
                db,
                user_in=UserCreate(username=args.username, password=password, role=UserRole(args.role)),
                password_hasher=hash_password,
            )
        except IntegrityError as exc:  # pragma: no cover - safety net
            db.rollback()
            print(f"Failed to create user: {exc}", file=sys.stderr)
            return 1

    print(f"Created user '{user.username}' with role '{user.role}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

