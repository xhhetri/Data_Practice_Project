# FuelScope: computed market-model evidence

Evidence `b90c007a7dd3c810`; model `c68367a4645c6b17`; historical run `712af298d4510368`.

Separate monthly petrol and total diesel SALES, in ML. The current extract covers July 2010–July 2026 across 7 jurisdictions.
Each series compares seasonal naive and additive Holt-Winters on 41 earlier rolling origins (60 initial training months, six-month horizon, three-month steps).
Method selection precedes the final 6 observed months, February 2026–July 2026. Refit outlook: August 2026–January 2027.

| State | Fuel | Selected | Earlier naive MAPE % | Earlier HW MAPE % | Final MAPE % | Final naive MAPE % | 95% band coverage % |
|---|---|---|---:|---:|---:|---:|---:|
| NSW | Diesel | holt_winters | 5.20 | 3.57 | 4.83 | 3.11 | 66.67 |
| NSW | Petrol | holt_winters | 7.17 | 6.74 | 3.28 | 3.18 | 100.00 |
| NT | Diesel | holt_winters | 11.66 | 10.20 | 6.67 | 17.91 | 100.00 |
| NT | Petrol | holt_winters | 8.21 | 6.93 | 3.15 | 2.86 | 100.00 |
| QLD | Diesel | holt_winters | 5.75 | 5.02 | 2.60 | 5.66 | 100.00 |
| QLD | Petrol | holt_winters | 4.99 | 3.94 | 7.15 | 6.50 | 83.33 |
| SA | Diesel | holt_winters | 5.70 | 4.42 | 7.41 | 8.55 | 50.00 |
| SA | Petrol | holt_winters | 5.86 | 4.29 | 3.62 | 3.80 | 100.00 |
| TAS | Diesel | holt_winters | 7.75 | 5.85 | 6.90 | 9.99 | 100.00 |
| TAS | Petrol | holt_winters | 7.14 | 6.32 | 4.25 | 5.05 | 100.00 |
| VIC | Diesel | holt_winters | 4.99 | 4.05 | 4.96 | 4.21 | 83.33 |
| VIC | Petrol | seasonal_naive | 7.20 | 8.07 | 4.60 | 4.60 | 100.00 |
| WA | Diesel | holt_winters | 5.12 | 4.10 | 2.91 | 3.31 | 100.00 |
| WA | Petrol | holt_winters | 6.02 | 4.58 | 3.57 | 5.11 | 100.00 |

## Interpretation and limitations

- The current revised extract is used; original historical publication vintages are not reconstructed.
- Rolling windows overlap. Historical absolute-error quantiles provide approximate bands, not calibrated future probabilities.
- Six final holdout observations make interval coverage coarse. Future shocks may exceed historical errors.
- Candidate selection does not guarantee a win on the final holdout; baseline wins are reported.
- Daily prices and weekly national stocks currently provide review context, not added predictive features.
- Review queue markers are transparent descriptive checks, not a learned shortage classifier.
- Price-change review marker: absolute seven-calendar-day change of at least 5 c/L. Source-age markers: prices more than 4 days old; stocks more than 10 days old.
- National stocks, city wholesale prices, monthly state sales and annual official inventories retain different boundaries.
- Actual participant benefit, professional adoption and policy effects have not been measured.

## Current source evidence

- [AIP terminal gate prices](https://aip.com.au/resources/historical-ulp-and-diesel-tgp-data/): observed through 2026-10-02, 94,992 parsed observations; status unchanged; SHA256 `02beec619266ffa78b6e7ad1c1b5eb83890cc7a4c31061a830e7de28bbdfee5e`.
- [DCCEEW weekly MSO stocks](https://www.dcceew.gov.au/energy/security/australias-fuel-security/minimum-stockholding-obligation/statistics): observed through 2026-09-22, 93 parsed observations; status unchanged; SHA256 `7399e25a2f0714c9a452297bd2b200cec024ebc3bae9d32382df1fa74f88a578`.
- [Australian Petroleum Statistics](https://www.energy.gov.au/publications/australian-petroleum-statistics-2026): observed through 2026-07-01, 2,702 parsed observations; status unchanged; SHA256 `d7b5d662a36e501cf3481c14e1a1a25bcd90b4afc5c496419f3a1ebf10e3ea51`.
