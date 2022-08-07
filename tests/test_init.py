# -*- coding: utf-8 -*-
import uuid
from datetime import datetime
from tempfile import NamedTemporaryFile
from time import time
from unittest.mock import MagicMock, patch

import pxapi
import pytest
from chaoslib.exceptions import ActivityFailed, InvalidExperiment

from chaospixie import (
    encode,
    execute_script,
    get_auth,
    handle_timestamp,
    load_script_from_file,
    nanotime_to_datetime,
    serialize_row,
)

PXL_SCRIPT = """
import px
df = px.DataFrame('http_events')[['resp_status','req_path']]
df = df.head(10)
px.display(df, 'http_table')
"""


def test_get_auth_expects_cluster_id():
    with pytest.raises(InvalidExperiment):
        get_auth({}, {"api_key": "secret"})


def test_get_auth_expects_api_key():
    with pytest.raises(InvalidExperiment):
        get_auth({"pixie_cluster_id": "abc"}, {})


def test_load_script_from_file_requires_realfile():
    with pytest.raises(ActivityFailed):
        load_script_from_file("blah.py")


def test_load_script_from_file():
    with NamedTemporaryFile() as f:
        f.write(PXL_SCRIPT.encode("utf-8"))
        f.seek(0)
        assert load_script_from_file(f.name) == PXL_SCRIPT


def test_serialize_row():
    r = MagicMock()
    r.columns = [
        MagicMock(column_name="cola", column_type=2),
        MagicMock(column_name="colb", column_type=2),
        MagicMock(column_name="colc", column_type=5),
    ]

    tableA = pxapi.data._TableStream(
        "a", relation=pxapi.data._Relation(r), subscribed=False
    )
    row = pxapi.data.Row(tableA, [1, 2, "three"])

    assert serialize_row(row) == {"cola": 1, "colb": 2, "colc": "three"}


def test_handle_time_():
    r = MagicMock()
    r.columns = [
        MagicMock(column_name="cola", column_type=2),
        MagicMock(column_name="colb", column_type=2),
        MagicMock(column_name="time_", column_type=6),
    ]

    tableA = pxapi.data._TableStream(
        "a", relation=pxapi.data._Relation(r), subscribed=False
    )
    row = pxapi.data.Row(tableA, [1, 2, int(time()) / 1e9])

    row = serialize_row(row)
    handle_timestamp(row)
    assert "_dt" in row


def test_handle_create_time():
    r = MagicMock()
    r.columns = [
        MagicMock(column_name="cola", column_type=2),
        MagicMock(column_name="colb", column_type=2),
        MagicMock(column_name="create_time", column_type=6),
    ]

    tableA = pxapi.data._TableStream(
        "a", relation=pxapi.data._Relation(r), subscribed=False
    )
    row = pxapi.data.Row(tableA, [1, 2, int(time()) / 1e9])

    row = serialize_row(row)
    handle_timestamp(row)
    assert "_dt" in row


def test_handle_start_time():
    r = MagicMock()
    r.columns = [
        MagicMock(column_name="cola", column_type=2),
        MagicMock(column_name="colb", column_type=2),
        MagicMock(column_name="start_time", column_type=6),
    ]

    tableA = pxapi.data._TableStream(
        "a", relation=pxapi.data._Relation(r), subscribed=False
    )
    row = pxapi.data.Row(tableA, [1, 2, int(time()) / 1e9])

    row = serialize_row(row)
    handle_timestamp(row)
    assert "_dt" in row


def test_encode_datetime():
    d = datetime.utcnow()
    i = d.isoformat()
    assert encode(d) == i


def test_encode_uuid():
    u = uuid.uuid4()
    assert encode(u) == str(u)


def test_nanotime_to_datetime():
    n = int(time()) * 1.0e9
    d = datetime.now()

    nanotime_to_datetime(n) == d


@patch("chaospixie.pxapi.Client", autospec=True)
def test_execute_script(client: MagicMock):
    c = MagicMock()
    s = MagicMock()
    c.prepare_script.return_value = s

    r = MagicMock()
    r.columns = [
        MagicMock(column_name="cola", column_type=2),
        MagicMock(column_name="colb", column_type=2),
        MagicMock(column_name="start_time", column_type=6),
    ]

    tableA = pxapi.data._TableStream(
        "a", relation=pxapi.data._Relation(r), subscribed=False
    )
    row = pxapi.data.Row(tableA, [1, 2, int(time()) / 1e9])

    s.results.return_value = [row]

    execute_script(c, PXL_SCRIPT, "http_table")
