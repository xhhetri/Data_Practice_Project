from datetime import date, timedelta
from decimal import Decimal
import pytest


def row(i, day, odo, litres='40', **changes):
    result = dict(id=str(i), vehicle_id='v', occurred_at=f'{day}T12:00:00', has_time=1,
                  odometer_km=str(odo) if odo is not None else None, litres=litres,
                  amount_cents=8000, tank_status='full', incomplete=0, void=0, revision=1,
                  reference='', vendor='', note='')
    result.update(changes)
    return result


def test_full_to_full_excludes_opening_volume_and_includes_partials():
    from src.fleet.analytics import efficiency_intervals
    rows = [row(1, '2024-01-01', 1000, '60'), row(2, '2024-01-03', 1200, '15', tank_status='partial'),
            row(3, '2024-01-08', 1500, '25')]
    intervals = efficiency_intervals(rows)['intervals']
    assert len(intervals) == 1
    assert Decimal(intervals[0]['rate_l_per_100km']) == 8
    assert Decimal(intervals[0]['litres']) == 40
    assert intervals[0]['source_ids'] == ['1', '2', '3']


@pytest.mark.parametrize('changes', [dict(odometer_km=None), dict(odometer_km='900'), dict(incomplete=1)])
def test_unsupported_efficiency_is_withheld(changes):
    from src.fleet.analytics import efficiency_intervals
    result = efficiency_intervals([row(1, '2024-01-01', 1000), row(2, '2024-01-08', 1500, **changes)])
    assert result['intervals'] == []
    assert result['warnings']


def test_ambiguous_date_only_same_day_records_have_no_efficiency():
    from src.fleet.analytics import efficiency_intervals
    records = [row(1, '2024-01-01', 1000), row(2, '2024-01-08', 1500, has_time=0),
               row(3, '2024-01-08', 1600, tank_status='partial', has_time=0)]
    assert efficiency_intervals(records)['intervals'] == []


def test_exact_spend_decomposition_and_partial_week_comparison():
    from src.fleet.analytics import weekly_review
    records = [row(1, '2024-01-01', 1000, '10', amount_cents=2000),
               row(2, '2024-01-05', 1200, '100', amount_cents=20000),
               row(3, '2024-01-08', 1500, '20', amount_cents=6000)]
    result = weekly_review(records, [], date(2024, 1, 8), date(2024, 1, 10))
    assert result['partial_week'] and result['end'] == '2024-01-10'
    assert result['previous']['amount_cents'] == 2000
    assert result['current']['amount_cents'] == 6000
    parts = result['decomposition']
    assert Decimal(parts['volume_cents']) + Decimal(parts['price_cents']) == 4000
    assert 'purchased' in result['caveat']


def test_zero_previous_period_and_future_week():
    from src.fleet.analytics import weekly_review
    result = weekly_review([], [], date(2024, 1, 8), date(2024, 1, 10))
    assert result['decomposition'] is None and result['change_pct'] is None
    with pytest.raises(ValueError):
        weekly_review([], [], date(2099, 1, 1), date(2024, 1, 10))


def test_efficiency_rule_uses_six_prior_intervals_and_evidence_revisions():
    from src.fleet.analytics import exceptions
    start = date(2024, 1, 1)
    records = [row(i, (start + timedelta(days=7*i)).isoformat(), 1000 + 500*i) for i in range(7)]
    changed = row(7, (start + timedelta(days=49)).isoformat(), 4500, '60')
    assert not [e for e in exceptions(records, []) if e['rule'] == 'efficiency_change']
    records.append(changed)
    alerts = [e for e in exceptions(records, []) if e['rule'] == 'efficiency_change']
    assert len(alerts) == 1 and alerts[0]['earlier_intervals'] == 6
    assert Decimal(alerts[0]['baseline']) == 8
    records[-1]['revision'] = 2
    assert [e for e in exceptions(records, []) if e['rule'] == 'efficiency_change'][0]['id'] != alerts[0]['id']


def test_duplicate_and_capacity_alerts_are_review_requests():
    from src.fleet.analytics import exceptions
    records = [row(1, '2024-01-01', 1000, reference='R1'), row(2, '2024-01-08', 1500, reference='R1')]
    alerts = exceptions(records, [dict(id='v', tank_capacity_l='30', revision=1)])
    assert {a['rule'] for a in alerts} == {'repeated_reference', 'capacity'}
    assert all('review' in a['message'].lower() or 'check' in a['message'].lower() for a in alerts)


def test_scenarios_are_explicit_assumptions_and_reject_invalid_values():
    from src.fleet.analytics import scenario
    result = scenario('500', '8', ['1.80', '2.00', '2.20'])
    assert result['costs'] == ['72.00', '80.00', '88.00']
    assert 'assumptions' in result['caveat']
    for value in ('-1', 'NaN', 'Infinity'):
        with pytest.raises(ValueError):
            scenario(value, '8', ['2'])


def test_observed_scenario_rate_is_distance_weighted():
    from src.fleet.analytics import observed_rate
    rows = [row(1, '2024-01-01', 1000), row(2, '2024-01-08', 1400, '32'), row(3, '2024-01-15', 2000, '72')]
    assert Decimal(observed_rate(rows)) == Decimal('10.4')
    assert observed_rate([]) is None


def test_report_treats_user_text_as_text_not_remote_markdown_content():
    from src.fleet.analytics import weekly_review, render_weekly_report
    records = [row(1, '2024-01-01', 1000, reference='same'), row(2, '2024-01-08', 1500, reference='same')]
    review = weekly_review(records, [], date(2024, 1, 8), date(2024, 1, 14))
    content = render_weekly_report(review, [dict(id='v', name='![Van](https://external.example/image)')],
        [dict(id=review['exceptions'][0]['id'], status='explained', note='<img src="https://external.example/note">')])
    assert '![Van](' not in content
    assert '<img ' not in content
