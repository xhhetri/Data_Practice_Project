"""Authoritative landing pages and explicit activity boundaries."""
SOURCES = {
    'abs_population': ('https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/latest-release', 'Quarterly estimated resident population; FY quarterly mean'),
    'bitre_yearbook': ('https://www.bitre.gov.au/sites/default/files/documents/bitre-yearbook-2025.pdf', 'Table 4.3 road VKT; Table 4.6b historical calendar-year vehicle stock'),
    'petroleum_statistics': ('https://www.energy.gov.au/energy-data/australian-petroleum-statistics', 'Monthly automotive gasoline and TOTAL diesel SALES; not road-only consumption'),
    'quarterly_ghg_update': ('https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-gas-inventory-quarterly-updates', 'National quarterly inventories, retained separately from state analysis'),
    'state_territory_ghg': ('https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-accounts/state-and-territory-greenhouse-gas-inventories-data-tables-methodology', 'Financial-year whole-transport inventory; all transport modes'),
    'nga_factors_2025': ('https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-accounts-factors-2025', 'Table 9 car/light-commercial combustion factors; used only as a boundary diagnostic'),
}
