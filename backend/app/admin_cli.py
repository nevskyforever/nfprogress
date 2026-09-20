"""Server-side emergency administration. It never starts an HTTP server."""
from __future__ import annotations

import argparse
import getpass

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .cloud.models import User
from .cloud.repositories import UserRepository, normalize_username
from .cloud.services import AccountService
from .config import RuntimeConfig


def _create(_args: argparse.Namespace) -> int:
    username = input('Username: ').strip()
    email = input('Email: ').strip()
    password = getpass.getpass('Password: ')
    confirmation = getpass.getpass('Confirm password: ')
    if password != confirmation:
        print('Passwords do not match.')
        return 2
    engine = create_engine(RuntimeConfig.from_env().require_database_url())
    try:
        with Session(engine) as session:
            AccountService().create_user(session, username=username, email=email, password=password,
                role='admin', status='active').email_verified = True
            session.commit()
        print(f'Created active administrator {username}.')
        return 0
    except ValueError as error:
        print(f'Cannot create administrator: {error}')
        return 2
    except IntegrityError:
        print('Cannot create administrator: username or email already exists.')
        return 2
    finally:
        engine.dispose()


def _find(session: Session, username: str) -> User | None:
    return UserRepository().get_by_normalized_username(session, normalize_username(username))


def _promote(args: argparse.Namespace) -> int:
    engine = create_engine(RuntimeConfig.from_env().require_database_url())
    try:
        with Session(engine) as session:
            user = _find(session, args.username)
            if user is None:
                print('User was not found.')
                return 2
            user.role = 'admin'
            session.commit()
        print(f'Administrator role confirmed for {args.username}.')
        return 0
    finally:
        engine.dispose()


def _restore(args: argparse.Namespace) -> int:
    engine = create_engine(RuntimeConfig.from_env().require_database_url())
    try:
        with Session(engine) as session:
            user = _find(session, args.username)
            if user is None:
                print('User was not found.')
                return 2
            if user.role != 'admin':
                print('Only administrator accounts can be restored.')
                return 2
            user.status = 'active'
            session.commit()
        print(f'Administrator account restored for {args.username}.')
        return 0
    finally:
        engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Server-side nfprogress administrator management.')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('create').set_defaults(handler=_create)
    for name, handler in (('promote', _promote), ('restore', _restore)):
        command = commands.add_parser(name)
        command.add_argument('username')
        command.set_defaults(handler=handler)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.handler(args)


if __name__ == '__main__':
    raise SystemExit(main())
