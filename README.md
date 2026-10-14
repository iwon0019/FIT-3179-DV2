# The Air We Share

A static Vega-Lite website for FIT3179 Data Visualisation 2.

**Author:** Ivan Wong Shao Hou · **Student ID:** 35170018

## Open locally

Serve the repository root using a static HTTP server (opening `index.html` with `file://` will prevent data loading):

```powershell
python -m http.server 8765 --bind 127.0.0.1
```

Then open http://127.0.0.1:8765/ . No npm install or build is needed to view the finished site. Pinned Vega 5.30.0, Vega-Lite 5.20.1 and Vega-Embed 6.26.0 are included in `assets/vendor/` so the page does not depend on a CDN at runtime.

## Publish on GitHub Pages

1. Create a public GitHub repository.
2. Upload `index.html`, `.nojekyll`, `assets/`, `specs/`, `data/site/`, and the linked `data/prepared/README.md` and `data/prepared/validation_report.json`. Keep the directory structure intact. All chart URLs are relative and work under a repository subpath.
3. Include source/build scripts and attribution documents in the repository for reproducibility. Raw downloads and local QA screenshots do not need to be served by the webpage.
4. In repository Settings → Pages, choose **Deploy from a branch**, select your branch and **/(root)**, then save.
5. Verify the resulting public URL, every chart, and the readable JSON specifications. Add your own scanned hand-drawn sketch and include its public URL in the assignment submission.

No GitHub repository has been created or published by this task. A local preview is not a public submission URL.

## Structure

- `index.html`: narrative, controls, sources, authorship and AI acknowledgement.
- `assets/style.css`: responsive layout and visual design.
- `assets/app.js`: embeds the twelve specifications and coordinates year, location and episode selections.
- `specs/`: one readable Vega-Lite JSON specification per chart.
- `data/site/`: lightweight browser data, about 1.75 MB in total. Data files with no active chart reference are retained for inspection but are not automatically requested.
- `data/prepared/`: cleaned source tables and methodology.
- `scripts/prepare_data.py`: preparation from untouched raw downloads.
- `scripts/build_website.py`: produces website datasets and chart specifications.
- `scripts/check_charts.cjs`: executes all twelve charts using the bundled libraries and checks marks, filters and expected record counts.

## Rebuild and check

Python preparation/build scripts require pandas, numpy and openpyxl. Do not rerun preparation unless the raw inputs or cleaning method change. It deliberately includes unresolved-source notes in the data guide.

```powershell
python scripts/build_website.py
node scripts/check_charts.cjs
node --check assets/app.js
```

The test writes `output/qa/chart-checks.json`. Browser QA additionally checks year selection, location selection, episode inputs/reset, timeline brushing and responsive layout. Changing data requires rechecking narrative numbers in `index.html`, not just rebuilding the charts.

## Chart inventory

| # | Idiom | Input |
|---|---|---|
| 01 | Line chart | National monitoring, 2018–2024 |
| 02 | Grouped bar chart | WHO urban/rural exposure, 2017–2023 |
| 03 | **Slope chart** | Location annual PM2.5, 2024 and 2025 |
| 04 | **Proportional-symbol map** | Location annual PM2.5 |
| 05 | **Heatmap** | Location monthly PM2.5 |
| 06 | **Jitter plot** | Daily PM2.5, horizontal jitter only |
| 07 | Scatterplot | Daily weather and PM2.5 |
| 08 | **Radial bar chart** | Monthly precipitation |
| 09 | Column timeline | Daily retained hotspot detections |
| 10 | **Choropleth map** | Detections per 1,000 km² |
| 11 | **Dot map** | Hotspots in a selected episode |
| 12 | **Spatial-bin map** | Annual counts per 0.25° cell |

There are 12 charts, four distinct map idioms and eight advanced idioms (maps included). Chart 12 sits beside chart 10 before the full-width episode map for readability. The revised sketch's basic narrative and chart selection are preserved.

## Interpretation

The location dataset is modelled, not city-wide observed monitoring. Eight named locations are included; one unconfirmed location is excluded. Weather is available for seven. Main comparisons use complete years 2024–2025. State fire densities use approximate spherical boundary area, not official land-area statistics. Fire detections are not unique fire events or proof of a pollution source. The source export does not resolve NASA's historic fire-type processing-version caveat. See `data/prepared/README.md` for source links, units, confidence filtering and boundary limitations.

## Third-party libraries

Vega, Vega-Lite and Vega-Embed are BSD-3-Clause software. Their license files are included in `assets/vendor/`. Geographic boundaries retain their original ODbL attribution; the site does not relicense source data. See the on-page sources and data guide.

## Rubric review

See `output/assignment/rubric-audit.md` for the requirement review. Public hosting, sketch verification and submission documents remain outstanding. DM Serif Display is bundled under `assets/fonts/OFL.txt`.
