"""Single-workspace access protection; no shared-tenant or public identity claims."""
import getpass
from contextlib import closing
import hashlib
import hmac
import secrets
import sqlite3
import time
from pathlib import Path


def _parse(value):
    if not isinstance(value, str) or len(value) > 300:
        raise ValueError('Invalid password hash.')
    parts = value.split('$')
    if len(parts) != 7 or parts[:4] != ['scrypt', '16384', '8', '1'] or parts[4] != '64':
        raise ValueError('Unsupported password hash parameters.')
    try:
        salt, digest = bytes.fromhex(parts[5]), bytes.fromhex(parts[6])
    except ValueError as error:
        raise ValueError('Invalid password hash encoding.') from error
    if len(salt) != 16 or len(digest) != 64:
        raise ValueError('Invalid password hash size.')
    return salt, digest


def hash_password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 256:
        raise ValueError('Use a password of 12–256 characters.')
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=64)
    return f'scrypt$16384$8$1$64${salt.hex()}${digest.hex()}'


def verify_password(password, stored):
    try:
        salt, expected = _parse(stored)
        if not isinstance(password, str) or len(password) > 256:
            return False
        actual = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=64)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def validate_config(mode, stored):
    if mode not in ('local', 'production'):
        raise ValueError('FLEET_MODE must be local or production.')
    if stored:
        _parse(stored)
        return True
    if mode == 'production':
        raise ValueError('Production requires a valid FLEET_PASSWORD_HASH before records can be accessed.')
    return False


class AuthGate:
    def __init__(self, path, stored):
        _parse(stored)
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stored = stored
        self.identity = hashlib.sha256(stored.encode()).hexdigest()
        with closing(sqlite3.connect(self.path)) as c, c:
            c.execute('CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, failures INTEGER NOT NULL, window REAL NOT NULL, blocked_until REAL NOT NULL)')
            c.execute('INSERT OR IGNORE INTO attempts VALUES (1,0,0,0)')

    def attempt(self, password, now=None):
        now = time.time() if now is None else now
        with closing(sqlite3.connect(self.path, timeout=10)) as c, c:
            c.execute('BEGIN IMMEDIATE')
            failures, window, blocked = c.execute('SELECT failures,window,blocked_until FROM attempts WHERE id=1').fetchone()
            if now < blocked:
                return dict(ok=False, retry_after=max(1, int(blocked - now)))
            if now - window > 60 or now < window:
                failures, window = 0, now
            if verify_password(password, self.stored):
                c.execute('UPDATE attempts SET failures=0,window=?,blocked_until=0 WHERE id=1', (now,))
                return dict(ok=True, retry_after=0)
            failures += 1
            blocked = now + 300 if failures >= 5 else 0
            c.execute('UPDATE attempts SET failures=?,window=?,blocked_until=? WHERE id=1', (failures, window, blocked))
            return dict(ok=False, retry_after=300 if blocked else 0)

    def new_session(self, now=None):
        now = time.time() if now is None else now
        return dict(created=now, last_seen=now, identity=self.identity)

    def session_valid(self, session, now=None):
        now = time.time() if now is None else now
        try:
            valid = (hmac.compare_digest(session['identity'], self.identity)
                     and 0 <= now - session['last_seen'] <= 1800
                     and 0 <= now - session['created'] <= 28800)
            if valid:
                session['last_seen'] = now
            return valid
        except (KeyError, TypeError):
            return False


if __name__ == '__main__':
    first = getpass.getpass('New workspace password (at least 12 characters): ')
    second = getpass.getpass('Repeat password: ')
    if first != second:
        raise SystemExit('Passwords did not match.')
    print(hash_password(first))
