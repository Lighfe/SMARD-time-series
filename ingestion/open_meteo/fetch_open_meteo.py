"""Fetch historical forecast weather data from Open-Meteo and store it in GCS."""

import logging
import os
import time
from datetime import date

import requests
from dotenv import load_dotenv
from google.cloud import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
START_YEAR = 2022
FIRST_YEAR_START = "2022-04-01"

LOCATIONS = [
    {"name": "north",   "latitude": 54.0, "longitude": 9.9},
    {"name": "central", "latitude": 51.2, "longitude": 10.4},
    {"name": "south",   "latitude": 48.5, "longitude": 10.0},
]

VARIABLES = [
    "temperature_2m",
    "wind_speed_100m",
    "wind_direction_100m",
    "shortwave_radiation",
    "cloud_cover",
    "precipitation",
]


def gcs_path(location_name: str, year: int) -> str:
    return f"open_meteo/forecast/{location_name}/{year}.json"


def blob_exists(bucket: storage.Bucket, path: str) -> bool:
    return bucket.blob(path).exists()


def fetch_year(
    session: requests.Session,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> bytes:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(VARIABLES),
        "models": "icon_global",
        "timezone": "UTC",
    }
    response = session.get(OPEN_METEO_URL, params=params)
    response.raise_for_status()
    return response.content


def run() -> None:
    load_dotenv()
    bucket_name = os.environ["GCS_BUCKET_NAME"]
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    session = requests.Session()
    today = date.today()
    current_year = today.year

    for location in LOCATIONS:
        name = location["name"]
        lat = location["latitude"]
        lon = location["longitude"]
        log.info("Processing location: %s (lat=%.1f, lon=%.1f)", name, lat, lon)

        uploaded = 0
        skipped = 0

        for year in range(START_YEAR, current_year + 1):
            path = gcs_path(name, year)

            if blob_exists(bucket, path):
                log.info("  Skipping %s (already exists)", path)
                skipped += 1
                continue

            start_date = FIRST_YEAR_START if year == START_YEAR else f"{year}-01-01"
            end_date = today.isoformat() if year == current_year else f"{year}-12-31"

            log.info("  Fetching %s: %s → %s", path, start_date, end_date)
            data = fetch_year(session, lat, lon, start_date, end_date)
            bucket.blob(path).upload_from_string(data, content_type="application/json")
            log.info("  Stored %s (%d bytes)", path, len(data))
            uploaded += 1
            time.sleep(1)

        log.info("  Done %s: %d uploaded, %d skipped", name, uploaded, skipped)


if __name__ == "__main__":
    run()
