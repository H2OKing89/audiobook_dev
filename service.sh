#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="$(basename "${SCRIPT_DIR}")"
SYSTEMCTL_BIN="$(command -v systemctl || true)"
JOURNALCTL_BIN="$(command -v journalctl || true)"
SUDO_BIN="$(command -v sudo || true)"

COLOR_RESET=$'\033[0m'
COLOR_BLUE=$'\033[1;34m'
COLOR_CYAN=$'\033[1;36m'
COLOR_GREEN=$'\033[1;32m'
COLOR_RED=$'\033[1;31m'
COLOR_YELLOW=$'\033[1;33m'
COLOR_DIM=$'\033[2m'

SERVICE_NAME=""

banner() {
    cat <<'EOF'
    ___              ___ __              __
   /   | __  _______/ (_) /_  ____  ____/ /__
  / /| |/ / / / __  / / / __ \/ __ \/ __  / _ \
 / ___ / /_/ / /_/ / / / /_/ / /_/ / /_/ /  __/
/_/  |_|\__,_/\__,_/_/_/_.___/\____/\__,_/\___/

   _____                 _
  / ___/___  ______   __(_)_______
  \__ \/ _ \/ ___/ | / / / ___/ _ \
 ___/ /  __/ /   | |/ / / /__/  __/
/____/\___/_/    |___/_/\___/\___/
EOF
}

usage() {
    banner
    cat <<EOF

${COLOR_CYAN}Systemd control panel${COLOR_RESET}
${COLOR_DIM}Service:${COLOR_RESET} ${SERVICE_NAME:-auto-detect}

Usage:
  ./service.sh start
  ./service.sh stop
  ./service.sh restart
  ./service.sh status
  ./service.sh logs
  ./service.sh follow
  ./service.sh enable
  ./service.sh disable
  ./service.sh reload
  ./service.sh daemon-reload
  ./service.sh help

Environment:
  AUDIOBOOK_SERVICE_NAME   Override the default systemd unit name.

Examples:
  ./service.sh restart
  AUDIOBOOK_SERVICE_NAME=my-app ./service.sh status
EOF
}

service_candidates() {
    local normalized

    normalized="${PROJECT_NAME//_/-}"

    printf '%s\n' \
        audiobook \
        audiobook-approval \
        audiobook_dev \
        audiobook-dev \
        "${PROJECT_NAME}" \
        "${normalized}"
}

unit_exists() {
    [[ -n "${SYSTEMCTL_BIN}" ]] || return 1
    "${SYSTEMCTL_BIN}" list-unit-files --type=service --no-legend --no-pager 2>/dev/null |
        awk -v unit="$1.service" '$1 == unit { found = 1 } END { exit(found ? 0 : 1) }'
}

resolve_service_name() {
    local candidate

    if [[ -n "${AUDIOBOOK_SERVICE_NAME:-}" ]]; then
        SERVICE_NAME="${AUDIOBOOK_SERVICE_NAME}"
        return
    fi

    while IFS= read -r candidate; do
        if [[ -n "${candidate}" ]] && unit_exists "${candidate}"; then
            SERVICE_NAME="${candidate}"
            return
        fi
    done < <(service_candidates | awk '!seen[$0]++')

    SERVICE_NAME="audiobook"
}

list_matching_units() {
    require_systemctl
    "${SYSTEMCTL_BIN}" list-unit-files --type=service --no-legend --no-pager 2>/dev/null |
        awk '{print $1}' | grep -E 'audio|book|approval|mam' || true
}

ensure_known_unit() {
    local matches

    if unit_exists "${SERVICE_NAME}"; then
        return
    fi

    matches="$(list_matching_units)"

    printf '%b\n' "${COLOR_RED}[MISS]${COLOR_RESET} ${SERVICE_NAME}.service is not installed on this machine." >&2
    if [[ -n "${matches}" ]]; then
        printf '%b\n' "${COLOR_YELLOW}Try one of these units:${COLOR_RESET}" >&2
        printf '%s\n' "${matches}" >&2
    else
        printf '%b\n' "${COLOR_YELLOW}No matching audiobook-style units were found.${COLOR_RESET}" >&2
    fi
    printf '%b\n' "${COLOR_DIM}Override with:${COLOR_RESET} AUDIOBOOK_SERVICE_NAME=<unit> ./service.sh <command>" >&2
    exit 1
}

require_systemctl() {
    if [[ -z "${SYSTEMCTL_BIN}" ]]; then
        printf '%b\n' "${COLOR_RED}systemctl was not found on this machine.${COLOR_RESET}" >&2
        exit 1
    fi
}

require_journalctl() {
    if [[ -z "${JOURNALCTL_BIN}" ]]; then
        printf '%b\n' "${COLOR_RED}journalctl was not found on this machine.${COLOR_RESET}" >&2
        exit 1
    fi
}

run_systemctl() {
    require_systemctl

    if [[ "${EUID}" -eq 0 ]]; then
        "${SYSTEMCTL_BIN}" "$@"
        return
    fi

    if [[ -n "${SUDO_BIN}" ]]; then
        "${SUDO_BIN}" "${SYSTEMCTL_BIN}" "$@"
        return
    fi

    printf '%b\n' "${COLOR_RED}This command needs root privileges and sudo is unavailable.${COLOR_RESET}" >&2
    exit 1
}

run_journalctl() {
    require_journalctl

    if [[ "${EUID}" -eq 0 ]]; then
        "${JOURNALCTL_BIN}" "$@"
        return
    fi

    if [[ -n "${SUDO_BIN}" ]]; then
        "${SUDO_BIN}" "${JOURNALCTL_BIN}" "$@"
        return
    fi

    "${JOURNALCTL_BIN}" "$@"
}

print_header() {
    banner
    printf '%b\n' "${COLOR_BLUE}==>${COLOR_RESET} ${COLOR_CYAN}$1${COLOR_RESET}"
    printf '%b\n' "${COLOR_DIM}Unit:${COLOR_RESET} ${SERVICE_NAME}"
    printf '\n'
}

show_status() {
    local state

    ensure_known_unit

    if state="$("${SYSTEMCTL_BIN}" is-active "${SERVICE_NAME}" 2>/dev/null)"; then
        printf '%b\n' "${COLOR_GREEN}[LIVE]${COLOR_RESET} ${SERVICE_NAME} is ${state}"
        return
    fi

    state="$("${SYSTEMCTL_BIN}" is-enabled "${SERVICE_NAME}" 2>/dev/null || true)"
    if [[ -n "${state}" ]]; then
        printf '%b\n' "${COLOR_YELLOW}[IDLE]${COLOR_RESET} ${SERVICE_NAME} is not active (${state})"
        return
    fi

    printf '%b\n' "${COLOR_RED}[MISS]${COLOR_RESET} ${SERVICE_NAME} is unknown to systemd"
}

action_start() {
    print_header "Ignition sequence"
    ensure_known_unit
    run_systemctl start "${SERVICE_NAME}"
    show_status
}

action_stop() {
    print_header "Shutdown sequence"
    ensure_known_unit
    run_systemctl stop "${SERVICE_NAME}"
    show_status
}

action_restart() {
    print_header "Hard reboot"
    ensure_known_unit
    run_systemctl restart "${SERVICE_NAME}"
    show_status
}

action_status() {
    print_header "Status scan"
    require_systemctl
    show_status
    printf '\n'
    "${SYSTEMCTL_BIN}" status "${SERVICE_NAME}" --no-pager || true
}

action_logs() {
    print_header "Recent journal"
    ensure_known_unit
    run_journalctl -u "${SERVICE_NAME}" -n 50 --no-pager
}

action_follow() {
    print_header "Live journal tail"
    ensure_known_unit
    run_journalctl -u "${SERVICE_NAME}" -f
}

action_enable() {
    print_header "Boot hookup"
    ensure_known_unit
    run_systemctl enable "${SERVICE_NAME}"
    "${SYSTEMCTL_BIN}" is-enabled "${SERVICE_NAME}" || true
}

action_disable() {
    print_header "Boot disconnect"
    ensure_known_unit
    run_systemctl disable "${SERVICE_NAME}"
    "${SYSTEMCTL_BIN}" is-enabled "${SERVICE_NAME}" || true
}

action_reload() {
    print_header "Soft reload"
    ensure_known_unit
    run_systemctl reload "${SERVICE_NAME}"
    show_status
}

action_daemon_reload() {
    print_header "Systemd refresh"
    run_systemctl daemon-reload
    printf '%b\n' "${COLOR_GREEN}[OK]${COLOR_RESET} systemd manager configuration reloaded"
}

main() {
    local action="${1:-help}"

    case "${action}" in
        help|-h|--help)
            usage
            return
            ;;
    esac

    resolve_service_name

    case "${action}" in
        start)
            action_start
            ;;
        stop)
            action_stop
            ;;
        restart)
            action_restart
            ;;
        status)
            action_status
            ;;
        logs)
            action_logs
            ;;
        follow)
            action_follow
            ;;
        enable)
            action_enable
            ;;
        disable)
            action_disable
            ;;
        reload)
            action_reload
            ;;
        daemon-reload)
            action_daemon_reload
            ;;
        *)
            printf '%b\n\n' "${COLOR_RED}Unknown command:${COLOR_RESET} ${action}" >&2
            usage
            exit 1
            ;;
    esac
}

main "$@"
