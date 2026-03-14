# etc-hosts-locker

Small Python script to block or unblock domains from a list using `/etc/hosts`.

> **Important:**
> This script performs a **simple local domain blocking** by redirecting domains to `0.0.0.0` via `/etc/hosts`.
> It **does NOT bypass governmental, ISP, DNS, DPI, or network-level restrictions**.
> This is **not a censorship circumvention tool**, only a local hosts-based blocker.

## Requirements

- Python **3.8+**
- Linux / macOS
- **Root / Administrator privileges** (required to modify `/etc/hosts`)

## Usage

#### Block domains from file
```bash
sudo ./etc-hosts-locker.py block --file servers
```

#### Block a single domain
```bash
sudo ./etc-hosts-locker.py block --domain example.com
```

#### Block with IPv6 entries too
```bash
sudo ./etc-hosts-locker.py block --domain example.com --ipv6
```

#### Preview changes without applying (dry-run)
```bash
sudo ./etc-hosts-locker.py block --file servers --dry-run
```

#### Unblock domains from file
```bash
sudo ./etc-hosts-locker.py unblock --file servers
```

#### Unblock a single domain
```bash
sudo ./etc-hosts-locker.py unblock --domain example.com
```

#### Show currently blocked domains
```bash
sudo ./etc-hosts-locker.py list
```

#### Verbose output
```bash
sudo ./etc-hosts-locker.py -v block --file servers
```

## Commands

| Command | Description |
|---------|-------------|
| `block` | Block domains from file or single domain |
| `unblock` | Unblock domains from file or single domain |
| `list` | Show currently blocked domains |

## Options

| Option | Commands | Description |
|--------|----------|-------------|
| `--file FILE` | block, unblock | File with domain list (one per line, `#` comments supported) |
| `--domain DOMAIN` | block, unblock | Single domain to target |
| `--dry-run` | block, unblock | Preview changes without writing to `/etc/hosts` |
| `--ipv6` | block | Also add `::1` IPv6 block entries |
| `-v / --verbose` | all | Enable verbose/debug output |

## How it works

The script reads a list of domains from a text file (one domain per line) and:
- **block** — adds entries like `0.0.0.0 example.com` to `/etc/hosts`
- **unblock** — removes those entries
- **list** — shows currently blocked domains

Automatically:
- **validates** domain names before writing
- **creates a backup** of `/etc/hosts` to `/etc/hosts.backup`
- **flushes the DNS cache** so changes apply immediately

Blocking is done by redirecting domains to `0.0.0.0` (and optionally `::1` for IPv6).

⚠️ Requires root/administrator privileges to modify /etc/hosts.

---

## Changelog

### v0.2.0 — 2026-03-14

#### Bug Fixes
- **Fixed false positives in `block()`**: replaced unsafe substring search (`domain in line`) with proper hosts-line parsing, preventing `example.com` from matching `notexample.com`
- **Fixed multi-domain line handling in `unblock()`**: lines like `0.0.0.0 domain1 domain2` are now correctly handled — only matching domains are removed; remaining ones are preserved on the same line
- **Removed redundant `sudo` calls in `flush_dns()`**: the script already requires root, calling sudo internally was unnecessary and could fail in some environments

#### New Features
- **Domain validation**: all domains are validated against an RFC-compliant regex before processing; invalid entries are skipped with a warning
- **`--dry-run` mode**: preview exactly what would be written to `/etc/hosts` without making any changes
- **`--ipv6` flag** (block command): optionally adds `::1` IPv6 block entries alongside IPv4 `0.0.0.0`
- **`-v / --verbose` flag**: enables debug-level output for detailed operation logging
- **Comment support in domain files**: lines starting with `#` in the domains file are now ignored
- **Python version check**: script exits with a clear message if run on Python < 3.8

#### Improvements
- **Error handling**: all file I/O operations are wrapped in `try/except` with clear error messages
- **Fixed `list` command crash**: `check_args()` no longer tries to access `--file`/`--domain` for the `list` subcommand
- **`list` command now shows IPv6 blocks** (`::1`) alongside IPv4
- **Informative output**: reports how many domains were blocked/unblocked and which ones; warns when all domains are already in the desired state

### v0.0.1 — Initial release

- Basic block / unblock / list functionality via `/etc/hosts`
- Backup creation before modifications
- DNS cache flushing on Linux and macOS
- `--file` and `--domain` flags
