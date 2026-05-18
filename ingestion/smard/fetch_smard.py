"""Fetch raw SMARD hourly data chunks and store them in GCS."""

import logging
import os
import time

import requests
from dotenv import load_dotenv
from google.cloud import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

SMARD_BASE = "https://www.smard.de/app/chart_data"
REGION = "DE"
RESOLUTION = "hour"
START_MS = 1648771200000  # 2022-04-01 00:00:00 UTC

FILTERS: dict[int, str] = {
    4169: "price_germany_luxembourg",
    1223: "generation_lignite",
    1224: "generation_nuclear",
    1225: "generation_wind_offshore",
    1226: "generation_hydro",
    1227: "generation_other_conventional",
    1228: "generation_other_renewables",
    4066: "generation_biomass",
    4067: "generation_wind_onshore",
    4068: "generation_solar",
    4069: "generation_hard_coal",
    4070: "generation_pumped_storage",
    4071: "generation_natural_gas",
    410:  "consumption_total",
    4359: "consumption_residual_load",
    4387: "consumption_pumped_storage",
}


def gcs_path(filter_code: int, timestamp: int) -> str:
    return f"smard/raw/{filter_code}/{filter_code}_{timestamp}.json"


def blob_exists(bucket: storage.Bucket, path: str) -> bool:
    return bucket.blob(path).exists()


def fetch_index(session: requests.Session, filter_code: int) -> list[int]:
    url = f"{SMARD_BASE}/{filter_code}/{REGION}/index_{RESOLUTION}.json"
    response = session.get(url)
    response.raise_for_status()
    timestamps: list[int] = response.json().get("timestamps", [])
    return [ts for ts in timestamps if ts >= START_MS]


def fetch_chunk(session: requests.Session, filter_code: int, timestamp: int) -> bytes:
    url = f"{SMARD_BASE}/{filter_code}/{REGION}/{filter_code}_{REGION}_{RESOLUTION}_{timestamp}.json"
    response = session.get(url)
    response.raise_for_status()
    return response.content


def run() -> None:
    load_dotenv()
    bucket_name = os.environ["GCS_BUCKET_NAME"]
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    session = requests.Session()

    for filter_code, name in FILTERS.items():
        log.info("Processing filter %s (%s)", filter_code, name)

        timestamps = fetch_index(session, filter_code)
        log.info("  %d qualifying timestamps for %s", len(timestamps), name)
        time.sleep(0.5)

        uploaded = 0
        skipped = 0

        for timestamp in timestamps:
            path = gcs_path(filter_code, timestamp)

            if blob_exists(bucket, path):
                skipped += 1
                continue

            chunk = fetch_chunk(session, filter_code, timestamp)
            bucket.blob(path).upload_from_string(chunk, content_type="application/json")
            log.info("  Stored %s", path)
            uploaded += 1
            time.sleep(0.5)

        log.info(
            "  Done %s: %d uploaded, %d skipped", name, uploaded, skipped
        )


if __name__ == "__main__":
    run()
