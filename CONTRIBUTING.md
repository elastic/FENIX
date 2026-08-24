# Contributing to FENIX

FENIX is a **lab-only** fileless-execution PoC for detection engineering on systems you own.

This tree is published as a **snapshot**, not an officially supported Elastic product. It is not under active development; there is no CI. **GitHub issues and pull requests are not accepted.**

This project follows the [Elastic Community Code of Conduct](CODE_OF_CONDUCT.md).

## Lab setup

```bash
git clone https://github.com/elastic/fenix.git && cd fenix
make all
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
export FENIX_BIN_DIR=$PWD/bin
fenix check
```

Install from a clone (`pip install -e .`). FENIX is not published to PyPI. Use a **Linux VM** for helpers, `lkm-load`, and `fenix run-all`.

## License

Apache License 2.0, except `payloads/hello_lkm/hello_lkm.c` which is GPL-2.0-only. See [LICENSE](LICENSE) and [licenses/](licenses/).

## Out of scope

Persistence, ptrace/process injection, eBPF rootkits, C2, SIEM/detection rule content, privilege escalation, and default upload to third-party file hosts.
