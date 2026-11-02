# Census SAHIE health-insurance estimates in DuckDB

Model-based health-insurance estimates for all U.S. states, DC and counties in 2024,
from the Census Bureau's August 2026 [Small Area Health Insurance Estimates release](https://www.census.gov/data/datasets/time-series/demo/sahie/estimates-acs.html).
This release adds county insurance coverage and poverty-group estimates
to datapond's Medicare expenditure and provider data.

| Table or view | Grain | Rows |
|---|---|---:|
| `estimates` | Year, geography, age, race, sex, income group | 402,786 |
| `geographies` | State or county FIPS | 3,195 |
| `category_codes` | Category and code | 26 |
| `county_uninsured` (view) | County; under 65, all races, both sexes, all incomes | 3,144 |

The 14.17 MB database also contains standard datapond `_metadata` and `_columns`,
plus `_provenance` with the exact source identity. Table-row totals are **not people**.
See [FIELD-GUIDE.md](FIELD-GUIDE.md) for definitions and [DICTIONARY.md](DICTIONARY.md)
for types, null rates and joins.

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

## Query a local build

```python
import duckdb
con = duckdb.connect('data/sahie.duckdb', read_only=True)
print(con.sql("""
    SELECT fips, county_name, pctui, pctui_moe
    FROM county_uninsured WHERE statefips = '36' ORDER BY fips LIMIT 3
""").fetchall())
con.close()
```

```r
library(DBI)
con <- dbConnect(duckdb::duckdb(), dbdir='data/sahie.duckdb', read_only=TRUE)
dbGetQuery(con, "SELECT fips, county_name, pctui, pctui_moe
                FROM county_uninsured WHERE statefips='36' ORDER BY fips LIMIT 3")
dbDisconnect(con, shutdown=TRUE)
```

The released Python datapond 0.1.5 and CRAN R datapond 0.1.0 clients have also been
tested against this exact file through an isolated HTTP range server and temporary
registry. Registry-based `datapond.connect('sahie')` / `dp_connect('sahie')` access
becomes available when the corresponding registry entry is merged. No client
package change is necessary.

## Rebuild and validate

Python >=3.10 and `uv` are required for the commands below. Dependencies use DuckDB
1.5.5 and an exact `datapond-build` Git revision in `pyproject.toml`.

```sh
uv run python -m unittest -v test_build
uv run python build_database.py --sample-rows 1000 --output data/sample.duckdb
uv run python build_database.py --output data/sahie.duckdb
```

Start with the sample. The full pinned ZIP is only 13,653,790 bytes; the builder
streams its one 111.58 MB CSV member, uses one thread and 256 MiB DuckDB memory,
disables disk spill and refuses to overwrite prior files. Reserve at least 512 MiB
of free space on the actual host filesystem. Failed intermediates are preserved
for inspection; use a fresh output basename when retrying.

The source lock rejects a changed upstream file instead of silently calling it the
same release. To refresh, review the official release and layout, update the lock,
year/schema expectations and release-specific checks, then rerun sample, full build,
tests and both client checks. This initial release includes **2024 only**; historical
SAHIE years are a useful later extension, not implicitly included here.

With already installed released clients and their HTTPFS extensions, run:

```sh
python run_smoke.py --db data/sahie.duckdb --python /path/to/client/python --rscript /path/to/Rscript \
  --r-library /path/to/existing/R/library
```

The server binds only to localhost, serves this database and a temporary registry,
and shuts down on completion. It performs no publication or credential setup.
Evidence from the completed build and client checks is in [evidence](evidence).

## Interpretation and reuse

These are modeled aggregate estimates with 90% margins of error, not individual
records or causal effects. Age, income, race totals and sex totals overlap; do not sum across them.
Race detail is state-level only. FIPS codes retain leading zeros; match geographic
vintages when joining to other datasets. The source's `.` values become SQL NULL,
including unavailable Kalawao County estimates. Zero MOEs retain the source rounding
meaning, not certainty. See the [official layout](https://www2.census.gov/programs-surveys/sahie/technical-documentation/file-layouts/sahie-file-layout-2008-2024.pdf).

Source data: U.S. public domain as a Census Bureau work. The [Census policy](https://www2.census.gov/foia/ds_policies/ds027.pdf), page 9,
distinguishes U.S. copyright treatment from possible foreign protection; no worldwide
CC0 license is asserted. Please cite the Census SAHIE 2024 release and the source SHA
recorded in [source-lock.json](source-lock.json).

`HF-README.md` is the build-time card template. `prepare_release.py` creates the
release-ready Hugging Face README and hashes the complete upload set. Validation
summary and source-file hashes are in `evidence/release-validation.json`; full
private review transcripts and local machine logs are excluded from this repository.
