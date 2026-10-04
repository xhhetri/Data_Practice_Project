"""Validated, transactional single-workspace storage. No personal data is logged."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

GRADES = ('Unleaded 91', 'Unleaded 95', 'Unleaded 98', 'Diesel', 'LPG', 'Other')
STATUSES = ('open', 'explained', 'record corrected', 'follow-up needed')
TABLES = ('vehicles', 'purchases', 'events', 'imports', 'reviews')


def decimal_value(value, label, *, places=3, positive=True, maximum='100000000'):
    try:
        if isinstance(value, bool):
            raise ValueError
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or (positive and result == 0) or result > Decimal(maximum):
            raise ValueError
        if result != result.quantize(Decimal(1).scaleb(-places)):
            raise ValueError
        return result
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ValueError(f'{label} must be a finite {"positive" if positive else "non-negative"} number with at most {places} decimal places.') from error


def text_value(value, label, maximum=120, required=False):
    if not isinstance(value, str):
        raise ValueError(f'{label} must be text.')
    value = value.strip()
    if len(value) > maximum or '\x00' in value or (required and not value):
        raise ValueError(f'{label} must contain {"1–" if required else "at most "}{maximum} characters, without null characters.')
    return value


def boolean(value, label):
    if type(value) is not bool:
        raise ValueError(f'{label} must be true or false.')
    return value


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def normalise_purchase(payload, vehicles, timezone_name='Australia/Sydney', correction=False):
    zone = ZoneInfo(timezone_name)
    allowed = {'vehicle_id', 'occurred_at', 'litres', 'amount', 'odometer_km', 'tank_status', 'incomplete', 'reference', 'vendor', 'note'}
    if set(payload) - allowed:
        raise ValueError('Unexpected purchase fields.')
    vehicle_id = text_value(payload.get('vehicle_id', ''), 'Vehicle', 64, True)
    v = next((v for v in vehicles if v['id'] == vehicle_id), None)
    if v is None or (v['archived'] and not correction):
        raise ValueError('Select an active vehicle.')
    raw_date = text_value(payload.get('occurred_at', ''), 'Transaction date', 40, True)
    try:
        date = datetime.fromisoformat(raw_date)
        if date.tzinfo is not None:
            date = date.astimezone(zone).replace(tzinfo=None)
        if date.date() > datetime.now(zone).date():
            raise ValueError
        if date.year < 1900:
            raise ValueError
    except ValueError as error:
        raise ValueError('Use a valid transaction date that is not in the future.') from error
    status = payload.get('tank_status', 'unknown')
    if status not in ('full', 'partial', 'unknown'):
        raise ValueError('Tank status must be full, partial or unknown.')
    odo = payload.get('odometer_km')
    return dict(vehicle_id=vehicle_id, occurred_at=date.isoformat(timespec='seconds'), has_time=int('T' in raw_date or ' ' in raw_date),
                litres=str(decimal_value(payload.get('litres'), 'Litres', maximum='10000')),
                amount_cents=int(decimal_value(payload.get('amount'), 'Amount paid', places=2, maximum='1000000') * 100),
                odometer_km=str(decimal_value(odo, 'Odometer', places=1, positive=False, maximum='10000000')) if odo not in (None, '') else None,
                tank_status=status, incomplete=int(boolean(payload.get('incomplete', False), 'Missing purchases')),
                reference=text_value(payload.get('reference', ''), 'Receipt reference'),
                vendor=text_value(payload.get('vendor', ''), 'Vendor'), note=text_value(payload.get('note', ''), 'Note', 2000))


class Repository:
    def __init__(self, path, timezone='Australia/Sydney'):
        self.path = Path(path)
        self.timezone = ZoneInfo(timezone)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection(write=True) as c:
            version = c.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('Unsupported workspace schema version. Use a compatible release or restore a backup.')
            statements = [
                '''CREATE TABLE IF NOT EXISTS vehicles (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    fuel_grade TEXT NOT NULL, tank_capacity_l TEXT,
                    archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),
                    revision INTEGER NOT NULL CHECK(revision>0))''',
                '''CREATE TABLE IF NOT EXISTS purchases (
                    id TEXT PRIMARY KEY, vehicle_id TEXT NOT NULL REFERENCES vehicles(id),
                    occurred_at TEXT NOT NULL, has_time INTEGER NOT NULL CHECK(has_time IN (0,1)),
                    litres TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
                    odometer_km TEXT, tank_status TEXT NOT NULL CHECK(tank_status IN ('full','partial','unknown')),
                    incomplete INTEGER NOT NULL CHECK(incomplete IN (0,1)),
                    reference TEXT NOT NULL, vendor TEXT NOT NULL, note TEXT NOT NULL,
                    void INTEGER NOT NULL DEFAULT 0 CHECK(void IN (0,1)), revision INTEGER NOT NULL CHECK(revision>0),
                    request_id TEXT NOT NULL UNIQUE, request_hash TEXT NOT NULL)''',
                '''CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, entity TEXT NOT NULL, record_id TEXT NOT NULL,
                    action TEXT NOT NULL, before_json TEXT, after_json TEXT NOT NULL, at_utc TEXT NOT NULL)''',
                '''CREATE TABLE IF NOT EXISTS imports (
                    id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL, purchase_ids TEXT NOT NULL, at_utc TEXT NOT NULL)''',
                '''CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY, status TEXT NOT NULL, note TEXT NOT NULL,
                    refund_cents INTEGER NOT NULL CHECK(refund_cents>=0), refund_reference TEXT NOT NULL,
                    updated_at TEXT NOT NULL)''',
                'CREATE INDEX IF NOT EXISTS purchase_vehicle_date ON purchases(vehicle_id,occurred_at)',
            ]
            for statement in statements:
                c.execute(statement)
            c.execute('PRAGMA user_version=1')

    @contextmanager
    def connection(self, write=False):
        c = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        c.row_factory = sqlite3.Row
        try:
            c.execute('PRAGMA foreign_keys=ON')
            c.execute('PRAGMA busy_timeout=10000')
            c.execute('PRAGMA journal_mode=WAL')
            c.execute('PRAGMA synchronous=FULL')
            c.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def _event(self, c, entity, record_id, action, before, after):
        c.execute('INSERT INTO events(entity,record_id,action,before_json,after_json,at_utc) VALUES (?,?,?,?,?,?)',
                  (entity, record_id, action, encoded(before) if before else None, encoded(after), datetime.now(timezone.utc).isoformat()))

    def _list(self, table):
        if table not in TABLES:
            raise ValueError('Unknown record collection.')
        with self.connection() as c:
            return [dict(r) for r in c.execute(f'SELECT * FROM {table}')]

    def vehicles(self):
        return self._list('vehicles')

    def purchases(self, include_void=False):
        return sorted([r for r in self._list('purchases') if include_void or not r['void']], key=lambda r: (r['occurred_at'], r['id']))

    def history(self):
        return self._list('events')

    def reviews(self):
        return self._list('reviews')

    def _vehicle(self, payload):
        if set(payload) - {'name', 'fuel_grade', 'tank_capacity_l', 'archived'}:
            raise ValueError('Unexpected vehicle fields.')
        name = text_value(payload.get('name', ''), 'Vehicle name', 64, True)
        grade = payload.get('fuel_grade')
        if grade not in GRADES:
            raise ValueError('Select a supported fuel grade.')
        tank = payload.get('tank_capacity_l')
        return dict(name=name, fuel_grade=grade,
                    tank_capacity_l=str(decimal_value(tank, 'Tank capacity', maximum='10000')) if tank not in (None, '') else None,
                    archived=int(boolean(payload.get('archived', False), 'Archived')))

    def create_vehicle(self, payload):
        value = dict(id=str(uuid4()), **self._vehicle(payload), revision=1)
        with self.connection(True) as c:
            try:
                self._insert(c, 'vehicles', value)
            except sqlite3.IntegrityError as error:
                raise ValueError('A vehicle with this name already exists.') from error
            self._event(c, 'vehicle', value['id'], 'create', None, value)
        return value

    @staticmethod
    def _insert(c, table, value):
        if table not in TABLES:
            raise ValueError('Unknown record collection.')
        c.execute(f'INSERT INTO {table} ({",".join(value)}) VALUES ({",".join("?" for _ in value)})', tuple(value.values()))

    @staticmethod
    def _current(c, table, record_id, revision):
        row = c.execute(f'SELECT * FROM {table} WHERE id=?', (record_id,)).fetchone()
        if row is None:
            raise ValueError('This record no longer exists.')
        if type(revision) is not int or row['revision'] != revision:
            raise ValueError('This record changed in another session. Reload it before saving.')
        return dict(row)

    def update_vehicle(self, record_id, payload, expected_revision):
        with self.connection(True) as c:
            before = self._current(c, 'vehicles', record_id, expected_revision)
            fields = {k: before[k] for k in ('name', 'fuel_grade', 'tank_capacity_l')}
            fields['archived'] = bool(before['archived'])
            fields.update(payload)
            after = dict(id=record_id, **self._vehicle(fields), revision=before['revision'] + 1)
            try:
                self._replace(c, 'vehicles', after)
            except sqlite3.IntegrityError as error:
                raise ValueError('A vehicle with this name already exists.') from error
            self._event(c, 'vehicle', record_id, 'update', before, after)
            return after

    @staticmethod
    def _replace(c, table, value):
        keys = [k for k in value if k != 'id']
        c.execute(f'UPDATE {table} SET {",".join(k+"=?" for k in keys)} WHERE id=?', tuple(value[k] for k in keys) + (value['id'],))

    def _purchase(self, c, payload, *, correction=False):
        vehicles = [dict(v) for v in c.execute('SELECT * FROM vehicles')]
        return normalise_purchase(payload, vehicles, self.timezone.key, correction)

    def _save(self, c, payload, request_id):
        request_id = text_value(request_id, 'Save request', 128, True)
        value = self._purchase(c, payload)
        identity = fingerprint(value)
        existing = c.execute('SELECT * FROM purchases WHERE request_id=?', (request_id,)).fetchone()
        if existing:
            if existing['request_hash'] != identity:
                raise ValueError('This save request was already used for different data.')
            return dict(existing)
        value.update(id=str(uuid4()), void=0, revision=1, request_id=request_id, request_hash=identity)
        self._insert(c, 'purchases', value)
        self._event(c, 'purchase', value['id'], 'create', None, value)
        return value

    def save_purchase(self, payload, request_id):
        with self.connection(True) as c:
            return self._save(c, payload, request_id)

    def update_purchase(self, record_id, payload, expected_revision):
        with self.connection(True) as c:
            before = self._current(c, 'purchases', record_id, expected_revision)
            fields = {k: before[k] for k in ('vehicle_id', 'litres', 'odometer_km', 'tank_status', 'reference', 'vendor', 'note')}
            fields.update(occurred_at=before['occurred_at'] if before['has_time'] else before['occurred_at'][:10],
                          amount=str(Decimal(before['amount_cents']) / 100), incomplete=bool(before['incomplete']))
            fields.update(payload)
            after = {**before, **self._purchase(c, fields, correction=True), 'revision': before['revision'] + 1}
            self._replace(c, 'purchases', after)
            self._event(c, 'purchase', record_id, 'update', before, after)
            return after

    def void_purchase(self, record_id, expected_revision, void=True):
        void = boolean(void, 'Void')
        with self.connection(True) as c:
            before = self._current(c, 'purchases', record_id, expected_revision)
            after = {**before, 'void': int(void), 'revision': before['revision'] + 1}
            self._replace(c, 'purchases', after)
            self._event(c, 'purchase', record_id, 'void' if void else 'restore', before, after)
            return after

    def import_rows(self, rows, batch_id, expected_snapshot=None):
        batch_id = text_value(batch_id, 'Import batch', 128, True)
        identity = fingerprint(rows)
        with self.connection(True) as c:
            old = c.execute('SELECT * FROM imports WHERE id=?', (batch_id,)).fetchone()
            if old:
                if old['payload_hash'] != identity:
                    raise ValueError('This import batch was already used for different data.')
                ids = json.loads(old['purchase_ids'])
                return [dict(c.execute('SELECT * FROM purchases WHERE id=?', (i,)).fetchone()) for i in ids]
            if expected_snapshot is not None:
                current = fingerprint(dict(
                    vehicles=sorted(tuple(r) for r in c.execute('SELECT id,revision,archived FROM vehicles')),
                    purchases=sorted(tuple(r) for r in c.execute('SELECT id,revision,void FROM purchases'))))
                if current != expected_snapshot:
                    raise ValueError('The workspace changed after preview. Preview the file again.')
            saved = [self._save(c, row, f'import:{batch_id}:{index}') for index, row in enumerate(rows)]
            self._insert(c, 'imports', dict(id=batch_id, payload_hash=identity,
                purchase_ids=encoded([r['id'] for r in saved]), at_utc=datetime.now(timezone.utc).isoformat()))
            return saved

    def save_review(self, payload):
        allowed = {'id', 'status', 'note', 'refund_amount', 'refund_reference'}
        if set(payload) - allowed or payload.get('status') not in STATUSES:
            raise ValueError('Select a valid review outcome.')
        refund = int(decimal_value(payload.get('refund_amount', '0'), 'Confirmed refund', places=2, positive=False, maximum='1000000') * 100)
        reference = text_value(payload.get('refund_reference', ''), 'Refund evidence')
        if refund and not reference:
            raise ValueError('A confirmed refund requires an evidence reference.')
        result = dict(id=text_value(payload.get('id', ''), 'Finding', 128, True), status=payload['status'],
                      note=text_value(payload.get('note', ''), 'Review note', 2000), refund_cents=refund,
                      refund_reference=reference, updated_at=datetime.now(timezone.utc).isoformat())
        with self.connection(True) as c:
            old = c.execute('SELECT * FROM reviews WHERE id=?', (result['id'],)).fetchone()
            if old:
                self._replace(c, 'reviews', result)
            else:
                self._insert(c, 'reviews', result)
            self._event(c, 'review', result['id'], 'update' if old else 'create', dict(old) if old else None, result)
        return result
