# Contributing to MinerU-GLMBridge

Thanks for your interest in contributing! Bug reports, feature ideas and pull
requests are all welcome. Please keep contributions compatible with the dual
[AGPL-3.0](LICENSE) / [commercial](COMMERCIAL.md) licensing.

## Reporting bugs / requesting features

1. Open an [Issue](https://github.com/SpiralQWQ/mineru-glm-bridge/issues).
2. Choose the matching template (`bug_report` / `feature_request`).
3. For bugs, include: command + full logs (minus any tokens/keys), expected vs
   actual behavior, and OS/Python versions.

## Development setup

```bash
git clone https://github.com/SpiralQWQ/mineru-glm-bridge.git
cd mineru-glm-bridge
pip install -r requirements.txt   # consider a virtualenv
```

All configuration is environment-based (see README):

- `MGB_ROOT` / `MGB_TOOLS` — workspace / tool paths
- `MGB_PROXY_PORT` — proxy listen port
- `MGB_HEARTBEAT` / `MGB_PROXY_USAGE_LOG` — heartbeat & usage log knobs
- GLM credentials — always via environment variables, never hardcoded

## Running the tests / self-check

```bash
python -m py_compile glm_mineru_proxy.py mineru_local_batch.py watchdog.py
```

## Submitting a pull request

1. Fork the repo and create a branch from `master`.
2. Make focused, minimal changes; keep code style consistent with the existing
   scripts (environment variables over hardcoded paths, `***`-masked secrets).
3. Run the self-check above and make sure `git status` is clean of stray files.
4. Open a PR against `master` using the `PULL_REQUEST_TEMPLATE`.

## License

By contributing, you agree that your contributions are licensed under the
project's dual license (AGPL-3.0 + commercial). See [LICENSE](LICENSE) and
[COMMERCIAL.md](COMMERCIAL.md).
