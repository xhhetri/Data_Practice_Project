# NSW transport emissions briefing

NSW transport emissions rose 2.1% between FY2010-11 and FY2023-24.

Latest selected emissions: **26,960.60 kt CO2-e** (FY2023-24).
Per capita: **3,189.37 kg CO2-e per person**; rank 6 of 7 jurisdictions (highest first).

Per-capita emissions changed -13.2%. Check both total and per-capita changes before deciding what to investigate.

## Peer comparison

| Jurisdiction | Total kt CO2-e | kg CO2-e/person |
|---|---:|---:|
| NT | 1,908.88 | 7,352.18 |
| WA | 16,042.02 | 5,440.43 |
| QLD | 23,845.50 | 4,311.41 |
| SA | 6,602.58 | 3,522.55 |
| VIC | 22,213.70 | 3,218.65 |
| NSW | 26,960.60 | 3,189.37 |
| TAS | 1,714.07 | 2,983.89 |

## Fuel-sales outlook

Method: holt_winters; selected using 21 earlier rolling windows.
Untouched holdout MAPE: 3.84%.
Same-holdout seasonal-naive baseline MAPE: 3.09%. This score is reported after selection; it does not choose the operational method.
Holdout interval coverage: 80% band 83.33% and 95% band 83.33% across 6 months only.
Approximate bands from a small, changing historical sample. 6-month holdout coverage is coarse; future shocks may fall outside bands.

| Month | Sales ML | Approximate 95% band ML |
|---|---:|---:|
| 2026-07-01 | 1,062.00 | 1,004.22 to 1,119.78 |
| 2026-08-01 | 1,070.89 | 1,029.80 to 1,111.98 |
| 2026-09-01 | 1,047.98 | 968.27 to 1,127.69 |
| 2026-10-01 | 1,090.53 | 972.44 to 1,208.63 |
| 2026-11-01 | 1,109.70 | 1,020.00 to 1,199.40 |
| 2026-12-01 | 1,111.70 | 1,045.10 to 1,178.30 |

## Interpretation limits

- Official emissions cover the whole transport sector; petrol plus total diesel sales have a different boundary.
- ACT is excluded from the merged comparison because the selected sales source has no separate ACT series.
- Historical vehicle stock uses BITRE calendar-year labels associated with the financial year starting in that year; it is not a financial-year average.
- State comparisons indicate where to investigate; they do not establish which policy caused a change.
- Source release dates differ. Forecasts start after the latest observed sales month, which may precede today.

## Sources and provenance

Pipeline run: `712af298d4510368`
Built at: 2026-10-08T00:54:00.572201+00:00
Observation cutoffs: {"annual_start": 2010, "annual_end": 2023, "sales_start": "2010-07-01", "sales_end": "2026-06-01", "annual_rows": 98, "monthly_rows": 1344}

- [abs_population](https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/latest-release); file SHA256 `8fe4b1a1fc7d228e4e086214c5ecf8d5a8f3f1de803e107cb02bae0e1e5cc34f`
- [bitre_yearbook](https://www.bitre.gov.au/sites/default/files/documents/bitre-yearbook-2025.pdf); file SHA256 `f2359bd8c3175e31e2e4ad47b53b9d0acf315142ab1deb1e4bfb092db0b3ebdc`
- [petroleum_statistics](https://www.energy.gov.au/energy-data/australian-petroleum-statistics); file SHA256 `96eaf6375ff8e4aed88ba98a37fbca999c77c8ab7c4a04a96fad9f10621f6041`
- [quarterly_ghg_update](https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-gas-inventory-quarterly-updates); file SHA256 `a7379282533ce0a0db4e94aefbeaa77643374a65250a49dcf4cd4442c72c5f54`
- [state_territory_ghg](https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-accounts/state-and-territory-greenhouse-gas-inventories-data-tables-methodology); file SHA256 `0323c34b1411f998560f33258e7c1fb3e97ed4b859e5310e9ee8cacbedd0b8fa`
- [nga_factors_2025](https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-accounts-factors-2025); file SHA256 `ef398719acf8e22136674573cfed9550bdb3af4303cee36fe8b60991a5aec16d`
