# evalwire.uploader

`DatasetUploader` reads a CSV testset and uploads it to Arize Phoenix as one named dataset per unique tag value. It handles three conflict modes (`skip`, `overwrite`, `append`) and supports multi-tag rows via a configurable delimiter.

## Basic usage

```python
from phoenix.client import Client
from evalwire.uploader import DatasetUploader

client = Client()

uploader = DatasetUploader(
    csv_path="data/testset.csv",
    phoenix_client=client,
)
datasets = uploader.upload(on_exist="skip")
print(datasets)  # {"es_search": <Dataset>, "source_router": <Dataset>}
```

## CSV format

The CSV must contain at least a tag column, one input column, and one expected-output column:

```csv
user_query,expected_output,tags
"find cycling paths","url-a | url-b","es_search | source_router"
"find parks","url-c","es_search"
```

Pipe-delimited values in any column are split into lists. A row with `tags = "es_search | source_router"` is added to both datasets.

## Conflict modes

| `on_exist` | Behaviour |
|---|---|
| `"skip"` | Do nothing if the dataset already exists. |
| `"overwrite"` | Delete the existing dataset and re-create it. |
| `"append"` | Call `add_examples_to_dataset` on the existing dataset. If not found, create it. |

## Pitfalls

- Phoenix raises `ValueError` (not a Phoenix-specific exception) when `get_dataset` is called for a non-existent dataset. evalwire catches this and creates the dataset instead.
- There is no official delete method in the Phoenix Python client. evalwire calls the REST endpoint `DELETE /v1/datasets/{id}` directly for the `overwrite` mode.
- Creating a dataset with a name that already exists returns a 409 Conflict error, not a new version. Use `on_exist="overwrite"` to replace it.

## See also

- [Configuration Reference](../configuration.md) for `evalwire.toml` keys
- [CLI Reference](cli.md) for `evalwire upload`

---

::: evalwire.uploader
