-- County estimates with published uncertainty, no overlapping-category sums.
SELECT fips, county_name, pctui, pctui_moe
FROM county_uninsured WHERE statefips = '36' ORDER BY fips LIMIT 3;

-- Published state estimates for all people under 65 at <=138% of poverty.
SELECT fips, state_name, nipr, nui, pctui, pctui_moe
FROM estimates
WHERE geocat = 40 AND agecat = 0 AND racecat = 0 AND sexcat = 0 AND iprcat = 3
ORDER BY fips;

-- Discover the complete age code definitions before selecting a population.
SELECT code, label FROM category_codes WHERE category = 'agecat' ORDER BY code;
