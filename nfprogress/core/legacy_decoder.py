"""Static-inspected, restricted decoder for legacy NFProgress pickle files.

This module is a migration boundary only.  It deliberately does not attempt to
be a security sandbox: the allowlisted Python classes still execute their
normal object construction methods while the pickle is decoded.  A future web
converter must run this code in a disposable isolated worker.
"""

from __future__ import annotations

import pickle
import pickletools
from io import BytesIO
from pathlib import Path
from typing import Any


MAX_PICKLE_BYTES = 64 * 1024 * 1024
MAX_PICKLE_OPCODES = 500_000
MAX_OBJECTS = 250_000
MAX_OBJECT_DEPTH = 128


class LegacyDecodeError(RuntimeError):
    """A legacy pickle cannot be safely classified or decoded."""

    code = "source_corrupt"


class UnsupportedLegacyObject(LegacyDecodeError):
    """The pickle requests a class or callable outside the NFProgress allowlist."""

    code = "unsupported_legacy_object"


# These are the concrete classes used by the historical desktop stores.  The
# list is intentionally explicit; adding a class requires a fixture and a
# migration review.
ALLOWED_GLOBALS = frozenset({
    ("engine", "Project"),
    ("engine", "Stage"),
    ("engine", "Note"),
    ("engine", "Notification"),
    ("game", "Gamer"),
    ("game", "Quest"),
    ("game_data", "Buff"),
    ("game_data", "Item"),
    ("game_data", "FuncItem"),
    ("game_data", "BankAccount"),
    ("game_data", "Credit"),
    ("game_data", "Deposit"),
    ("datetime", "date"),
    ("datetime", "datetime"),
    ("datetime", "time"),
    ("decimal", "Decimal"),
    ("uuid", "UUID"),
    ("pathlib", "Path"),
    ("collections", "OrderedDict"),
    ("copyreg", "_reconstructor"),
})

ALLOWED_BUILTINS = frozenset({
    "bool", "bytearray", "bytes", "complex", "dict", "float", "frozenset",
    "int", "list", "set", "slice", "str", "tuple",
})

# Persistent IDs and the old instance opcodes can invoke external loaders or
# construct classes without the modern NEWOBJ path.  They are not used by the
# NFProgress stores and are rejected before unpickling.
FORBIDDEN_OPCODES = frozenset({
    "EXT1", "EXT2", "EXT4", "INST", "OBJ", "PERSID", "BINPERSID",
    "NEWOBJ_EX",
})


def _static_globals(payload: bytes) -> list[tuple[str, str]]:
    """Inspect opcodes and recover GLOBAL/STACK_GLOBAL references."""
    references: list[tuple[str, str]] = []
    stack: list[Any] = []
    memo: dict[int, Any] = {}
    memo_next = 0
    mark = object()
    for index, (opcode, argument, _position) in enumerate(pickletools.genops(payload)):
        if index >= MAX_PICKLE_OPCODES:
            raise LegacyDecodeError("pickle contains too many opcodes")
        if opcode.name in FORBIDDEN_OPCODES:
            raise LegacyDecodeError(f"unsupported pickle opcode: {opcode.name}")
        if opcode.name == "GLOBAL":
            try:
                module, name = str(argument).split(" ", 1)
            except ValueError as error:
                raise LegacyDecodeError("malformed pickle global") from error
            references.append((module, name))
            stack.append((module, name))
            continue
        if opcode.name in {"SHORT_BINUNICODE", "BINUNICODE", "UNICODE", "STRING"}:
            stack.append(argument)
            continue
        if opcode.name in {"BINPUT", "LONG_BINPUT", "PUT"} and stack:
            memo[int(argument)] = stack[-1]
            continue
        if opcode.name == "MEMOIZE" and stack:
            memo[memo_next] = stack[-1]
            memo_next += 1
            continue
        if opcode.name in {"BINGET", "LONG_BINGET", "GET"}:
            stack.append(memo.get(int(argument)))
            continue
        if opcode.name == "STACK_GLOBAL":
            if len(stack) < 2 or not isinstance(stack[-1], str) or not isinstance(stack[-2], str):
                raise LegacyDecodeError("cannot statically resolve pickle global")
            module, name = stack[-2], stack[-1]
            references.append((module, name))
            stack[-2:] = [(module, name)]
            continue
        if opcode.name == "MARK":
            stack.append(mark)
        elif opcode.name in {"EMPTY_DICT", "EMPTY_LIST", "EMPTY_TUPLE"}:
            stack.append({} if opcode.name == "EMPTY_DICT" else [] if opcode.name == "EMPTY_LIST" else ())
        elif opcode.name == "TUPLE1" and stack:
            stack[-1:] = [(stack[-1],)]
        elif opcode.name == "SETITEM" and len(stack) >= 3:
            value, key = stack.pop(), stack.pop()
            _container = stack[-1]
            del value, key
        elif opcode.name in {"SETITEMS", "APPENDS"} and mark in stack:
            mark_index = max(index for index, item in enumerate(stack) if item is mark)
            stack[mark_index:] = [{} if opcode.name == "SETITEMS" else []]
        elif opcode.name in {"APPEND", "POP"} and len(stack) > 1:
            stack.pop()
        elif opcode.name in {"NEWOBJ", "REDUCE"} and len(stack) >= 2:
            stack[-2:] = [object()]
        elif opcode.name == "BUILD" and len(stack) >= 2:
            stack[-2:] = [stack[-2]]
        # The static pass only needs the strings/memo stack.  Other structural
        # operations are harmless for classification and are intentionally not
        # interpreted as Python objects here.
    return references


class RestrictedLegacyUnpickler(pickle.Unpickler):
    """Unpickler with an explicit NFProgress class/callable allowlist."""

    def find_class(self, module: str, name: str) -> Any:  # noqa: D102
        if (module, name) in ALLOWED_GLOBALS:
            return super().find_class(module, name)
        if module == "builtins" and name in ALLOWED_BUILTINS:
            return super().find_class(module, name)
        raise UnsupportedLegacyObject(f"unsupported_legacy_object: {module}.{name}")


def _check_object_graph(value: Any, *, depth: int = 0, seen: set[int] | None = None) -> int:
    if seen is None:
        seen = set()
    if depth > MAX_OBJECT_DEPTH:
        raise LegacyDecodeError("legacy object graph is too deeply nested")
    if value is None or isinstance(value, (str, bytes, bytearray, int, float, bool)):
        return 1
    marker = id(value)
    if marker in seen:
        return 1
    seen.add(marker)
    total = 1
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, (list, tuple, set, frozenset)):
        items = ((None, item) for item in value)
    elif hasattr(value, "__dict__"):
        items = vars(value).items()
    else:
        items = ()
    for key, item in items:
        total += _check_object_graph(key, depth=depth + 1, seen=seen)
        total += _check_object_graph(item, depth=depth + 1, seen=seen)
        if total > MAX_OBJECTS:
            raise LegacyDecodeError("legacy object graph contains too many values")
    seen.remove(marker)
    return total


def load_legacy_pickle(path: str | Path) -> Any:
    """Inspect and decode one known legacy pickle without unrestricted loading."""
    source = Path(path).expanduser().resolve()
    try:
        size = source.stat().st_size
    except OSError as error:
        raise LegacyDecodeError(f"cannot stat legacy pickle: {source.name}") from error
    if size > MAX_PICKLE_BYTES:
        raise LegacyDecodeError("legacy pickle exceeds the 64 MiB limit")
    try:
        payload = source.read_bytes()
    except OSError as error:
        raise LegacyDecodeError(f"cannot read legacy pickle: {source.name}") from error
    try:
        references = _static_globals(payload)
    except (ValueError, IndexError, UnicodeDecodeError, pickle.UnpicklingError) as error:
        raise LegacyDecodeError("malformed legacy pickle opcode stream") from error
    unknown = [reference for reference in references if reference not in ALLOWED_GLOBALS and not (
        reference[0] == "builtins" and reference[1] in ALLOWED_BUILTINS
    )]
    if unknown:
        module, name = unknown[0]
        raise UnsupportedLegacyObject(f"unsupported_legacy_object: {module}.{name}")
    try:
        value = RestrictedLegacyUnpickler(BytesIO(payload)).load()
    except UnsupportedLegacyObject:
        raise
    except (EOFError, ValueError, TypeError, pickle.UnpicklingError, AttributeError, RecursionError) as error:
        raise LegacyDecodeError("malformed or truncated legacy pickle") from error
    _check_object_graph(value)
    return value


__all__ = [
    "ALLOWED_GLOBALS", "LegacyDecodeError", "RestrictedLegacyUnpickler",
    "UnsupportedLegacyObject", "load_legacy_pickle",
]
