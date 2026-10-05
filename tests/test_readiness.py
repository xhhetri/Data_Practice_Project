"""Regression checks for errors found during the project readiness audit."""
import numpy as np
from src.analysis import silver, validate


def test_vehicle_stock_is_historical_and_matches_bitre_units():
    df = silver.load_vehicle_registrations()
    assert 'year' in df.columns, 'Fleet snapshot cannot replace historical stock'
    nsw = df[df.state == 'NSW'].set_index('year')['count']
    assert nsw.loc[2010] == 4681471
    assert nsw.loc[2023] == 6155747
    assert nsw.nunique() > 10
    assert not df.duplicated(['state', 'year']).any()


def test_reconciliation_preserves_direction_and_does_not_claim_validation():
    comparison, fig = validate.validate_emission_factors(save=False)
    import matplotlib.pyplot as plt
    plt.close(fig)
    assert 'signed_pct_diff' in comparison.columns
    expected = (comparison.implied_kt_co2e / comparison.ghg_kt_co2e - 1) * 100
    np.testing.assert_allclose(comparison.signed_pct_diff, expected)
    assert (comparison.signed_pct_diff > 0).sum() > len(comparison) / 2
