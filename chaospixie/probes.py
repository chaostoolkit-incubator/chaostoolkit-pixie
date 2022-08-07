# -*- coding: utf-8 -*-
from typing import Any, Dict, List

from chaoslib.types import Configuration, Secrets

from chaospixie import connect, execute_script, load_script_from_file

__all__ = ["run_script", "run_script_from_local_file"]


def run_script(
    script: str,
    table_name: str = "output",
    configuration: Configuration = None,
    secrets: Secrets = None,
) -> str:
    """
    Run a Pixie script.

    Make sure to provide the name of the table you want to fetch data for.
    Usually it's the name given to the `px.display()` function in your script.
    """
    c = connect(configuration, secrets)
    return execute_script(c, script, table_name)


def run_script_from_local_file(
    script_path: str,
    table_name: str = "output",
    configuration: Configuration = None,
    secrets: Secrets = None,
) -> List[Dict[str, Any]]:
    """
    Run a Pixie script loaded from a local file.

    Make sure to provide the name of the table you want to fetch data for.
    Usually it's the name given to the `px.display()` function in your script.
    """
    s = load_script_from_file(script_path)
    return run_script(s, table_name, configuration, secrets)
