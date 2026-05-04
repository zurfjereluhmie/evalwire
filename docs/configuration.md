# Configuration Reference

evalwire can be driven entirely from a `evalwire.toml` file at the root of your project. CLI flags always take precedence over config file values, which take precedence over hardcoded defaults.

## Precedence

```
CLI flag  >  evalwire.toml  >  hardcoded default
```

## Example file

```toml
[dataset]
csv_path   = "data/testset.csv"
on_exist   = "skip"
input_keys = ["user_query"]
output_keys = ["expected_output"]
tag_column = "tags"
delimiter  = "|"

[experiments]
dir         = "experiments"
prefix      = "eval"
concurrency = 4
```

## `[dataset]` section

Used by `evalwire upload`.

| Key | Type | Default | Description |
|---|---|---|---|
| `csv_path` | string | none (required) | Path to the CSV testset file. |
| `on_exist` | `"skip"` / `"overwrite"` / `"append"` | `"skip"` | How to handle a dataset that already exists in Phoenix. |
| `input_keys` | list of strings | `["user_query"]` | CSV column names treated as example inputs. |
| `output_keys` | list of strings | `["expected_output"]` | CSV column names treated as expected outputs. |
| `tag_column` | string | `"tags"` | CSV column used to split rows into separate datasets. |
| `delimiter` | string | `"\|"` | Character used to assign a row to multiple datasets. |

### `on_exist` modes

| Value | Behaviour |
|---|---|
| `skip` | Leave the existing dataset untouched. |
| `overwrite` | Delete the existing dataset and re-create it from the CSV. |
| `append` | Add the new rows to the existing dataset. |

## `[experiments]` section

Used by `evalwire run`.

| Key | Type | Default | Description |
|---|---|---|---|
| `dir` | string | `"experiments"` | Path to the experiments directory. |
| `prefix` | string | `"eval"` | Prefix prepended to every experiment name in Phoenix. |
| `concurrency` | integer | `1` | Number of experiments to run in parallel. |

## `[phoenix]` section

Reserved for future use. Currently read by `get_phoenix_config()` but not consumed by the CLI.

## CLI flag reference

### `evalwire upload`

| Flag | Config key | Default |
|---|---|---|
| `--csv PATH` | `dataset.csv_path` | none |
| `--on-exist MODE` | `dataset.on_exist` | `skip` |
| `--input-keys COLS` | `dataset.input_keys` | `user_query` |
| `--output-keys COLS` | `dataset.output_keys` | `expected_output` |
| `--tag-column COL` | `dataset.tag_column` | `tags` |
| `--delimiter CHAR` | `dataset.delimiter` | `\|` |
| `--config PATH` | n/a | `./evalwire.toml` |

### `evalwire run`

| Flag | Config key | Default |
|---|---|---|
| `--experiments PATH` | `experiments.dir` | `experiments` |
| `--name NAME` | n/a | all experiments |
| `--prefix PREFIX` | `experiments.prefix` | `eval` |
| `--concurrency N` | `experiments.concurrency` | `1` |
| `--dry-run [N]` | n/a | off |
| `--config PATH` | n/a | `./evalwire.toml` |

`--name` is repeatable: `evalwire run --name es_search --name source_router`.

`--dry-run` runs the task but does not upload results to Phoenix. Optionally accepts a number to limit the run to the first N examples per dataset.
