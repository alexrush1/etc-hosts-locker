#!/usr/bin/env python3
import argparse
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 8)
if sys.version_info < MIN_PYTHON:
    sys.exit(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required.")

HOSTS_DICTIONARY = "servers"
ETC_HOSTS_FILE = "/etc/hosts"
ETC_HOSTS_FILE_BACKUP = "/etc/hosts.backup"
ZEROED_IP = "0.0.0.0"
ZEROED_IPV6 = "::1"

DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(message)s", level=level)


def is_valid_domain(domain: str) -> bool:
    return bool(DOMAIN_RE.match(domain))


def get_dictionary(file=None) -> set:
    dictionary_file = file if file else HOSTS_DICTIONARY
    path = Path(dictionary_file)
    if not path.exists():
        logger.error(f"Dictionary file not found: {dictionary_file}")
        sys.exit(1)

    domains = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        domain = line.strip()
        if not domain or domain.startswith("#"):
            continue
        if not is_valid_domain(domain):
            logger.warning(f"Skipping invalid domain: {domain!r}")
            continue
        domains.add(domain)
    return domains


def check_root():
    if os.geteuid() != 0:
        logger.error("Root privileges required. Try with sudo.")
        sys.exit(1)


def backup():
    try:
        shutil.copy(ETC_HOSTS_FILE, ETC_HOSTS_FILE_BACKUP)
        logger.info(f"Backup created: {ETC_HOSTS_FILE_BACKUP}")
    except OSError as e:
        logger.error(f"Failed to create backup: {e}")
        sys.exit(1)


def read_hosts_file() -> list:
    try:
        with open(ETC_HOSTS_FILE, "r", encoding="utf-8") as f:
            return f.readlines()
    except OSError as e:
        logger.error(f"Failed to read {ETC_HOSTS_FILE}: {e}")
        sys.exit(1)


def write_hosts_file(lines: list, dry_run: bool = False):
    if dry_run:
        logger.info("[dry-run] Would write the following to %s:", ETC_HOSTS_FILE)
        for line in lines:
            logger.info(line.rstrip())
        return
    try:
        with open(ETC_HOSTS_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        logger.info(f"File {ETC_HOSTS_FILE} was changed!")
    except OSError as e:
        logger.error(f"Failed to write {ETC_HOSTS_FILE}: {e}")
        sys.exit(1)


def _run(cmd: list):
    """Run a command without sudo (already root), log debug info, suppress failures."""
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.debug("Command failed (exit %d): %s", result.returncode, result.stderr.strip())


def flush_dns():
    system = platform.system()
    logger.info("Flushing DNS cache...")
    try:
        if system == "Linux":
            _run(["systemd-resolve", "--flush-caches"])
            _run(["systemctl", "restart", "nscd"])
        elif system == "Darwin":
            _run(["dscacheutil", "-flushcache"])
            _run(["killall", "-HUP", "mDNSResponder"])
        else:
            logger.warning("Unknown operating system. DNS flush skipped.")
    except Exception as e:
        logger.warning("Exception while flushing DNS: %s", e)


def _parse_hosts_line(line: str):
    """Return (ip, [domains]) from a hosts line, or None if not a data line."""
    clean = line.split("#", 1)[0].strip()
    if not clean:
        return None
    parts = clean.split()
    if len(parts) < 2:
        return None
    return parts[0], parts[1:]


def block(file=None, domain=None, dry_run: bool = False, ipv6: bool = False):
    if file:
        dictionary = get_dictionary(file)
    else:
        if not is_valid_domain(domain):
            logger.error(f"Invalid domain: {domain!r}")
            sys.exit(1)
        dictionary = {domain}

    hosts_lines = read_hosts_file()

    already_blocked = set()
    for line in hosts_lines:
        parsed = _parse_hosts_line(line)
        if parsed:
            already_blocked.update(parsed[1])

    new_lines = hosts_lines.copy()
    added = []

    for d in sorted(dictionary):
        if d not in already_blocked:
            new_lines.append(f"{ZEROED_IP} {d}\n")
            if ipv6:
                new_lines.append(f"{ZEROED_IPV6} {d}\n")
            added.append(d)
            logger.debug("Blocking: %s", d)
        else:
            logger.debug("Already blocked, skipping: %s", d)

    if added:
        logger.info("Blocking %d domain(s): %s", len(added), ", ".join(added))
        write_hosts_file(new_lines, dry_run=dry_run)
        if not dry_run:
            flush_dns()
    else:
        logger.info("All specified domains are already blocked.")


def unblock(file=None, domain=None, dry_run: bool = False):
    if file:
        dictionary = get_dictionary(file)
    else:
        if not is_valid_domain(domain):
            logger.error(f"Invalid domain: {domain!r}")
            sys.exit(1)
        dictionary = {domain}

    hosts_lines = read_hosts_file()
    new_lines = []
    removed = []

    for line in hosts_lines:
        parsed = _parse_hosts_line(line)
        if parsed is None:
            new_lines.append(line)
            continue

        ip, domains = parsed
        remaining = [d for d in domains if d not in dictionary]
        removed.extend([d for d in domains if d in dictionary])

        if remaining:
            comment = ""
            if "#" in line:
                comment = " #" + line.split("#", 1)[1].rstrip()
            new_lines.append(f"{ip} {' '.join(remaining)}{comment}\n")
            logger.debug("Kept on line: %s", remaining)
        else:
            logger.debug("Removing line: %s", line.rstrip())

    if removed:
        logger.info("Unblocking %d domain(s): %s", len(removed), ", ".join(removed))
        write_hosts_file(new_lines, dry_run=dry_run)
        if not dry_run:
            flush_dns()
    else:
        logger.info("None of the specified domains were blocked.")


def blocked_list():
    hosts_lines = read_hosts_file()
    blocked = []

    for line in hosts_lines:
        parsed = _parse_hosts_line(line)
        if parsed and parsed[0] in (ZEROED_IP, ZEROED_IPV6, "127.0.0.1"):
            blocked.extend(parsed[1])

    if blocked:
        print("Blocked domains:\n")
        for d in blocked:
            print(d)
    else:
        print("No blocked domains right now.")


def parse_args():
    parser = argparse.ArgumentParser(description="Manage domain blocking via /etc/hosts")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for cmd in ("block", "unblock"):
        p = subparsers.add_parser(cmd, help=f"{cmd.capitalize()} domains")
        p.add_argument("--domain", help="Single domain to target")
        p.add_argument("--file", help="File with list of domains (one per line)")
        p.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without modifying /etc/hosts"
        )
        if cmd == "block":
            p.add_argument(
                "--ipv6",
                action="store_true",
                help="Also add an IPv6 (::1) block entry for each domain"
            )

    subparsers.add_parser("list", help="Show all blocked domains")
    return parser.parse_args()


def check_args(args):
    if args.command in ("block", "unblock"):
        if args.file is None and args.domain is None:
            print("No file or domain specified. Use --file or --domain.")
            sys.exit(1)


def menu():
    args = parse_args()
    setup_logging(getattr(args, "verbose", False))
    check_args(args)

    if args.command in ("block", "unblock"):
        check_root()
        backup()
        dry_run = getattr(args, "dry_run", False)
        if args.command == "block":
            block(args.file, args.domain, dry_run=dry_run, ipv6=getattr(args, "ipv6", False))
        else:
            unblock(args.file, args.domain, dry_run=dry_run)
    elif args.command == "list":
        blocked_list()


if __name__ == "__main__":
    menu()
