# -*- coding: utf-8 -*-
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import pxapi
from chaoslib.discovery.discover import (
    discover_probes,
    initialize_discovery_result,
)
from chaoslib.exceptions import ActivityFailed, InvalidExperiment
from chaoslib.types import (
    Configuration,
    DiscoveredActivities,
    Discovery,
    Secrets,
)
from logzero import logger

__version__ = "0.1.0"
__all__ = ["connect", "discover", "execute_script"]


def connect(configuration: Configuration, secrets: Secrets) -> pxapi.Conn:
    """
    Connect the client to the Pixie server. The following keys can be set:

    * configuration key `pixie_cluster_id` or the `PIXIE_CLUSTER_ID` env var
    * secret key `api_key` or the `PIXIE_API_KEY` env var
    * configuration key `px_server_url` or the `PIXIE_SERVER_URL` env var,
      which uses the default Pixie saas server endpoint
    """
    auth = get_auth(configuration, secrets)

    px_client = pxapi.Client(
        token=auth["px_key"],
        server_url=auth["px_server_url"],
        use_encryption=False,
    )
    conn = px_client.connect_to_cluster(auth["px_cluster_id"])

    return conn


def execute_script(
    conn: pxapi.Conn, script: str, table_name: str
) -> List[Dict[str, Any]]:
    """
    Executes the script synchronously and read the given table for rows of
    results.
    """
    logger.debug(f"Running Pixie script:\n{script}")

    s = conn.prepare_script(script)
    r = []
    for idx, e in enumerate(s.results(table_name)):
        e = serialize_row(e)
        handle_timestamp(e)
        r.append(e)

    logger.debug(f"Pixie script returned: {r}")

    return r


def discover(discover_system: bool = True) -> Discovery:  # pragma: no cover
    """
    Discover Kubernetes capabilities offered by this extension.
    """
    logger.info("Discovering capabilities from chaostoolkit-pixie")

    discovery = initialize_discovery_result(
        "chaostoolkit-pixie", __version__, "pixie"
    )
    discovery["activities"].extend(load_exported_activities())
    return discovery


###############################################################################
# Private functions
###############################################################################
def load_exported_activities() -> List[
    DiscoveredActivities
]:  # pragma: no cover
    """
    Extract metadata from actions and probes exposed by this extension.
    """
    activities = []
    activities.extend(discover_probes("chaospixie.probes"))


def get_auth(configuration: Configuration, secrets: Secrets) -> Dict[str, str]:
    configuration = configuration or {}
    secrets = secrets or {}

    px_cluster_id = os.getenv(
        "PIXIE_CLUSTER_ID", configuration.get("pixie_cluster_id")
    )
    px_key = os.getenv("PIXIE_API_KEY", secrets.get("api_key"))

    if not px_cluster_id:
        raise InvalidExperiment(
            "missing the Pixie cluster id. Set it either in the configuration "
            "as `pixie_cluster_id` or via the PIXIE_CLUSTER_ID environment "
            "variable."
        )

    if not px_key:
        raise InvalidExperiment(
            "missing the Pixie API key. Set it either in the secrets "
            "as `px_key` or via the PIXIE_API_KEY environment variable."
        )

    px_server_url = os.getenv(
        "PIXIE_SERVER_URL",
        configuration.get("px_server_url", pxapi.client.DEFAULT_PIXIE_URL),
    )

    return {
        "px_cluster_id": px_cluster_id,
        "px_key": px_key,
        "px_server_url": px_server_url,
    }


def load_script_from_file(script_path: str) -> str:
    """
    Read the Pixie script from the given local file.
    """
    p = Path(script_path)
    if not p.exists():
        raise ActivityFailed(f"'{script_path} is not a valid path")

    return p.read_text("utf-8")


def serialize_row(row: pxapi.data.Row) -> Dict[str, Any]:
    """
    Serialize a Pixie row into a dictionary of native types.
    """
    out = {}
    for i, c in enumerate(row._data):
        out[row.relation.get_col_name(i)] = encode(c)
    return out


def handle_timestamp(r: pxapi.data.Row) -> None:
    """
    Add an entry with any found timestamp from nanoseconds to a Python
    datetime object (to the microseconds as Python cannot do better).

    Merely convenience.
    """
    if "time_" in r:
        r["_dt"] = encode(nanotime_to_datetime(r["time_"]))
    elif "create_time" in r:
        r["_dt"] = encode(nanotime_to_datetime(r["create_time"]))
    elif "start_time" in r:
        r["_dt"] = encode(nanotime_to_datetime(r["start_time"]))


def nanotime_to_datetime(nano: int) -> datetime:
    """
    Convert a timestamp in nanoseconds to a Python UTC datetime object,
    down to the microseconds only.
    """
    # we can't better than microseconds with Python datetimes
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(
        microseconds=nano / 1000.0
    )


def encode(o: object) -> Any:
    """
    The results will be serialized to json by Chaos Toolkit, so let's ensure
    some of the types don't break this process by encoding to native types
    ourselves.
    """
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    elif isinstance(o, uuid.UUID):
        return str(o)

    return o
