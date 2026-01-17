#!/usr/bin/env python3
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HOSTS_DICTIONARY = "servers"
ETC_HOSTS_FILE = "/etc/hosts"
ETC_HOSTS_FILE_BACKUP = "/etc/hosts.backup"
ZEROED_IP = "0.0.0.0"


def get_dictionary(file=None) -> set:
    dictionary_file = file if file else HOSTS_DICTIONARY
    path = Path(dictionary_file)
    if not path.exists():
        print(f"Dictionary file not found: {dictionary_file}")
        sys.exit(1)

    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def check_root():
    if os.geteuid() != 0:
        print("Root privileges required. Try with sudo.")
        sys.exit(1)


def backup():
    shutil.copy(ETC_HOSTS_FILE, ETC_HOSTS_FILE_BACKUP)
    print(f"Backup created: {ETC_HOSTS_FILE_BACKUP}")


def read_hosts_file() -> list:
    with open(ETC_HOSTS_FILE, "r", encoding="utf-8") as f:
        return f.readlines()


def write_hosts_file(lines: list):
    with open(ETC_HOSTS_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"File {ETC_HOSTS_FILE} was changed!")


def flush_dns():
    system = platform.system()
    try:
        if system == "Linux":
            subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], check=False)
            subprocess.run(["sudo", "systemctl", "restart", "nscd"], check=False)
        elif system == "Darwin":
            subprocess.run(["sudo", "dscacheutil", "-flushcache"], check=False)
            subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], check=False)
        else:
            print("Unknown operating system. DNS Flush skipped")
    except Exception as e:
        print("Exception while DNS Flushing:", e)


def block(file=None, domain=None):
    if file:
        dictionary = get_dictionary(file)
    else:
        dictionary = [domain]

    hosts_lines = read_hosts_file()
    new_lines = hosts_lines.copy()

    for domain in dictionary:
        if not any(domain in l for l in hosts_lines):
            new_lines.append(f"{ZEROED_IP} {domain}\n")

    write_hosts_file(new_lines)
    flush_dns()


def unblock(file=None, domain=None):
    if file:
        dictionary = get_dictionary(file)
    else:
        dictionary = [domain]

    hosts_lines = read_hosts_file()
    new_lines = []

    for line in hosts_lines:
        clean_line = line.split("#", 1)[0].strip()
        if not clean_line:
            new_lines.append(line)
            continue

        parts = clean_line.split()
        if len(parts) < 2:
            new_lines.append(line)
            continue

        ip, domain = parts
        if not domain in dictionary:
            new_lines.append(line)

    write_hosts_file(new_lines)
    flush_dns()


def blocked_list():
    hosts_lines = read_hosts_file()
    blocked = []

    for line in hosts_lines:
        clean_line = line.split("#", 1)[0].strip()
        if not clean_line:
            continue
        parts = clean_line.split()
        if len(parts) >= 2 and parts[0] == ZEROED_IP:
            blocked.extend(parts[1:])

    if blocked:
        print("Blocked domains:\n")
        for domain in blocked:
            print(domain)
    else:
        print("No blocked domains right now.")


def parse_args():
    parser = argparse.ArgumentParser(description="Manage domain blocking via /etc/hosts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    block_parser = subparsers.add_parser("block", help="Block domains from the list")
    block_parser.add_argument(
        "--domain",
        help="Domain to target lock without list"
    )
    block_parser.add_argument(
        "--file",
        help="File with the list of domains to apply (if not specified, the --domain option is waiting)"
    )

    unblock_parser = subparsers.add_parser("unblock", help="Unblock domains from the list")
    unblock_parser.add_argument(
        "--domain",
        help="Domain to target lock without list"
    )
    unblock_parser.add_argument(
        "--file",
        help="File with the list of domains to apply (if not specified, the --domain option is waiting)"
    )

    subparsers.add_parser("list", help="Show all blocked domains")
    return parser.parse_args()

def check_args(args):
    if args.file is None and args.domain is None:
        print("No file or domain specified")
        sys.exit(1)


actions = {
    "block": block,
    "unblock": unblock,
    "list": blocked_list
}


def menu():
    args = parse_args()
    check_args(args)

    if args.command in ["block", "unblock"]:
        check_root()
        backup()

    action = actions.get(args.command)
    if action:
        action(args.file, args.domain)
    else:
        print("Chosen action not found")


if __name__ == '__main__':
    menu()
