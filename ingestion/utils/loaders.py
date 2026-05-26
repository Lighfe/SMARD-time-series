"""Load raw GCS data into pandas DataFrames."""

import json
import logging
from pathlib import Path

import pandas as pd
from google.cloud import storage

log = logging.getLogger(__name__)

OPEN_METEO_VARIABLES = [
    "temperature_2m",
    "wind_speed_100m",
    "wind_direction_100m",
    "shortwave_radiation",
    "cloud_cover",
    "precipitation",
]


def _fetch_blob(blob: storage.Blob, local_path: Path) -> bytes:
    """Return blob bytes from local cache if present, otherwise download and cache."""
    if local_path.exists():
        log.debug("  Reading from cache: %s", local_path)
        return local_path.read_bytes()
    log.debug("  Downloading from GCS: %s", blob.name)
    data = blob.download_as_bytes()
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(data)
    return data


def load_smard(
    bucket: storage.Bucket,
    filter_code: int,
    cache_dir: str = "data/raw",
) -> pd.DataFrame:
    """Return all chunks for a SMARD filter as a sorted, null-free DataFrame.

    Columns: timestamp (UTC, datetime64[ns, UTC]), value (float).
    Chunks are cached locally under {cache_dir}/smard/{filter_code}/.
    """
    prefix = f"smard/raw/{filter_code}/"
    blobs = list(bucket.list_blobs(prefix=prefix))
    log.info("Loading SMARD filter %d: %d chunk files", filter_code, len(blobs))

    frames: list[pd.DataFrame] = []
    for blob in blobs:
        filename = blob.name.split("/")[-1]
        local_path = Path(cache_dir) / "smard" / str(filter_code) / filename
        raw = json.loads(_fetch_blob(blob, local_path))
        series = raw.get("series", [])
        if not series:
            log.debug("  Empty series in %s, skipping", blob.name)
            continue
        df = pd.DataFrame(series, columns=["timestamp", "value"])
        frames.append(df)

    if not frames:
        log.warning("No data found for SMARD filter %d", filter_code)
        return pd.DataFrame(columns=["timestamp", "value"])

    combined = pd.concat(frames, ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], unit="ms", utc=True)
    combined = (
        combined.dropna(subset=["value"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    log.info("  Loaded %d rows for filter %d", len(combined), filter_code)
    return combined


def load_open_meteo(
    bucket: storage.Bucket,
    location: str,
    cache_dir: str = "data/raw",
) -> pd.DataFrame:
    """Return all years for an Open-Meteo location as a sorted DataFrame.

    Columns: timestamp (UTC, datetime64[ns, UTC]), temperature_2m,
    wind_speed_100m, wind_direction_100m, shortwave_radiation,
    cloud_cover, precipitation.
    Files are cached locally under {cache_dir}/open_meteo/{location}/.
    """
    prefix = f"open_meteo/forecast/{location}/"
    blobs = list(bucket.list_blobs(prefix=prefix))
    log.info("Loading Open-Meteo location '%s': %d year files", location, len(blobs))

    frames: list[pd.DataFrame] = []
    for blob in blobs:
        filename = blob.name.split("/")[-1]
        local_path = Path(cache_dir) / "open_meteo" / location / filename
        raw = json.loads(_fetch_blob(blob, local_path))
        hourly = raw.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            log.debug("  Empty hourly data in %s, skipping", blob.name)
            continue
        data = {"timestamp": times}
        for var in OPEN_METEO_VARIABLES:
            data[var] = hourly.get(var, [None] * len(times))
        frames.append(pd.DataFrame(data))

    if not frames:
        log.warning("No data found for Open-Meteo location '%s'", location)
        cols = ["timestamp"] + OPEN_METEO_VARIABLES
        return pd.DataFrame(columns=cols)

    combined = pd.concat(frames, ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True)
    combined = combined.sort_values("timestamp").reset_index(drop=True)
    log.info("  Loaded %d rows for location '%s'", len(combined), location)
    return combined
