---
pretty_name: Census Small Area Health Insurance Estimates (SAHIE), 2024
license: other
license_name: us-public-domain-census-bureau-work
license_link: https://www2.census.gov/foia/ds_policies/ds027.pdf
tags:
- health-insurance
- census
- sahie
- duckdb
- datapond
size_categories:
- 100K<n<1M
---

# County and State Health Insurance Estimates

**Local publication candidate; not yet hosted or registered.** The Census Bureau's
August 2026 release provides 2024 model-based health-insurance estimates for states,
DC and counties. This compact DuckDB database retains published counts, percentages
and 90% margins of error, with standard datapond metadata.

| Table | Description | Rows | Columns |
|---|---|---:|---:|
| `estimates` | Demographic/income estimates, overlapping groups | 402,786 | 27 |
| `geographies` | State and county FIPS/names | 3,195 | 6 |
| `category_codes` | Official category definitions | 26 | 3 |

`county_uninsured` selects under-65, all-race, both-sex, all-income estimates for
3,144 counties. Source missing values remain SQL NULL. The database is 14,168,064
bytes. Source ZIP SHA-256: `5ec0a0cc5cb2e4e17cf046d9f68508decfdb4d9bbb982781d94bbf56ce50347a`.

```sql
-- After opening the local sahie.duckdb candidate:
SELECT fips, county_name, pctui, pctui_moe
FROM county_uninsured WHERE statefips='36' ORDER BY fips LIMIT 3;
```

Python and R local examples are in README.md. The released datapond clients have
passed localhost HTTP range tests with this exact database; public registry access
will require publication. Use the build manifest for artifact identity and checks.

The groups overlap, so table rows must not be added as population counts. Race
detail is state-only. Match geographic vintages before FIPS joins. Kalawao County
is unavailable. Zero margins of error reflect source rounding. These aggregate
modeled data do not identify causal effects. See the [field guide](https://huggingface.co/datasets/Nason/sahie-database/blob/main/FIELD-GUIDE.md),
[data dictionary](https://huggingface.co/datasets/Nason/sahie-database/blob/main/DICTIONARY.md) and the
[official layout](https://www2.census.gov/programs-surveys/sahie/technical-documentation/file-layouts/sahie-file-layout-2008-2024.pdf).

Source: [Census SAHIE, 2024](https://www.census.gov/data/datasets/time-series/demo/sahie/estimates-acs.html),
retrieved November 2, 2026. U.S. public domain as a Census Bureau work under the
[agency policy](https://www2.census.gov/foia/ds_policies/ds027.pdf); no worldwide CC0 claim.

The population denominator is the Census poverty universe. `pctui` uses the
selected income group; `pctelig` uses the same demographic group at all incomes.
Published 90% uncertainty reflects model and sampling error, subject to model
assumptions, and excludes nonsampling error. Missing estimates remain NULL.
The field guide defines all measures, overlapping categories, zero-denominator
missingness, Kalawao omissions, rounding and geographic-vintage caveats.

## Query the hosted database with Python or R

These direct DuckDB examples work independently of registry-PR merge status.
Install Python `duckdb` or R `duckdb` and `DBI`; `INSTALL httpfs` below installs
DuckDB's HTTP extension if it is not already present. Tested engine versions are
Python DuckDB 1.5.6 and R DuckDB 1.5.5.

```python
import duckdb
con = duckdb.connect(config={"memory_limit": "128MiB", "threads": "1",
                            "max_temp_directory_size": "0B"})
try:
    con.execute("INSTALL httpfs; LOAD httpfs")
    con.execute("ATTACH 'https://huggingface.co/datasets/Nason/sahie-database/resolve/main/sahie.duckdb' AS sahie (READ_ONLY)")
    print(con.execute("""
        SELECT fips, county_name, pctui, pctui_moe
        FROM sahie.county_uninsured
        WHERE statefips = '36' ORDER BY fips LIMIT 3
    """).fetchall())
finally:
    con.close()
```

```r
library(DBI)
con <- dbConnect(duckdb::duckdb())
tryCatch({
  dbExecute(con, "SET memory_limit='128MiB'")
  dbExecute(con, "SET threads=1")
  dbExecute(con, "SET max_temp_directory_size='0B'")
  dbExecute(con, "INSTALL httpfs; LOAD httpfs")
  dbExecute(con, "ATTACH 'https://huggingface.co/datasets/Nason/sahie-database/resolve/main/sahie.duckdb' AS sahie (READ_ONLY)")
  print(dbGetQuery(con, "
    SELECT fips, county_name, pctui, pctui_moe
    FROM sahie.county_uninsured
    WHERE statefips='36' ORDER BY fips LIMIT 3"))
}, finally = dbDisconnect(con, shutdown=TRUE))
```

Expected first counties are Albany, Allegany and Bronx, with uninsured percentages
4.8, 5.4 and 8.1 and 90% margins of error 0.5, 0.7 and 0.6 percentage points.
Python returns DECIMAL percentages as `Decimal`; R returns numeric values. FIPS
identifiers remain strings. These are source estimates, not individual records.

Once the `sahie` registry entry is merged, Python `datapond.connect('sahie')` and
R `datapond::dp_connect('sahie')` provide the registered shortcut. Use Python
datapond 0.1.5 or later and released CRAN R datapond (tested 0.1.0). Before merge,
the direct examples above avoid depending on an unavailable registry identifier.

Queries run on your machine. The 14.17 MB file size is storage, not required RAM;
DuckDB's 128 MiB limit covers its buffer pool, not the entire Python/R process.
Selected columns reduce transfer, but a final `LIMIT` does not guarantee a small
scan. These examples use one thread and disable disk spill.
