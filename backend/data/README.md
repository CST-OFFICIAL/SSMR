# Crop reference rules

No production crop rules are bundled yet. Do not fill this directory with guessed thresholds. Recommendations remain disabled until the project adds reviewed agricultural references applicable to the target region, growing season, and water-availability category.

`crop_rules.example.json` shows the expected shape using an empty array; it contains no recommendations. `SSMR_CROP_RULES_PATH` can point to a JSON array of rules. Every rule must include crop, region, season, water availability, one or more measurement thresholds, source title, source URL, and applicability notes. Measurement names must be one of `soil_moisture`, `soil_temperature`, `ph`, or `ec`; units must match the scan payload exactly. The engine will not silently convert units.

The rule engine reports whether a scan matches the supplied thresholds, not a yield forecast or guarantee of suitability. It does not infer N-P-K values from pH or EC. Have a qualified agricultural source/reviewer validate rule values and applicability before using them in the field.
