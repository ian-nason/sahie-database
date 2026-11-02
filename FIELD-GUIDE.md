# SAHIE 2024 field guide

The [official 2008–2024 layout](https://www2.census.gov/programs-surveys/sahie/technical-documentation/file-layouts/sahie-file-layout-2008-2024.pdf)
and CSV preamble define these fields. Values and published 90% margins of error are
retained without recalculation.

| Fields | Meaning |
|---|---|
| `year`, `version` | Estimate year; version is the source's empty string for this release, not a missing key |
| `statefips`, `countyfips`, `geocat` | Two- and three-character codes; geography category 40 state, 50 county. State records use county code `000` |
| `fips` | Added join key: two characters for state rows, five for county rows. Always filter geography level |
| `agecat`, `racecat`, `sexcat`, `iprcat` | Demographic and income categories. Join to `category_codes` by category name and code |
| `nipr`, `nipr_moe` | Number in the demographic/income group in the poverty universe; count margin of error |
| `nui`, `nui_moe` | Number uninsured in that group; count margin of error |
| `nic`, `nic_moe` | Number insured in that group; count margin of error |
| `pctui`, `pctui_moe` | Percent uninsured within that demographic/income group; percentage-point margin of error |
| `pctic`, `pctic_moe` | Percent insured within that demographic/income group; percentage-point margin of error |
| `pctelig`, `pctelig_moe` | Number uninsured in the income group divided by the demographic group's poverty-universe population at all incomes, times 100; percentage-point margin of error |
| `pctliic`, `pctliic_moe` | Number insured in the income group divided by the demographic group's poverty-universe population at all incomes, times 100; percentage-point margin of error |
| `state_name`, `county_name` | Source geography labels; state estimate rows have blank county names (NULL in `geographies`) |
| `source_row` | One-based data-row position after the CSV header; added for provenance |

Income codes 0–5 mean all incomes, <=200%, <=250%, <=138%, <=400%, and 138%–400%
of poverty. Age codes include overlapping ranges, with 21–29 years added as code 6
in 2024. Under-19 estimates are not split by sex or detailed race. Race detail applies
only to state rows. These restrictions are checked before a build is accepted.
The source population is the poverty universe (layout note 2), not the entire
resident population. All-race and
both-sex totals also overlap their component groups.

`county_uninsured` fixes age=0 (under 65), race=0, sex=0 and income=0, providing a
safe one-row-per-county starting point. It includes 3,144 counties, with NULLs for
Kalawao County (`15005`). Source missing values also occur where percentages have
zero denominators; do not replace NULLs with zero. Exact null counts are recorded
in the build manifest.

Published values retain source precision. In 56 all-income source rows,
`pctliic` differs from `pctic` by 0.1 percentage point; these source values are
preserved. The consistency checks allow that published precision, not larger
discrepancies. The official preamble notes that details may not sum due to rounding.

A count MOE of zero represents less than one person before rounding; a percentage
MOE of zero represents less than 0.1 percentage point. Do not pool published MOEs
or estimate state rates by averaging county percentages. Use published state rows
for state estimates and Census guidance for derived comparisons.

The published uncertainty reflects model and sampling error, subject to the model
assumptions; it excludes nonsampling error such as coverage or processing error.
See the [Census source and accuracy guidance](https://www.census.gov/programs-surveys/sahie/technical-documentation/source-and-accuracy.html).
Connecticut uses planning regions as county equivalents in this release; match
geographic vintages before joining to older Connecticut county data. DuckDB DECIMAL
percentages appear as Decimal values in Python and numeric doubles in R; retain
the source's one-decimal precision. Client tests cover DuckDB 1.5.5 and 1.5.6 only.
