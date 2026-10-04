"""Evidence-linked analysis of recorded purchases; no causal or savings claims."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import median
from .store import decimal_value, fingerprint

D = Decimal


def active(records):
    return sorted((r for r in records if not r.get('void')), key=lambda r: (r['occurred_at'], r['id']))


def efficiency_intervals(records):
    groups = defaultdict(list)
    for r in active(records):
        groups[r['vehicle_id']].append(r)
    intervals, warnings = [], []
    for vehicle_id, rows in groups.items():
        counts = Counter(r['occurred_at'][:10] for r in rows)
        ambiguous = {r['occurred_at'][:10] for r in rows if not r['has_time'] and counts[r['occurred_at'][:10]] > 1}
        times = Counter(r['occurred_at'] for r in rows)
        opening, between = None, []
        for r in rows:
            if opening:
                between.append(r)
            if r['tank_status'] != 'full':
                continue
            odo = r['odometer_km']
            bad_boundary = r['occurred_at'][:10] in ambiguous or times[r['occurred_at']] > 1
            if opening:
                sources = [opening, *between]
                reasons = []
                if odo is None:
                    reasons.append('Closing odometer missing')
                if any(s['occurred_at'][:10] in ambiguous or times[s['occurred_at']] > 1 for s in sources):
                    reasons.append('Transaction order is ambiguous')
                if any(s.get('incomplete') for s in between):
                    reasons.append('Purchases declared missing')
                known = [D(s['odometer_km']) for s in sources if s['odometer_km'] is not None]
                if any(b < a for a, b in zip(known, known[1:])) or (odo is not None and D(odo) <= D(opening['odometer_km'])):
                    reasons.append('Odometers do not establish a positive consistent distance')
                if reasons:
                    warnings.append(dict(vehicle_id=vehicle_id, start=opening['occurred_at'], end=r['occurred_at'],
                                         source_ids=[s['id'] for s in sources], reason='; '.join(reasons)))
                else:
                    litres = sum((D(s['litres']) for s in between), D(0))
                    distance = D(odo) - D(opening['odometer_km'])
                    intervals.append(dict(vehicle_id=vehicle_id, start=opening['occurred_at'], end=r['occurred_at'],
                        litres=str(litres), distance_km=str(distance), rate_l_per_100km=str(litres / distance * 100),
                        source_ids=[s['id'] for s in sources]))
            elif odo is None or bad_boundary:
                warnings.append(dict(vehicle_id=vehicle_id, start=r['occurred_at'], end=r['occurred_at'],
                                     source_ids=[r['id']], reason='A full tank with an unambiguous odometer is needed to establish a boundary'))
            # A missing odometer may be an intermediate purchase in a longer supported interval.
            if odo is not None:
                opening = None if bad_boundary else r
                between = []
    return dict(intervals=intervals, warnings=warnings)


def exceptions(records, vehicles):
    rows = active(records)
    vehicle_map = {v['id']: v for v in vehicles}
    lookup = {r['id']: r for r in rows}
    findings = []

    def add(rule, sources, message, **details):
        ids = sorted({s['id'] for s in sources})
        vehicle_id = sources[-1]['vehicle_id']
        evidence = [(i, lookup[i]['revision']) for i in ids]
        identity = fingerprint(dict(rule=rule, evidence=evidence, vehicle_revision=vehicle_map.get(vehicle_id, {}).get('revision', 1)))
        findings.append(dict(id=identity, rule=rule, vehicle_id=vehicle_id, source_ids=ids,
                             date=max(s['occurred_at'][:10] for s in sources), message=message, **details))

    references, identical, by_vehicle = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in rows:
        by_vehicle[r['vehicle_id']].append(r)
        if r['reference']:
            references[(r['vehicle_id'], r['reference'].casefold())].append(r)
        identical[(r['vehicle_id'], r['occurred_at'], r['litres'], r['amount_cents'], r['odometer_km'])].append(r)
        tank = vehicle_map.get(r['vehicle_id'], {}).get('tank_capacity_l')
        if tank and D(r['litres']) > D(tank):
            add('capacity', [r], 'Review this purchase: recorded litres exceed the supplied tank capacity. Check the receipt, capacity and any extra containers.')
    duplicate_ids = set()
    for group in references.values():
        if len(group) > 1:
            add('repeated_reference', group, 'Review the repeated receipt reference. These may be duplicate records or legitimate transactions with the same reference.')
            duplicate_ids.update(s['id'] for s in group)
    for group in identical.values():
        if len(group) > 1 and not all(s['id'] in duplicate_ids for s in group):
            add('similar_purchase', group, 'Review these matching purchase details; confirm whether both purchases occurred before voiding either record.')
    for group in by_vehicle.values():
        known = [r for r in group if r['odometer_km'] is not None]
        for previous, current in zip(known, known[1:]):
            if D(current['odometer_km']) < D(previous['odometer_km']):
                add('odometer_order', [previous, current], 'Check the declining odometer readings and transaction order; efficiency requires consistent readings.')

    prior = defaultdict(list)
    for interval in efficiency_intervals(rows)['intervals']:
        earlier = prior[interval['vehicle_id']]
        rate = D(interval['rate_l_per_100km'])
        if len(earlier) >= 6:
            baseline = median(D(i['rate_l_per_100km']) for i in earlier)
            spread = median(abs(D(i['rate_l_per_100km']) - baseline) for i in earlier) * D('1.4826')
            if rate > baseline * D('1.20') and rate > baseline + 3 * spread:
                evidence_ids = {i for item in [*earlier, interval] for i in item['source_ids']}
                add('efficiency_change', [lookup[i] for i in sorted(evidence_ids, key=lambda i: lookup[i]['occurred_at'])],
                    'Review the increased recorded fuel rate. Check missing receipts, loads, routes and conditions before interpreting a maintenance issue.',
                    baseline=str(baseline), rate=str(rate), earlier_intervals=len(earlier),
                    threshold='Exceeds both 20% above the earlier median and three scaled MADs; exploratory rule',
                    interval_start=interval['start'], interval_end=interval['end'])
        earlier.append(interval)
    return findings


def totals(records):
    volume = sum((D(r['litres']) for r in records), D(0))
    amount = sum(r['amount_cents'] for r in records)
    return dict(amount_cents=amount, litres=str(volume), receipt_count=len(records),
                price_per_litre=str(D(amount) / 100 / volume) if volume else None)


def weekly_review(records, vehicles, week, today):
    week = date.fromisoformat(week) if isinstance(week, str) else week
    today = date.fromisoformat(today) if isinstance(today, str) else today
    start = week - timedelta(days=week.weekday())
    if start > today:
        raise ValueError('Choose a week that has already started.')
    end = min(start + timedelta(days=6), today)
    previous_start, previous_end = start - timedelta(days=7), end - timedelta(days=7)
    rows = active(records)
    selected = [r for r in rows if start.isoformat() <= r['occurred_at'][:10] <= end.isoformat()]
    prior_rows = [r for r in rows if previous_start.isoformat() <= r['occurred_at'][:10] <= previous_end.isoformat()]
    current, previous = totals(selected), totals(prior_rows)
    difference = current['amount_cents'] - previous['amount_cents']
    decomposition = None
    if D(current['litres']) and D(previous['litres']):
        v0, v1 = D(previous['litres']), D(current['litres'])
        p0, p1 = D(previous['amount_cents']) / v0, D(current['amount_cents']) / v1
        volume_part = (v1 - v0) * (p1 + p0) / 2
        decomposition = dict(volume_cents=str(volume_part), price_cents=str(D(difference) - volume_part))
    efficiency = efficiency_intervals(rows)
    return dict(start=start.isoformat(), end=end.isoformat(), previous_start=previous_start.isoformat(),
        previous_end=previous_end.isoformat(), partial_week=end < start + timedelta(days=6),
        current=current, previous=previous, change_cents=difference,
        change_pct=str(D(difference) / previous['amount_cents'] * 100) if previous['amount_cents'] else None,
        decomposition=decomposition, records=selected,
        intervals=[i for i in efficiency['intervals'] if start.isoformat() <= i['end'][:10] <= end.isoformat()],
        warnings=[w for w in efficiency['warnings'] if start.isoformat() <= w['end'][:10] <= end.isoformat()],
        exceptions=[e for e in exceptions(rows, vehicles) if start.isoformat() <= e['date'] <= end.isoformat()],
        caveat='Litres are fuel purchased during this period, not measured weekly consumption. Missing records and fuel-grade changes affect comparisons. '
               'Full-to-full intervals show their actual dates and assume all purchases are recorded.')


def scenario(km, rate, prices):
    distance = decimal_value(km, 'Planned kilometres', positive=False, maximum='100000')
    efficiency = decimal_value(rate, 'Assumed L/100 km', maximum='1000')
    if not prices or len(prices) > 3:
        raise ValueError('Supply one to three fuel-price assumptions.')
    cost = [distance / 100 * efficiency * decimal_value(p, 'Assumed price', places=3, maximum='100') for p in prices]
    return dict(litres=str(distance / 100 * efficiency), costs=[str(c.quantize(D('0.01'))) for c in cost],
                caveat='Calculated from your distance, fuel-rate and price assumptions. These scenarios are not statistical forecasts or guaranteed future costs.')


def observed_rate(records):
    intervals = efficiency_intervals(records)['intervals']
    distance = sum((D(i['distance_km']) for i in intervals), D(0))
    volume = sum((D(i['litres']) for i in intervals), D(0))
    return str(volume / distance * 100) if distance else None


def render_weekly_report(review, vehicles=(), reviews=()):
    # Downloads may be rendered by Markdown readers with remote images/HTML enabled.
    import html
    import re
    def plain(value):
        return re.sub(r'([\\`*_{}\[\]()#!|])', r'\\\1', html.escape(str(value))).replace('\n', ' ')
    names = {v['id']: v['name'] for v in vehicles}
    outcomes = {r['id']: r for r in reviews}
    money = lambda cents: f'AUD {D(cents)/100:,.2f}'
    r = review
    lines = ['# Weekly fuel review', '', f"Period: {r['start']} to {r['end']}{' (partial week)' if r['partial_week'] else ''}.",
             f"Recorded spending: {money(r['current']['amount_cents'])}; {r['current']['litres']} litres purchased; {r['current']['receipt_count']} receipts.",
             f"Comparison: {r['previous_start']} to {r['previous_end']}; {money(r['previous']['amount_cents'])}.", '', r['caveat'], '', '## Spending change', '']
    if r['decomposition']:
        lines += [f"Purchase-volume contribution: {money(r['decomposition']['volume_cents'])}.",
                  f"Paid-price contribution: {money(r['decomposition']['price_cents'])}. Display rounding may affect the sum by a cent."]
    else:
        lines += ['Price/volume decomposition unavailable because one period has no recorded purchases.']
    lines += ['', '## Items for review', '']
    if not r['exceptions']:
        lines += ['No rules flagged the supplied records for this period. This does not establish completeness or absence of problems.']
    for item in r['exceptions']:
        outcome = outcomes.get(item['id'], {})
        lines += [f"- {plain(names.get(item['vehicle_id'], item['vehicle_id']))}: {item['message']}",
                  f"  Evidence records: {', '.join(item['source_ids'])}; outcome: {plain(outcome.get('status', 'open'))}; {plain(outcome.get('note', ''))}"]
    lines += ['', '## Supported efficiency intervals', '']
    for i in r['intervals']:
        lines += [f"- {plain(names.get(i['vehicle_id'], i['vehicle_id']))}: {i['start']} to {i['end']}, {D(i['rate_l_per_100km']):.2f} L/100 km over {i['distance_km']} km."]
    for w in r['warnings']:
        lines += [f"- Efficiency withheld: {w['reason']} ({w['start']} to {w['end']})."]
    lines += ['', 'Review flags are prompts to inspect records, not diagnoses, fraud findings or demonstrated savings.']
    return '\n'.join(lines) + '\n'
