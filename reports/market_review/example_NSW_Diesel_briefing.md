# FuelScope weekly fuel-market briefing

NSW · Diesel · prepared 4 Oct 2026

## Current market evidence
- Sydney wholesale terminal price: 265.8 c/L including GST (2 Oct 2026).
- Change since 25 Sept 2026: -5.7 c/L.
- National diesel MSO holdings: 2,938 ML (22 Sept 2026).
- Effective national obligation: 2,225 ML; holdings 32.0% above it.
- Days equivalent: 32; this is not a countdown to shortage.

## Evidence to review
- Diesel prices fell: Sydney wholesale price changed -5.7 c/L between 25 Sept 2026 and 2 Oct 2026. Next step: Check the price history before quoting a market movement.
- National stock evidence: Diesel holdings changed +85 ML since 15 Sept 2026. Latest observation: 22 Sept 2026. Next step: Review holdings and the effective obligation together.
- NSW sales above last year: July 2026 diesel sales: 654.0 ML, +0.1% versus the same month last year. Next step: Inspect seasonality and model errors in the sales outlook.

## Six-month state sales outlook
Monthly diesel SALES, ML; observed through July 2026.
Selected method: holt_winters. Earlier rolling windows: 41.
Final 6-month holdout MAPE: 4.83%; seasonal-naive baseline: 3.11%.
Approximate interval coverage on the small final holdout: 80% band 66.67%; 95% band 66.67%.

| Month | Timing | Sales ML | Approx. 95% band ML |
|---|---|---:|---|
| Aug 2026 | Elapsed · not observed in this extract | 657.1 | 593.5 – 720.7 |
| Sept 2026 | Elapsed · not observed in this extract | 650.5 | 612.7 – 688.3 |
| Oct 2026 | Current month | 673.5 | 621.3 – 725.6 |
| Nov 2026 | Upcoming | 680.8 | 624.1 – 737.6 |
| Dec 2026 | Upcoming | 657.8 | 600.7 – 715.0 |
| Jan 2027 | Upcoming | 636.8 | 594.5 – 679.0 |

Approximate bands from a small, changing historical sample. 6-month holdout coverage is coarse; future shocks may fall outside bands.

## Analyst notes
No analyst notes added.

## Sources
- AIP terminal gate prices: https://aip.com.au/resources/historical-ulp-and-diesel-tgp-data/ (observed through 2026-10-02; downloaded 2026-10-04T01:20:08.141288+00:00; status unchanged; SHA256 02beec619266ffa78b6e7ad1c1b5eb83890cc7a4c31061a830e7de28bbdfee5e).
- DCCEEW weekly MSO stocks: https://www.dcceew.gov.au/energy/security/australias-fuel-security/minimum-stockholding-obligation/statistics (observed through 2026-09-22; downloaded 2026-10-04T01:20:07.515560+00:00; status unchanged; SHA256 7399e25a2f0714c9a452297bd2b200cec024ebc3bae9d32382df1fa74f88a578).
- Australian Petroleum Statistics: https://www.energy.gov.au/publications/australian-petroleum-statistics-2026 (observed through 2026-07-01; downloaded 2026-10-04T01:20:09.142842+00:00; status unchanged; SHA256 d7b5d662a36e501cf3481c14e1a1a25bcd90b4afc5c496419f3a1ebf10e3ea51).

## Interpretation limits
- Market prices are wholesale terminal benchmarks, not pump prices or delivered supplier quotes.
- State sales and capital-city prices cover different geographies. MSO stocks are national.
- Total diesel sales include non-road uses; recorded sales are not unconstrained demand.
- MSO days equivalent, monthly consumption cover and IEA coverage have different definitions.
- Statistical changes identify evidence to review; they do not establish shortages or policy effects.
- Forecasts start after the observation cutoff. Approximate bands cannot guarantee future coverage.
- Backtests use the current revised sales extract; historical publication vintages were not reconstructed.
- This research prototype has no completed participant study; adoption and time savings remain unmeasured.

## Review identity
Evidence: b90c007a7dd3c810; model: 880221d8ce552683; historical pipeline: a57380f681bc5405.
Saved checkpoint: none.
Actual adoption and time savings have not yet been measured.