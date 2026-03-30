# Changelog

## [0.2.1](https://github.com/zurfjereluhmie/evalwire/compare/v0.2.0...v0.2.1) (2026-03-30)


### Bug Fixes

* wrap async tasks for sync Phoenix client ([#5](https://github.com/zurfjereluhmie/evalwire/issues/5)) ([9d370cc](https://github.com/zurfjereluhmie/evalwire/commit/9d370cc1c4a24a7721ddfc1274be0e123553594e))

## [0.2.0](https://github.com/zurfjereluhmie/evalwire/compare/v0.1.0...v0.2.0) (2026-03-30)


### Features

* add pytest and pytest-mock to dev dependencies ([6e55a38](https://github.com/zurfjereluhmie/evalwire/commit/6e55a38365324bce8937a5470d99ad5978e38cdb))
* add runtime dependencies, extras, and CLI entry point ([a97d4f6](https://github.com/zurfjereluhmie/evalwire/commit/a97d4f6420213cc63b24a241e8d586b2b8887334))
* **demo:** auto-load .env via python-dotenv in run.py ([2e996b1](https://github.com/zurfjereluhmie/evalwire/commit/2e996b1594dbcc300905dafd9ae1ae07a5f693f0))
* expose public API in package __init__ ([c8828ce](https://github.com/zurfjereluhmie/evalwire/commit/c8828ce6487b94787b567dff23fe700b28179dd8))
* implement built-in evaluators (top_k and membership) ([d819763](https://github.com/zurfjereluhmie/evalwire/commit/d8197634cdfb1ed2b511147bf6972af957e23e3a))
* implement CLI upload and run commands ([241d614](https://github.com/zurfjereluhmie/evalwire/commit/241d614e172598e4aa5cc3337d8062a07434e081))
* implement DatasetUploader ([c2f587f](https://github.com/zurfjereluhmie/evalwire/commit/c2f587fbbc34aaccc2a1717852f9ac7c59866278))
* implement ExperimentRunner with auto-discovery ([b2cba1d](https://github.com/zurfjereluhmie/evalwire/commit/b2cba1dd61c9a6491d183ae15af4f9cbcca7db05))
* implement LangGraph node isolation helpers ([2f7c62a](https://github.com/zurfjereluhmie/evalwire/commit/2f7c62a68980d5048618668d90978e02e052d708))
* implement setup_observability ([3b9d67a](https://github.com/zurfjereluhmie/evalwire/commit/3b9d67a3bb29472111a6bca5423fb1a3701553e7))
* implement TOML config loader ([b877f2f](https://github.com/zurfjereluhmie/evalwire/commit/b877f2f8e0a0b288d8f63828b08eb296383ab36b))
* initialize project structure with essential files and configurations ([668cbff](https://github.com/zurfjereluhmie/evalwire/commit/668cbfff7f4a6a689f9a57233dbfca3541a26c9b))
* replace demo/requirements.txt with demo dependency-group in pyproject.toml ([3c3b67e](https://github.com/zurfjereluhmie/evalwire/commit/3c3b67ef7be2ac9483546a20954552e4942889e9))
* **runner:** implement concurrency via ThreadPoolExecutor and auto-create __init__.py ([763c53c](https://github.com/zurfjereluhmie/evalwire/commit/763c53c29caf9e3693661878622b70ac7f3bca4d))


### Bug Fixes

* align uploader and runner to phoenix.Client flat API (&gt;=13) ([b768011](https://github.com/zurfjereluhmie/evalwire/commit/b768011e10732b838f8ff4a4ad5e299468dedde9))
* **ci:** suppress unresolved-import for test_task_async.py in ty.toml ([1ae7cbc](https://github.com/zurfjereluhmie/evalwire/commit/1ae7cbce388f2c56b37e2ab49bab601011c77ad8))
* **error-handling:** log exc_info on swallowed exceptions in uploader and runner ([b82475a](https://github.com/zurfjereluhmie/evalwire/commit/b82475a86d3741c64bd241e84a4b49b51c4a9c8b))
* **evaluators:** guard top_k against None output when task failed ([a4b96d8](https://github.com/zurfjereluhmie/evalwire/commit/a4b96d854da0cf0da19939fe8323136aaec6da6d))
* **langgraph:** annotate build_subgraph return type as CompiledStateGraph via TYPE_CHECKING ([f512d54](https://github.com/zurfjereluhmie/evalwire/commit/f512d54fe8e92728cb8130b409425a6461ff8002))
* **runner:** switch to client.experiments.run_experiment namespaced API ([5eb8e63](https://github.com/zurfjereluhmie/evalwire/commit/5eb8e637df7d2f5d3b1b5c06ae437e864a7c07cb))
* **types:** resolve all ty type errors across package and tests ([c0314df](https://github.com/zurfjereluhmie/evalwire/commit/c0314df476efb80b04dceeafec24b11f8dc9d509))
* **typing:** annotate setup_observability return as TracerProvider and tighten dict types ([0bc67a3](https://github.com/zurfjereluhmie/evalwire/commit/0bc67a3226bebd04298889b2d658c17b98350d17))
* **uploader:** switch to client.datasets.* namespaced API and fix overwrite delete step ([f51d6d8](https://github.com/zurfjereluhmie/evalwire/commit/f51d6d8153b94a2f2717ae6788bc70e86d921dd0))
* **uploader:** use explicit list defaults for input_keys and output_keys ([b71280d](https://github.com/zurfjereluhmie/evalwire/commit/b71280d205c3e0d35c81be08264252457b0da7ee))
* **uploader:** use real Phoenix 13.x API and type phoenix_client as Client ([7b7b465](https://github.com/zurfjereluhmie/evalwire/commit/7b7b4658c21a68f47bc1561aa4b3ec1fe7824764))
* use is_string_dtype to support pandas 3.x StringDtype in _load_csv ([01c17ed](https://github.com/zurfjereluhmie/evalwire/commit/01c17ed398be86fe832cf42b09c2e038fe2ab563))


### Documentation

* add lazy-import comment to _make_client and export build_subgraph/invoke_node ([519a7b4](https://github.com/zurfjereluhmie/evalwire/commit/519a7b4a72263db51e615fe45fbf80fdebe96c45))
* add MkDocs setup with Material theme, mkdocstrings, and make targets ([5bfd1a2](https://github.com/zurfjereluhmie/evalwire/commit/5bfd1a235fd2ce581ad58698ca129b97c9b76da8))
* write README and quick-start guide ([f21a259](https://github.com/zurfjereluhmie/evalwire/commit/f21a25990eb09ac3b6d4c3b6390bedf13e49a27a))
