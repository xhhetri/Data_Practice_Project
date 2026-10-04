"""Bounded preview/import and portable recovery, without exposing server paths."""
import csv
import hashlib
import io
import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4, UUID

from .store import Repository, TABLES, STATUSES, encoded, fingerprint, normalise_purchase, text_value, decimal_value

CSV_LIMIT = 5 * 1024 * 1024
BACKUP_LIMIT = 25 * 1024 * 1024
ROW_LIMIT = 10000
FIELDS = ('vehicle_id', 'occurred_at', 'litres', 'amount', 'odometer_km', 'tank_status', 'incomplete', 'reference', 'vendor', 'note')


def csv_headers(content):
    if not isinstance(content, bytes) or not content or len(content) > CSV_LIMIT:
        raise ValueError('Upload a non-empty UTF-8 CSV up to 5 MiB.')
    try:
        reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')), strict=True)
        headers = reader.fieldnames
        if not headers or len(headers) > 50 or len(set(headers)) != len(headers) or any(not h.strip() or len(h) > 120 for h in headers):
            raise ValueError('CSV headers must be unique, non-empty names (at most 50 columns).')
        return headers
    except (UnicodeDecodeError, csv.Error) as error:
        raise ValueError('Use a valid UTF-8 CSV with a header row.') from error


def snapshot_key(vehicles, records):
    return fingerprint(dict(vehicles=sorted((v['id'], v['revision'], v['archived']) for v in vehicles),
                            purchases=sorted((r['id'], r['revision'], r['void']) for r in records)))


def _duplicate_key(r):
    return (r['vehicle_id'], r['occurred_at'], str(Decimal(r['litres']).normalize()), r['amount_cents'], r.get('odometer_km'))


def preview_csv(content, mapping, vehicles, existing, timezone_name='Australia/Sydney'):
    headers = csv_headers(content)
    if set(mapping) - set(FIELDS) or not {'vehicle_id', 'occurred_at', 'litres', 'amount'} <= set(mapping):
        raise ValueError('Map vehicle, date, litres and amount paid before previewing.')
    ids = {v['id'] for v in vehicles}
    names = {v['name'].casefold(): v['id'] for v in vehicles}
    for field, column in mapping.items():
        if column not in headers and not (field == 'vehicle_id' and column in ids):
            raise ValueError(f'Choose an existing column for {field}.')
    rows, errors, warnings = [], [], []
    seen = {_duplicate_key(r) for r in existing if not r['void']}
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')), strict=True)
    try:
        for number, raw in enumerate(reader, 2):
            if number > ROW_LIMIT + 1:
                raise ValueError('Import at most 10,000 data rows per file.')
            if None in raw or any(v is None for v in raw.values()):
                errors.append(dict(row=number, message='Column count differs from the header.'))
                continue
            payload = {field: raw[column].strip() if column in headers else column for field, column in mapping.items()}
            payload['vehicle_id'] = names.get(payload['vehicle_id'].casefold(), payload['vehicle_id'])
            status = payload.get('tank_status', 'unknown').casefold()
            payload['tank_status'] = {'true': 'full', 'yes': 'full', '1': 'full', 'false': 'partial', 'no': 'partial', '0': 'partial', '': 'unknown'}.get(status, status)
            if 'incomplete' in payload:
                flag = payload['incomplete'].casefold()
                if flag not in ('true', 'false', 'yes', 'no', '1', '0', ''):
                    errors.append(dict(row=number, message='Missing-purchases field must be true/false.'))
                    continue
                payload['incomplete'] = flag in ('true', 'yes', '1')
            try:
                normal = normalise_purchase(payload, vehicles, timezone_name)
            except ValueError as error:
                errors.append(dict(row=number, message=str(error)))
                continue
            key = _duplicate_key(normal)
            if key in seen:
                warnings.append(dict(row=number, message='Matching purchase details already occur in the file or workspace; review before importing.'))
            seen.add(key)
            rows.append(payload)
    except csv.Error as error:
        raise ValueError('Malformed CSV quoting or field size. Correct the file before importing.') from error
    if not rows and not errors:
        raise ValueError('The CSV contains no purchase rows.')
    identity = fingerprint(dict(file_sha256=hashlib.sha256(content).hexdigest(), mapping=mapping, timezone=timezone_name))
    return dict(batch_id=identity, rows=rows, rows_hash=fingerprint(rows), errors=errors, warnings=warnings,
                snapshot=snapshot_key(vehicles, existing), row_count=number - 1 if 'number' in locals() else 0)


def import_preview(repository, preview, acknowledge_duplicates=False):
    if preview['errors'] or not preview['rows'] or fingerprint(preview['rows']) != preview['rows_hash']:
        raise ValueError('Correct the file and regenerate its preview before importing.')
    known = {b['id'] for b in repository._list('imports')}
    if preview['batch_id'] in known:
        return repository.import_rows(preview['rows'], preview['batch_id'])
    if preview['snapshot'] != snapshot_key(repository.vehicles(), repository.purchases(True)):
        raise ValueError('The workspace changed after preview. Preview the file again.')
    if preview['warnings'] and not acknowledge_duplicates:
        raise ValueError('Confirm that you reviewed the matching purchases before importing.')
    return repository.import_rows(preview['rows'], preview['batch_id'], expected_snapshot=preview['snapshot'])


def safe_text(value):
    text = '' if value is None else str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')) else text


def export_csv(records, vehicles=()):
    names = {v['id']: v['name'] for v in vehicles}
    output = io.StringIO(newline='')
    columns = ('record_id', 'vehicle_id', 'vehicle_name', 'occurred_at', 'litres', 'amount_AUD', 'odometer_km', 'tank_status', 'missing_purchases', 'reference', 'vendor', 'note', 'void', 'revision')
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for r in records:
        value = dict(record_id=r['id'], vehicle_id=r['vehicle_id'], vehicle_name=names.get(r['vehicle_id'], ''),
                     occurred_at=r['occurred_at'] if r['has_time'] else r['occurred_at'][:10], litres=r['litres'],
                     amount_AUD=f"{Decimal(r['amount_cents'])/100:.2f}", odometer_km=r['odometer_km'],
                     tank_status=r['tank_status'], missing_purchases=bool(r['incomplete']), reference=r['reference'],
                     vendor=r['vendor'], note=r['note'], void=bool(r['void']), revision=r['revision'])
        writer.writerow({k: safe_text(v) for k, v in value.items()})
    return output.getvalue()


def backup(repository):
    with repository.connection() as c:
        data = dict(schema_version=1, timezone=repository.timezone.key,
                    tables={name: [dict(row) for row in c.execute(f'SELECT * FROM {name}')] for name in TABLES})
    data['checksum'] = fingerprint(data)
    return encoded(data).encode('utf-8')


def _integer(value, *, maximum=100000000000, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('Backup contains an invalid integer or flag.')


def _validate_backup(data, repo):
    if set(data) != {'schema_version', 'timezone', 'tables'} or type(data['schema_version']) is not int or data['schema_version'] != 1 or set(data['tables']) != set(TABLES):
        raise ValueError('Unsupported backup schema or record collections.')
    with repo.connection() as c:
        columns = {name: {r['name'] for r in c.execute(f'PRAGMA table_info({name})')} for name in TABLES}
    for table, rows in data['tables'].items():
        if not isinstance(rows, list) or len(rows) > 100000:
            raise ValueError('Backup collections exceed supported limits.')
        for row in rows:
            if not isinstance(row, dict) or set(row) != columns[table]:
                raise ValueError('Backup record fields do not match the schema.')
    vehicles = data['tables']['vehicles']
    for v in vehicles:
        UUID(v['id'])
        _integer(v['revision'], minimum=1)
        _integer(v['archived'], maximum=1)
        expected = repo._vehicle({k: v[k] for k in ('name', 'fuel_grade', 'tank_capacity_l')} | {'archived': bool(v['archived'])})
        if any(expected[k] != v[k] for k in expected):
            raise ValueError('Vehicle record is not normalized.')
    purchase_ids = set()
    for r in data['tables']['purchases']:
        UUID(r['id'])
        _integer(r['amount_cents'], minimum=1, maximum=100000000)
        for key in ('void', 'has_time', 'incomplete'):
            _integer(r[key], maximum=1)
        _integer(r['revision'], minimum=1)
        payload = {k: r[k] for k in ('vehicle_id', 'litres', 'odometer_km', 'tank_status', 'reference', 'vendor', 'note')}
        payload.update(occurred_at=r['occurred_at'] if r['has_time'] else r['occurred_at'][:10],
                       amount=str(Decimal(r['amount_cents']) / 100), incomplete=bool(r['incomplete']))
        expected = normalise_purchase(payload, vehicles, data['timezone'], correction=True)
        if any(expected[k] != r[k] for k in expected):
            raise ValueError('Purchase record is not normalized.')
        text_value(r['request_id'], 'Save request', 128, True)
        if len(r['request_hash']) != 64:
            raise ValueError('Invalid purchase identity.')
        purchase_ids.add(r['id'])
    review_ids = set()
    for r in data['tables']['reviews']:
        text_value(r['id'], 'Finding', 128, True)
        if r['status'] not in STATUSES:
            raise ValueError('Invalid review status.')
        text_value(r['note'], 'Review note', 2000)
        text_value(r['refund_reference'], 'Refund evidence')
        _integer(r['refund_cents'], maximum=100000000)
        if r['refund_cents'] and not r['refund_reference']:
            raise ValueError('Refund evidence is missing.')
        review_ids.add(r['id'])
    for batch in data['tables']['imports']:
        ids = json.loads(batch['purchase_ids'])
        if not isinstance(ids, list) or not all(i in purchase_ids for i in ids) or len(batch['payload_hash']) != 64:
            raise ValueError('Import batch contains invalid references.')
    targets = {'vehicle': {v['id'] for v in vehicles}, 'purchase': purchase_ids, 'review': review_ids}
    for event in data['tables']['events']:
        _integer(event['id'], minimum=1)
        if event['entity'] not in targets or event['record_id'] not in targets[event['entity']]:
            raise ValueError('History contains an unknown record reference.')
        if not isinstance(json.loads(event['after_json']), dict) or (event['before_json'] is not None and not isinstance(json.loads(event['before_json']), dict)):
            raise ValueError('History contains an invalid record version.')


def restore(content, directory):
    if not isinstance(content, bytes) or not content or len(content) > BACKUP_LIMIT:
        raise ValueError('Use a versioned JSON backup up to 25 MiB.')
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    temporary, destination = root / f'.restore-{token}.sqlite', root / f'workspace-{token}.sqlite'
    try:
        data = json.loads(content.decode('utf-8'))
        checksum = data.pop('checksum', None)
        if checksum != fingerprint(data):
            raise ValueError('Backup checksum is missing or does not match. Obtain a fresh backup.')
        repo = Repository(temporary, timezone=data.get('timezone', 'Australia/Sydney'))
        _validate_backup(data, repo)
        with repo.connection(True) as c:
            for table in TABLES:
                for row in data['tables'][table]:
                    repo._insert(c, table, row)
        temporary.replace(destination)
        return destination
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OSError) as error:
        raise ValueError(f'Backup could not be restored: {error}') from error
    except Exception as error:
        # Database constraints catch duplicate identities and invalid references atomically.
        raise ValueError('Backup could not be restored; existing records were retained.') from error
    finally:
        for suffix in ('', '-wal', '-shm'):
            scratch = root / (temporary.name + suffix)
            if scratch.parent == root and scratch.exists():
                scratch.unlink()
