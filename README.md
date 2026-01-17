# etc-hosts-locker

Small Python script to block or unblock domains from a list using `/etc/hosts`.

> **Important:**  
> This script performs a **simple local domain blocking** by redirecting domains to `0.0.0.0` via `/etc/hosts`.  
> It **does NOT bypass governmental, ISP, DNS, DPI, or network-level restrictions**.  
> This is **not a censorship circumvention tool**, only a local hosts-based blocker.

## Example

#### Block domain
```bash
~ ❯ ./etc-hosts-locker.py block --file="servers"
```
#### Unblock domain
```bash
~ ❯ ./etc-hosts-locker.py unblock --file="servers"
```
#### Currently blocked domains
```bash
~ ❯ ./etc-hosts-locker.py list
```

## Requirements

- Python **3.8+**
- Linux / macOS / Windows
- **Root / Administrator privileges** (required to modify `/etc/hosts`)

### Commands
* block - Block all domains from file
* unblock - Unblock all domains from file
* list - Show currently blocked domains

### How it works

The script reads a list of domains from a text file (one domain per line) and:
- **block** — adds entries like: 0.0.0.0 example.com to `/etc/hosts`
- **unblock** — removes those entries
- **list** — shows currently blocked domains

Automatically:
- **create backup** — creates a backup of `/etc/hosts` to `/etc/hosts.backup`
- **flushes DNS cache** so changes apply immediately

Blocking is done by redirecting domains to `0.0.0.0`.

⚠️ Requires root/administrator privileges to modify /etc/hosts.