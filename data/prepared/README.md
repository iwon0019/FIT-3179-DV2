# Prepared air quality and environmental data

These files are ready for Vega/Vega-Lite. The source downloads in the parent folder remain unchanged. Rebuild with `scripts/prepare_data.py` using Python with pandas, numpy and openpyxl.

## Scope and sources

The main analysis covers **1 January 2024 through 31 December 2025**, two complete years with matching pollution, weather and archived hotspot coverage. Longer national series are retained as separate context. Current conditions, future forecasts, partial 2026 data and the near-real-time fire file are not included in the main outputs. This is an intentional comparison window, not a claim that 2025 is the latest observation available.

| Data | Source documentation | Interpretation |
|---|---|---|
| Location PM2.5 and PM10 | https://open-meteo.com/en/docs/air-quality-api | CAMS model estimates near the supplied coordinates, not station observations. Global grid is approximately 45 km. Source CSV does not contain the original request URL/model selection. |
| Weather | https://open-meteo.com/en/docs/historical-weather-api | Exported weather estimates. Exact requested model is not recorded in the CSV; retain the original request URL if available. |
| National pollution | https://data.gov.my/data-catalogue/air_pollution | National monthly monitoring summary, with pollutant-specific units. |
| WHO SDGPM25 | https://www.who.int/data/gho/data/indicators/indicator-details/GHO/concentrations-of-fine-particulate-matter-%28pm2-5%29 | Population-weighted modelled annual exposure, distinct from the other two pollution sources. |
| Fire hotspots | https://firms.modaps.eosdis.nasa.gov/download/ | S-NPP archive; repeated detections are not separate fire events. |
| State boundaries | https://www.geoboundaries.org/api/current/gbOpen/MYS/ADM1/ | geoBoundaries MYS ADM1; supplied metadata describes 2017 boundaries, sourced from OpenStreetMap/Wambacher under ODbL 1.0. |

Credit Open-Meteo and its underlying CAMS/weather providers, NASA FIRMS, WHO, DOE/DOSM and geoBoundaries/OpenStreetMap as appropriate. Check each provider's terms when publishing. Source documentation URLs identify the datasets, but do not substitute for missing request parameters.

## Files and uses

| File | Use and row grain |
|---|---|
| `locations.csv` | One row per air-quality grid location. Canonical location keys, labels, coordinates and weather mapping. |
| `location_daily.csv` | One location per local date. Daily pollution and matched weather. Use for box plots, histograms, daily heatmaps and scatterplots. |
| `location_monthly.csv` | One location per month. Use for seasonal heatmaps and time series. |
| `location_annual.csv` | One location per year with map coordinates. Use for proportional-symbol maps and annual comparisons. |
| `wind_rose.csv` | Location, 100 m wind direction sector and speed band. Pre-aggregated frequency and mean coincident hourly PM2.5. |
| `national_pollution_monthly.csv` | Month and pollutant. All six pollutants retained; filter `pollutant == 'PM2.5'` for the main story. |
| `who_residence_annual.csv` | Year and residence category, Malaysia 2017–2023. |
| `fire_points.csv` | One retained hotspot detection. For selected-episode dot maps. |
| `fire_daily.csv` | One local date; national count of retained detections. |
| `fire_state_annual.csv` | State and year; detections, detections per 1,000 km², high-confidence share and mean radiative power. |
| `fire_spatial_bins.csv` | Year and 0.25-degree rectangular cell. Counts, cell corners, centre coordinates and mean radiative power. |
| `fire_spatial_bins.geojson` | The same bins as polygon features, directly usable with `format.property: 'features'`. Filter by year. |
| `malaysia_states.geojson` | State polygons with `state_code` and `state_name` properties. |
| `validation_report.json` | Row counts, source SHA-256 hashes, checks and file sizes. |

Use `location_key` for location joins, `date` for daily joins, and `state_code` for state-to-boundary joins. In Vega-Lite a GeoJSON state's key is `properties.state_code`. Dates are ISO strings; parse as temporal fields. Empty numeric cells mean unavailable, never zero. Parse numeric CSV fields as numbers.

## Locations and exclusions

Original location IDs are local to each download and must not be joined directly. Weather IDs were matched to the nearest air-quality coordinate, with a 15 km maximum and unique matches. The grid separation is retained. Slight coordinate differences reflect different grid locations; they are not treated as identical sensors.

Labels ending in `area` are inferred from coordinates, not verified source city labels. `L05` (4.4 N, 101.1 E) has no confirmed city name and must be excluded from named-city comparisons using `include_in_city_comparisons == true`. It remains in the prepared files for traceability. Do not rename it Kota Bharu. `L01` and `L05` lack weather; their weather values remain blank. Seven matched locations can be used immediately for weather comparisons.

`location_annual.csv` includes the comparison flag directly. Other location files require a lookup from `locations.csv`. Coordinates are the source model grid coordinates, not city-centre coordinates.

## Calculations and units

- PM columns ending `_ugm3` are micrograms per cubic metre. Daily means use 24 valid hourly records; all main-period days pass this check. `pm25_max_hourly_ugm3` is the maximum hourly value in that day, not a daily average.
- Monthly/annual PM means use equally weighted daily means. `pm25_p95_daily_ugm3` is the 95th percentile of daily averages, not hourly values. `days`, `valid_hours` and `weather_days` document record coverage, not independent monitoring completeness.
- Daily temperature and wind speeds are means of hourly records. Temperature extrema are hourly minima/maxima. Precipitation is summed over the day/month. Rain and precipitation were not added together. The daily precipitation sums reconcile to the source daily export within floating-point tolerance.
- Local air/weather timestamps have UTC+8 offset. The source timezone label is Asia/Singapore, which has the same offset for this period. Fire UTC acquisition timestamps were shifted by eight hours BEFORE filtering and aggregating to Malaysian calendar dates. This makes retained year counts differ slightly from raw UTC-year counts.
- Wind roses use 16 centred compass sectors and matching **100 m** direction and speed. Speed bands are [0,1), [1,5), [5,10), [10,20), [20,infinity) km/h. `percent_hours` uses all matched hours for that location as denominator. Show the 0–<1 km/h band as calm separately where possible; direction in calm conditions is not informative. Directions describe where wind comes from, not confirmed smoke trajectories. Mean PM is calculated from simultaneous modelled values.
- National gaseous pollutants use ppm; PM uses ug/m3. Do not put them on one shared concentration axis without a justified transformation. National PM2.5 is entirely missing in 2017; usable monthly PM2.5 begins in 2018. Missing rows remain explicit.
- WHO categories overlap: Total, Urban, Rural, Cities and Towns must not be summed or used as a stacked composition. Bounds are retained without assuming an undocumented confidence level. Do not merge WHO annual estimates with the national monitoring series as one continuous measurement series.

## Fire filtering and mapping

For the main local-time period there are 18,260 archived detections before filtering. We retain **12,948** records labelled `type == 0` (presumed vegetation fire) with nominal or high confidence (`n`/`h`). No interpolation, event deduplication or causal attribution is performed. Static land sources, offshore types and low-confidence records are excluded. These remain in the untouched originals.

NASA reports a historic Type-field issue in monthly Collection-2 products (https://firms.modaps.eosdis.nasa.gov/web-services/). The CSV's `version` field alone does not establish the monthly processing revision. Use wording such as **nominal/high-confidence hotspots classified as presumed vegetation fires** until product provenance is verified. Do not describe the data as confirmed wildfire events or as a complete count of all fires.

Point-in-polygon assignment uses the supplied simplified state polygons, including holes. **69** retained points do not match a polygon; their `state_code` is `UNASSIGNED`. They are retained in points, bins, daily totals and a separate annual summary row, but cannot be drawn as a state choropleth. Coastal simplification and source-area selection can both contribute to unmatched points. No nearest-state assignment was invented.

State annual tables include zero-detection state-years. Zero means no retained detections in this file, not verified absence of fire; clouds, satellite gaps and sampling affect detection. `mean_frp_mw` is mean instantaneous fire radiative power in megawatts, not cumulative energy or emissions. `high_confidence_percent` is undefined where detections are zero.

`boundary_area_km2` is calculated from the supplied simplified polygons, subtracting holes, on a sphere of radius 6,371.0088 km. It is an approximate geometric denominator, not an official land-area statistic. `detections_per_1000_km2` divides annual retained detections by this area and multiplies by 1,000. It is suitable for a labelled density choropleth but does not adjust for cloud cover, satellite sampling or vegetation area. Both fields are blank for UNASSIGNED points.

Spatial bins are 0.25-degree latitude/longitude cells. Their counts are **not detections per square kilometre**, since angular cells have different physical areas. No smoothing or invented PM surface is supplied.

## Suggested 12-chart plan

These are data-supported options, not a guarantee that a rubric rewards every design. Give each map a different question and scale; avoid repeating similar charts to inflate the count.

1. Proportional-symbol map: annual PM2.5 near the eight named locations (`location_annual.csv`, comparison flag true).
2. Choropleth: annual retained hotspot detections per 1,000 km² (`fire_state_annual.csv` + boundaries). Explain that this shows detection density, not PM2.5 or the number of distinct fires.
3. Dot map: individual retained hotspots for a selected high-PM episode (`fire_points.csv`).
4. Spatial-bin map: broad annual hotspot concentration (`fire_spatial_bins.geojson`).
5. Heatmap: location by month PM2.5 (`location_monthly.csv`).
6. Jitter plot: daily PM2.5 distributions by location (`location_daily.csv`); jitter horizontally within each location only.
7. Slope chart: annual PM2.5 change by location from 2024 to 2025 (`location_annual.csv`); omit the unconfirmed location.
8. Radial bar chart: monthly rainfall around the calendar (`location_monthly.csv`, `precipitation_mm`); select one matched location and one year.
9. National monthly PM2.5 line chart (`national_pollution_monthly.csv`).
10. Annual urban/rural exposure comparison (`who_residence_annual.csv`).
11. Daily rainfall versus PM2.5 scatterplot for matched locations (`location_daily.csv`).
12. Daily hotspot timeline, annotated alongside pollution episodes (`fire_daily.csv`).

The first four are map idioms; the next four are advanced non-map idioms from the user's specified list. The sketch orders these charts into narrative sections, so its chart numbers differ from this inventory. Wind-rose data remains available but is not used by the revised sketch. A PM2.5 spike and nearby hotspot are an association, not proof of transport or cause. The data does not support a Malaysian state-average PM2.5 choropleth, regional Indonesian-fire attribution, or city-wide observed-monitor claims.

## Delivery size and validation

Prepared CSV and GeoJSON files total about **1.98 MB** before compression. Load only the files each chart needs; the CSV and GeoJSON bin files are alternative encodings of the same data. Keep raw downloads out of webpage requests.

Validation checks include unique location/time keys, complete 24-hour daily coverage, missing and negative pollutant checks, unique coordinate matching, independent precipitation-total reconciliation, wind-frequency totals, and reconciliation of point, daily, state and spatial-bin fire counts. No source data values were fabricated or filled. The website now contains twelve rendered Vega-Lite charts. See `output/qa/chart-checks.json` for execution checks.
