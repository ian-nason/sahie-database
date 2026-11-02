# SAHIE 2024 data dictionary

Source: U.S. Census Bureau, August 2026 release. All MOEs are at 90% confidence.
See FIELD-GUIDE.md for measure definitions, overlap warnings and missing-value policy.

## estimates

2024 model-based state/county health-insurance estimates, overlapping demographic/income groups; published 90% margins of error retained

Rows: 402,786

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| year | INTEGER | 0.0% | 2024 |  |
| version | VARCHAR | 0.0% |  |  |
| statefips | VARCHAR | 0.0% | 01 | Two-character state FIPS, preserving leading zeros. |
| countyfips | VARCHAR | 0.0% | 000 | Three-character code within state; combine with statefips. |
| geocat | INTEGER | 0.0% | 40 |  |
| agecat | INTEGER | 0.0% | 0 | category_codes where category=agecat; groups overlap. |
| racecat | INTEGER | 0.0% | 0 | category_codes where category=racecat; detailed race is state-only. |
| sexcat | INTEGER | 0.0% | 0 | category_codes where category=sexcat |
| iprcat | INTEGER | 0.0% | 0 | category_codes where category=iprcat; nested income groups overlap. |
| nipr | BIGINT | 114 (<0.1%) | 0 |  |
| nipr_moe | BIGINT | 114 (<0.1%) | 0 |  |
| nui | BIGINT | 114 (<0.1%) | 0 |  |
| nui_moe | BIGINT | 114 (<0.1%) | 0 |  |
| nic | BIGINT | 114 (<0.1%) | 0 |  |
| nic_moe | BIGINT | 114 (<0.1%) | 0 |  |
| pctui | DECIMAL(5,1) | 132 (<0.1%) | 0.0 |  |
| pctui_moe | DECIMAL(5,1) | 132 (<0.1%) | 0.0 |  |
| pctic | DECIMAL(5,1) | 132 (<0.1%) | 100.0 |  |
| pctic_moe | DECIMAL(5,1) | 132 (<0.1%) | 0.0 |  |
| pctelig | DECIMAL(5,1) | 120 (<0.1%) | 0.0 |  |
| pctelig_moe | DECIMAL(5,1) | 120 (<0.1%) | 0.0 |  |
| pctliic | DECIMAL(5,1) | 120 (<0.1%) | 0.0 |  |
| pctliic_moe | DECIMAL(5,1) | 120 (<0.1%) | 0.0 |  |
| state_name | VARCHAR | 0.0% | Alabama |  |
| county_name | VARCHAR | 0.0% |  |  |
| source_row | BIGINT | 0.0% | 1 |  |
| fips | VARCHAR | 0.0% | 01 | Use geography level and year; county FIPS is five characters. Match geographic vintages before joining. |

## geographies

State and county identifiers/names observed in this release; FIPS strings retain leading zeros

Rows: 3,195

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| fips | VARCHAR | 0.0% | 01 | Use geography level and year; county FIPS is five characters. Match geographic vintages before joining. |
| statefips | VARCHAR | 0.0% | 01 | Two-character state FIPS, preserving leading zeros. |
| countyfips | VARCHAR | 0.0% | 000 | Three-character code within state; combine with statefips. |
| geocat | INTEGER | 0.0% | 40 |  |
| state_name | VARCHAR | 0.0% | Alabama |  |
| county_name | VARCHAR | 1.6% | Abbeville County |  |

## category_codes

Definitions of the five categorical fields from the official SAHIE file preamble

Rows: 26

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| category | VARCHAR | 0.0% | agecat |  |
| code | INTEGER | 0.0% | 0 |  |
| label | VARCHAR | 0.0% | 18 to 64 years |  |
