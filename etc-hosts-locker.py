#!/usr/bin/env python3
import subprocess
import platform
import argparse
import os
import shutil
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
        print(f"Файл справочника не найден: {dictionary_file}")
        sys.exit(1)

    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def check_root():
    if os.geteuid() != 0:
        print("Данный скрипт требует root-права. Запусти через sudo.")
        sys.exit(1)


def backup():
    shutil.copy(ETC_HOSTS_FILE, ETC_HOSTS_FILE_BACKUP)
    print(f"Создана резервная копия: {ETC_HOSTS_FILE_BACKUP}")


def read_hosts_file() -> list:
    with open(ETC_HOSTS_FILE, "r", encoding="utf-8") as f:
        return f.readlines()


def write_hosts_file(lines: list):
    with open(ETC_HOSTS_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Изменения успешно записаны в {ETC_HOSTS_FILE}")

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
            print("Неизвестная ОС, DNS кеш не очищен")
    except Exception as e:
        print("Ошибка при попытке очистить DNS кеш:", e)

def block(file=None):
    dictionary = get_dictionary(file)
    hosts_lines = read_hosts_file()
    new_lines = hosts_lines.copy()

    for domain in dictionary:
        if not any(domain in l for l in hosts_lines):
            new_lines.append(f"{ZEROED_IP} {domain}\n")

    write_hosts_file(new_lines)
    flush_dns()


def unblock(file=None):
    dictionary = get_dictionary(file)
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


def blocked_list(file=None):
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
        print("Заблокированные домены:")
        for domain in blocked:
            print(domain)
    else:
        print("Нет заблокированных доменов.")

def parse_args():
    parser = argparse.ArgumentParser(description="Управление блокировкой доменов через /etc/hosts")
    parser.add_argument("--file", help="Файл со списком доменов для применения (если не будет выбран, то берется файл \"servers\" рядом со скриптом)", default="servers")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("block", help="Блокировка доменов из списка")
    subparsers.add_parser("unblock", help="Разблокировка доменов из списка")
    subparsers.add_parser("list", help="Показать все заблокированные домены")
    return parser.parse_args()


actions = {
    "block": block,
    "unblock": unblock,
    "list": blocked_list
}


def menu():
    args = parse_args()

    if args.command in ["block", "unblock"]:
        check_root()
        backup()

    action = actions.get(args.command)
    if action:
        action(args.file)
    else:
        print("Данное действие не поддерживается")


if __name__ == '__main__':
    menu()
