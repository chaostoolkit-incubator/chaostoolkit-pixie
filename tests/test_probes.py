# -*- coding: utf-8 -*-
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

from chaospixie.probes import run_script, run_script_from_local_file

PXL_SCRIPT = """
import px
df = px.DataFrame('http_events')[['resp_status','req_path']]
df = df.head(10)
px.display(df, 'http_table')
"""


@patch("chaospixie.pxapi.Client", autospec=True)
def test_run_script(client: MagicMock):
    c = {"pixie_cluster_id": "cluster"}
    s = {"api_key": "secret"}
    assert run_script(PXL_SCRIPT, "http_table", c, s) == []


@patch("chaospixie.pxapi.Client", autospec=True)
def test_run_script_from_file(client: MagicMock):
    c = {"pixie_cluster_id": "cluster"}
    s = {"api_key": "secret"}
    with NamedTemporaryFile() as f:
        f.write(PXL_SCRIPT.encode("utf-8"))
        f.seek(0)
        assert run_script_from_local_file(f.name, "http_table", c, s) == []
