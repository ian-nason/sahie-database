# Proposed catalog text: SAHIE

Status: ready for review, not published. Proposed ID: `sahie`.

**Census Health Insurance Estimates** — 402,786 model-based 2024 state and county
estimates of insurance coverage, with demographic/income categories and published
90% margins of error. Includes 3,144 counties, 51 states/DC and a convenient
one-row-per-county view. Three data tables; 14.17 MB; annual source release.

Show Python and R alongside each other after the registry points to a verified
published artifact:

```python
import datapond
con = datapond.connect('sahie')
con.sql("SELECT fips, county_name, pctui, pctui_moe FROM county_uninsured WHERE statefips='36' ORDER BY fips LIMIT 3").show()
```

```r
library(datapond)
con <- dp_connect('sahie')
DBI::dbGetQuery(con, "SELECT fips, county_name, pctui, pctui_moe FROM county_uninsured WHERE statefips='36' ORDER BY fips LIMIT 3")
dp_disconnect(con)
```

Current public registry calls above will not resolve this proposed ID. The exact
queries were tested using a temporary local registry; the current local quick start
is in README.md. Do not increase the public catalog count until the upload and
registry change are complete. Generate the website's data from the approved registry
using its existing mechanism, and link the dictionary and source.

Source: https://www.census.gov/data/datasets/time-series/demo/sahie/estimates-acs.html

Reuse: U.S. public domain (Census Bureau work). Demographic categories overlap;
missing values remain NULL; published estimates are not causal effects.
