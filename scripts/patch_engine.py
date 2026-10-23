#!/usr/bin/env python3
"""Fail-closed RabbitMQ health-check compatibility patch for the pinned engine.

This modifies only the RabbitMQ healthcheck in the local, ignored upstream
Compose checkout. It never reads or writes environment files or Docker volumes.
"""

from pathlib import Path
import re
import sys

OLD_TEST = 'test: ["CMD", "rabbitmq-diagnostics", "-q", "check_running"]'
NEW_TEST = 'test: ["CMD", "gosu", "rabbitmq", "rabbitmq-diagnostics", "-q", "check_running"]'
HEALTH_VALUES = {
    "interval": ("5s", "10s"),
    "timeout": ("5s", "10s"),
    "retries": ("3", "10"),
    "start_period": ("5s", "120s"),
}


class PatchError(ValueError):
    """Compose layout differs from the vetted engine; do not guess."""


def _indent(line: str) -> int:
    prefix = line[: len(line) - len(line.lstrip())]
    if "\t" in prefix:
        raise PatchError("Unexpected tabs in Compose indentation")
    return len(prefix)


def _parent(lines: list[str], start: int, indent: int, label: str) -> int:
    for i in range(start - 1, -1, -1):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            continue
        depth = _indent(lines[i])
        if depth <= indent:
            if depth != indent or stripped != label:
                raise PatchError(f"RabbitMQ healthcheck expected beneath {label}")
            return i
    raise PatchError(f"Missing {label} enclosing RabbitMQ healthcheck")


def patch_compose(original: str) -> str:
    """Return patched YAML text; reject unexpected upstream formats unchanged."""
    lines = original.splitlines(keepends=True)
    candidates = [i for i, line in enumerate(lines) if line.strip() in (OLD_TEST, NEW_TEST)]
    if len(candidates) != 1:
        raise PatchError("Expected exactly one recognizable RabbitMQ diagnostics healthcheck")
    test_index = candidates[0]
    if _indent(lines[test_index]) != 6:
        raise PatchError("Unexpected RabbitMQ healthcheck indentation")
    health_index = _parent(lines, test_index, 4, "healthcheck:")
    _parent(lines, health_index, 2, "rabbitmq:")

    setting_indices: dict[str, int] = {}
    for i in range(health_index + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _indent(lines[i]) <= 4:
            break
        if _indent(lines[i]) != 6:
            continue
        match = re.fullmatch(r"(interval|timeout|retries|start_period):\s*(\S+)", stripped)
        if match:
            key, value = match.groups()
            if key in setting_indices:
                raise PatchError(f"Duplicate RabbitMQ {key} setting")
            old_value, new_value = HEALTH_VALUES[key]
            if value not in (old_value, new_value):
                raise PatchError(f"Unexpected RabbitMQ {key}: {value!r}")
            setting_indices[key] = i

    missing = set(HEALTH_VALUES) - set(setting_indices)
    if missing:
        raise PatchError(f"Missing RabbitMQ health settings: {', '.join(sorted(missing))}")

    lines[test_index] = lines[test_index].replace(OLD_TEST, NEW_TEST, 1)
    for key, (_, new_value) in HEALTH_VALUES.items():
        i = setting_indices[key]
        lines[i] = re.sub(
            rf"^(\s*{key}:\s*)\S+",
            lambda match: match.group(1) + new_value,
            lines[i],
            count=1,
        )
    return "".join(lines)


def main() -> int:
    compose = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("engine/docker-compose.yaml")
    try:
        raw = compose.read_bytes()
        current = raw.decode("utf-8")
        updated = patch_compose(current)
        if updated == current:
            print("RabbitMQ healthcheck already configured (120s startup grace period)")
        else:
            compose.write_bytes(updated.encode("utf-8"))
            print("RabbitMQ healthcheck updated (gosu rabbitmq; 120s startup grace period)")
    except (OSError, UnicodeError, PatchError) as error:
        print(f"RabbitMQ patch failed: {error}. Upstream Compose not changed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
