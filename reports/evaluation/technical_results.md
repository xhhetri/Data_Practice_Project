# Technical evaluation results

Run `982d7cbfcc4474d3`; built 2026-10-03T10:38:50.605958+00:00.

These are computed results, not participant-study findings. See docs/evaluation/pilot_protocol.md for the benefit evaluation.

## Monthly sales forecasts

Candidates are selected on earlier rolling windows. The final six months are held out of selection; all available observations are then used to refit the after-cutoff forecast. Percent errors are MAPE; lower is better.

| State | Earlier seasonal-naive MAPE % | Earlier Holt-Winters MAPE % | Selected | Final holdout MAPE % | Same-holdout naive MAPE % | Holdout 95% band coverage % |
|---|---:|---:|---|---:|---:|---:|
| NSW | 4.71 | 4.04 | holt_winters | 3.84 | 3.09 | 83.33 |
| NT | 10.16 | 8.43 | holt_winters | 12.92 | 16.32 | 100.00 |
| QLD | 4.65 | 4.53 | holt_winters | 5.68 | 4.63 | 100.00 |
| SA | 4.81 | 3.73 | holt_winters | 4.53 | 4.53 | 83.33 |
| TAS | 6.12 | 5.74 | holt_winters | 4.71 | 5.89 | 100.00 |
| VIC | 5.05 | 3.93 | holt_winters | 3.45 | 3.65 | 83.33 |
| WA | 4.49 | 3.84 | holt_winters | 2.71 | 4.46 | 100.00 |

21 earlier windows per state. Final holdout: 2026-01-01 to 2026-06-01.
After-cutoff outlook: 2026-07-01 to 2026-12-01.
Approximate bands from a small, changing historical sample. Six-month holdout coverage is coarse; future shocks may fall outside bands.

The 80/95% labels describe empirical error quantiles, not guaranteed future coverage. Six held-out observations cannot establish calibrated uncertainty. Candidate selection has not used the final holdout error. The same-holdout baseline is reported after selection, so selected Holt-Winters can underperform it on this test.

## Annual association benchmark

| Method | Chronological pooled R² | MAE kt CO2-e | MAPE % |
|---|---:|---:|---:|
| previous_year | 0.9940 | 494.10 | 4.13 |
| linear_regression | 0.9951 | 541.88 | 7.03 |
| random_forest | 0.9920 | 563.22 | 4.19 |

Expanding whole-year folds; contemporaneous inputs, associative only
High pooled R2 reflects state scale and accounting relationships. This is not a causal intervention model or a forecast of future emissions.

The previous-year benchmark uses only earlier emissions, while regression receives actual same-year activity. This is an association benchmark, not a like-for-like operational emissions forecast.

### Per-state annual MAPE (%)

| State | Previous year | Linear regression | Random forest |
|---|---:|---:|---:|
| NSW | 3.76 | 2.65 | 3.87 |
| NT | 8.20 | 18.05 | 7.26 |
| QLD | 3.05 | 3.85 | 3.28 |
| SA | 2.86 | 4.30 | 2.66 |
| TAS | 3.34 | 12.39 | 2.29 |
| VIC | 4.39 | 3.72 | 6.35 |
| WA | 3.33 | 4.24 | 3.60 |

## Unresolved boundary diagnostic

Mean absolute relative gap: 29.71%. Sales-based implied emissions exceed the official transport inventory in 93 of 98 state-years.
This is not a passed inventory validation. Total diesel sales include different uses, and the simple factors are not the state transport inventory methodology. Use official inventory values for the briefing.

## Reproduction

Run python run_pipeline.py, then python -m pytest tests/. Source and core-output hashes are in reports/run_metadata.json. The standalone and database-backed interfaces carry the same run identifier.
