# CLAUDE.md — Project Context for Claude Code

## Project

Germany electricity price forecasting portfolio project. Forecasts 24h day-ahead hourly prices using SMARD market data and Open-Meteo weather data.

## Stack

- Python with `uv` for package management
- GCS as raw data lake, BigQuery as analytical warehouse
- dbt for transformation layer
- marimo for notebooks
- FastAPI for REST API
- Docker for containerization of the API

## Conventions

- Always load `.env` using `python-dotenv` before reading environment variables
- Use `logging` not `print` statements
- GCS bucket name comes from `GCS_BUCKET_NAME` env var, GCP project from `GCP_PROJECT_ID`
- Before creating any marimo notebook, read `.claude/skills/marimo-notebook/SKILL.md`

## Project Structure

```
ingestion/smard/        # SMARD ingestion scripts
ingestion/open_meteo/   # Open-Meteo ingestion scripts
ingestion/utils/        # Shared data loading and parsing utilities
dbt/                    # dbt transformation layer
notebooks/              # marimo notebooks
modeling/               # forecasting models
api/                    # FastAPI REST API
docker/                 # Docker configuration
```

## Raw Data Layout in GCS

| Source | Path | Format |
|---|---|---|
| SMARD | `smard/raw/{filter_code}/{filter_code}_{timestamp_ms}.json` | `{"series": [[timestamp_ms, value], ...]}` |
| Open-Meteo | `open_meteo/forecast/{location_name}/{year}.json` | `{"hourly": {"time": [...], "variable": [...]}}` |

## Key Data Facts

- SMARD timestamps are UTC milliseconds
- Open-Meteo timestamps are ISO8601 UTC strings
- Prices are in EUR/MWh (filter 4169)
- Generation and consumption values are in MW
- All data starts from 2022-04-01 (approximately — first full chunk may start April 4)

## SMARD Filter Codes

| Filter | Series |
|---|---|
| 4169 | Price: Germany/Luxembourg |
| 1223 | Generation: Lignite |
| 1224 | Generation: Nuclear |
| 1225 | Generation: Wind Offshore |
| 1226 | Generation: Hydro |
| 1227 | Generation: Other Conventional |
| 1228 | Generation: Other Renewables |
| 4066 | Generation: Biomass |
| 4067 | Generation: Wind Onshore |
| 4068 | Generation: Solar |
| 4069 | Generation: Hard Coal |
| 4070 | Generation: Pumped Storage Generation |
| 4071 | Generation: Natural Gas |
| 410  | Consumption: Total (Grid Load) |
| 4359 | Consumption: Residual Load |
| 4387 | Consumption: Pumped Storage Consumption |

## Open-Meteo Locations

| Name | Latitude | Longitude |
|---|---|---|
| north | 54.0 | 9.9 |
| central | 51.2 | 10.4 |
| south | 48.5 | 10.0 |
