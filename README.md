# Chaos Toolkit Extension for the Pixie/eBPF platform

[![Version](https://img.shields.io/pypi/v/chaostoolkit-pixie.svg)](https://img.shields.io/pypi/v/chaostoolkit-pixie.svg)
[![License](https://img.shields.io/pypi/l/chaostoolkit-pixie.svg)](https://img.shields.io/pypi/l/chaostoolkit-pixie.svg)

![Build](https://github.com/chaostoolkit-incubator/chaostoolkit-pixie/workflows/Build/badge.svg)
[![codecov](https://codecov.io/gh/chaostoolkit-incubator/chaostoolkit-pixie/branch/master/graph/badge.svg)](https://codecov.io/gh/chaostoolkit-incubator/chaostoolkit-pixie)
[![Python versions](https://img.shields.io/pypi/pyversions/chaostoolkit-pixie.svg)](https://www.python.org/)

This extension allows you to run [Pixie](https://px.dev/) script during your
experiments.

## Install

This package requires Python 3.8+ as Pixie's dependency requires it.

To be used from your experiment, this package must be installed in the Python
environment where [chaostoolkit][] already lives.

[chaostoolkit]: https://github.com/chaostoolkit/chaostoolkit

```
$ pip install chaostoolkit-pixie
```

## Usage

This extension provides two probes to run Pixie scripts, either directly
embedded into the experiment or in a file local to the experiment.

For instance, a complete script:

```json
{
    "version": "1.0.0",
    "title": "Consumer service remains fast under higher traffic load",
    "description": "Showcase for how we remain responsive under a certain load. This should help us figure how many replicas we should run",
    "secrets": {
        "pixie": {
            "api_key": {
                "type": "env",
                "key": "PIXIE_API_KEY"
            }
        }
    },
    "configuration": {
        "pixie_cluster_id": {
            "type": "env",
            "key": "PIXIE_CLUSTER_ID"
        }
    },
    "steady-state-hypothesis": {
        "title": "Run a Pixie script and evaluate it",
        "probes": [
            {
                "type": "probe",
                "name": "p99-latency-of-consumer-service-for-past-2m-remained-under-300ms",
                "tolerance": {
                    "type": "probe",
                    "name": "compute-median",
                    "provider": {
                        "type": "python",
                        "module": "chaospixie.tolerances",
                        "func": "percentile_should_be_below",
                        "secrets": ["pixie"],
                        "arguments": {
                            "column": "latency_p99",
                            "percentile": 99,
                            "convert_from_nanoseconds": "milliseconds",
                            "treshold": 300.0
                        }
                    }
                },
                "provider": {
                    "type": "python",
                    "module": "chaospixie.probes",
                    "func": "run_script_from_local_file",
                    "secrets": ["pixie"],
                    "arguments": {
                        "script_path": "./pixiescript.py"
                    }
                }
            }
        ]
    },
    "method": [
        {
            "type": "action",
            "name": "send-10-requests-per-second-for-60s",
            "provider": {
                "type": "process",
                "path": "ddosify",
                "arguments": "-d 60 -n 600 -o stdout-json -t http://mydomain.com/consumer"
            }
        }
    ]
}
```

This assumes you have a a service named `consumer`. Pixie monitors its
latency and produces percentiles for it. We then use a probe tolerance to
evaluate the returned latency for the past 2 minutes and we measure if the
latency was mainly (99-percentile) under 300ms.

In this example, we use [ddosify](https://github.com/ddosify/ddosify) to
induce the load, but you can use your favourite tooling of course.

The Pixie script we run is as follows:

```python
import px

ns_per_ms = 1000 * 1000
ns_per_s = 1000 * ns_per_ms
window_ns = px.DurationNanos(10 * ns_per_s)
filter_unresolved_inbound = True
filter_health_checks = True
filter_ready_checks = True


def inbound_let_timeseries(start_time: str, service: px.Service):
    ''' Compute the let as a timeseries for requests received by `service`.

    Args:
    @start_time: The timestamp of data to start at.
    @service: The name of the service to filter on.

    '''
    df = let_helper(start_time)
    df = df[px.has_service_name(df.service, service)]

    df = df.groupby(['timestamp']).agg(
        latency_quantiles=('latency', px.quantiles),
        error_rate_per_window=('failure', px.mean),
        throughput_total=('latency', px.count),
        bytes_total=('resp_body_size', px.sum)
    )

    # Format the result of LET aggregates into proper scalar formats and
    # time series.
    df.latency_p50 = px.DurationNanos(px.floor(px.pluck_float64(df.latency_quantiles, 'p50')))
    df.latency_p90 = px.DurationNanos(px.floor(px.pluck_float64(df.latency_quantiles, 'p90')))
    df.latency_p99 = px.DurationNanos(px.floor(px.pluck_float64(df.latency_quantiles, 'p99')))
    df.request_throughput = df.throughput_total / window_ns
    df.errors_per_ns = df.error_rate_per_window * df.request_throughput / px.DurationNanos(1)
    df.error_rate = px.Percent(df.error_rate_per_window)
    df.bytes_per_ns = df.bytes_total / window_ns
    df.time_ = df.timestamp

    return df[['time_', 'latency_p50', 'latency_p90', 'latency_p99',
               'request_throughput', 'errors_per_ns', 'error_rate', 'bytes_per_ns']]


def let_helper(start_time: str):
    ''' Compute the initial part of the let for requests.
        Filtering to inbound/outbound traffic by service is done by the calling function.

    Args:
    @start_time: The timestamp of data to start at.

    '''
    df = px.DataFrame(table='http_events', start_time=start_time)
    # Filter only to inbound service traffic (server-side).
    # Don't include traffic initiated by this service to an external location.
    df = df[df.trace_role == 2]
    df.service = df.ctx['service']
    df.pod = df.ctx['pod']
    df.latency = df.latency

    df.timestamp = px.bin(df.time_, window_ns)

    df.failure = df.resp_status >= 400
    filter_out_conds = ((df.req_path != '/healthz' or not filter_health_checks) and (
        df.req_path != '/readyz' or not filter_ready_checks)) and (
        df['remote_addr'] != '-' or not filter_unresolved_inbound)

    df = df[filter_out_conds]
    return df


df = inbound_let_timeseries("-2m", "default/consumer")
px.display(df)
```

This is an abridged script from Pixie itself.

That's it!

## Configuration

<Specify any extra configuration your extension relies on here>

## Test

To run the tests for the project execute the following:

```
$ pytest
```

### Formatting and Linting

We use a combination of [`black`][black], [`flake8`][flake8], and [`isort`][isort]
to both lint and format this repositories code.

[black]: https://github.com/psf/black
[flake8]: https://github.com/PyCQA/flake8
[isort]: https://github.com/PyCQA/isort

Before raising a Pull Request, we recommend you run formatting against your
code with:

```console
$ make format
```

This will automatically format any code that doesn't adhere to the formatting
standards.

As some things are not picked up by the formatting, we also recommend you run:

```console
$ make lint
```

To ensure that any unused import statements/strings that are too long, etc.
are also picked up.

## Contribute

If you wish to contribute more functions to this package, you are more than
welcome to do so. Please, fork this project, make your changes following the
usual [PEP 8][pep8] code style, sprinkling with tests and submit a PR for
review.

[pep8]: https://pycodestyle.readthedocs.io/en/latest/
