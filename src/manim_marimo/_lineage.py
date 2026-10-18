"""Trace each shape in a rendered scene to the notebook results that produced it.

A scene reads notebook results with ``value()``, ``output()``, and ``cell()``,
then builds and animates shapes from them. The tracer follows those results
through the scene's own code in two halves:

- Before the scene runs, a static pass over each project file records which
  local names hold a read, a part of one, or a result computed from one. A
  name bound by ``joint = np.asarray(value("joint"))`` holds ``joint``, and a
  name bound by ``for index, probability in enumerate(probabilities)`` holds
  ``probabilities[index]``.
- While the scene runs, a line tracer watches only project frames. When a
  statement creates or changes a shape, the tracer evaluates the index
  expressions of the reads it uses with the frame's current locals, so
  ``Rectangle(fill_opacity=joint[i, j])`` marks that rectangle with
  ``joint[2][3]``. A change replaces the reads of earlier frames, so a shape
  that an updater moves along ``chain[index]`` carries the sample it shows.

Each written frame records the screen box of every shape that shows a read.
Runs of frames where a shape keeps its box and reads become one region of the
video, and the shapes on the last frame become regions of the poster.
"""

from __future__ import annotations

import ast
import json
import math
import operator
import sys
from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field, replace
from itertools import pairwise
from pathlib import Path
from types import CodeType, FrameType
from typing import Any, cast
from weakref import WeakKeyDictionary

_READS = frozenset({"value", "output", "cell"})
# Calls that keep the shape of a read, so indexing them indexes the read.
_SHAPE_PRESERVING = frozenset({"asarray", "array", "list", "tuple", "float", "int"})
# Calls that return a size, which places shapes without showing the read, as in
# ``for index in range(len(probabilities))``.
_SIZES = frozenset({"len", "range"})
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
# Methods that return another object, or only read their shape, so the shape
# they are called on keeps its reads.
_QUERIES = frozenset(
    {
        "copy",
        "deepcopy",
        "c2p",
        "p2c",
        "n2p",
        "p2n",
        "i2gp",
        "pfp",
        "coords_to_point",
        "point_to_coords",
        "number_to_point",
        "point_to_number",
        "input_to_graph_point",
        "point_from_proportion",
    }
)
_QUERY_PREFIXES = ("get_", "has_", "is_")
# Methods that arrange or collect shapes, so the group they are called on shows
# none of the reads of the shapes they place.
_PLACING = frozenset(
    {
        "add",
        "add_to_back",
        "remove",
        "insert_submobject",
        "set_submobjects",
        "arrange",
        "arrange_in_grid",
    }
)
# Methods that make their receiver take on another shape's geometry.
_ADOPTING = frozenset({"become", "match_points", "set_points", "replace"})
_OPERATORS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
# A box moves to a new region when an edge shifts by more than this fraction.
_MOVE = 0.004
MAX_REGIONS = 4_000
MAX_READS = 64
MAX_BYTES = 1_000_000


@dataclass(frozen=True)
class _Read:
    """A notebook read, or a part of one, that a name holds.

    ``steps`` are index expressions evaluated against a frame's locals, and
    ``None`` marks an index the scene's code leaves unknown. ``whole`` marks a
    name that is the read itself, so indexing the name indexes the read.
    """

    selector: str
    steps: tuple[ast.expr | None, ...] = ()
    whole: bool = False
    # The local name a statement reaches the read through, and how many of the
    # steps that name's own value covers, when it holds a part of the read.
    via: str | None = None
    held: int | None = None
    # The statement that bound that name, when the name has several.
    bound: int | None = None

    def narrowed(self, steps: Iterable[ast.expr | None]) -> _Read:
        return replace(self, steps=(*self.steps, *steps))


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _index_parts(node: ast.expr) -> list[ast.expr | None]:
    if isinstance(node, ast.Tuple):
        return [None if isinstance(item, ast.Slice) else item for item in node.elts]
    return [None if isinstance(node, ast.Slice) else node]


@dataclass(frozen=True)
class _Readers:
    """The names a project file reads notebook results through.

    ``functions`` holds names imported from ``manim_marimo``, such as ``value``
    or an alias of it, and ``modules`` holds names bound to the module itself.
    """

    functions: frozenset[str]
    modules: frozenset[str]

    @classmethod
    def of(cls, tree: ast.Module) -> _Readers:
        functions: set[str] = set()
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "manim_marimo":
                functions |= {
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name in _READS
                }
            elif isinstance(node, ast.Import):
                modules |= {
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "manim_marimo"
                }
        return cls(frozenset(functions), frozenset(modules))

    def reads(self, call: ast.Call) -> bool:
        function = call.func
        if isinstance(function, ast.Name):
            return function.id in self.functions
        return (
            isinstance(function, ast.Attribute)
            and function.attr in _READS
            and isinstance(function.value, ast.Name)
            and function.value.id in self.modules
        )


class _Scope:
    """The reads each local name of one function or module holds."""

    def __init__(self, node: ast.AST, parent: _Scope | None, readers: _Readers) -> None:
        self.node = node
        self.parent = parent
        self.readers = readers
        self.names: dict[str, set[_Read]] = {}
        self.binders: dict[str, set[int]] = {}

    def shadow(self, arguments: ast.arguments) -> None:
        """Bind each parameter, so it hides the outer name it shares."""
        for argument in (
            *arguments.posonlyargs,
            *arguments.args,
            arguments.vararg,
            *arguments.kwonlyargs,
            arguments.kwarg,
        ):
            if argument is not None:
                self.names.setdefault(argument.arg, set())

    def lookup(self, name: str) -> set[_Read]:
        scope: _Scope | None = self
        while scope is not None:
            if name in scope.names:
                return scope.names[name]
            scope = scope.parent
        return set()

    def reads(self, node: ast.AST | None) -> set[_Read]:
        """Return the reads an expression uses."""
        if node is None:
            return set()
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            first = node.args[0] if node.args else None
            if (
                self.readers.reads(node)
                and isinstance(first, ast.Constant)
                and isinstance(first.value, str)
            ):
                return {_Read(first.value, whole=True)}
            if name in _SHAPE_PRESERVING and len(node.args) == 1:
                return self.reads(node.args[0])
            if name in _SIZES:
                return set()
        if isinstance(node, ast.Subscript):
            inner = self.reads(node.value)
            parts = _index_parts(node.slice)
            if not inner:
                # An index into a constant, such as PALETTE[status], picks what
                # the shape shows by the index's reads.
                return self._partial(self.reads(node.slice))
            # An index into a read selects a part of it, which the shape shows,
            # rather than the reads that computed the index.
            return {
                read.narrowed(parts) if read.whole else replace(read, whole=False)
                for read in inner
            }
        if isinstance(node, ast.Name):
            # A loop or comprehension target receives a value, so it shows none
            # of the reads its name held before.
            if isinstance(node.ctx, ast.Store):
                return set()
            return {
                replace(read, via=node.id, held=len(read.steps) if read.whole else None)
                for read in self.lookup(node.id)
            }
        if isinstance(node, ast.Lambda):
            inner = _Scope(node, self, self.readers)
            inner.shadow(node.args)
            return inner.reads(node.body)
        if isinstance(node, _COMPREHENSIONS):
            return self._comprehension(node)
        found: set[_Read] = set()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr | ast.keyword | ast.comprehension):
                found |= self.reads(child)
        return self._partial(found)

    def _comprehension(
        self, node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp
    ) -> set[_Read]:
        """Return the reads of a comprehension, whose names stay inside it."""
        inner = _Scope(node, self, self.readers)
        found: set[_Read] = set()
        for generator in node.generators:
            found |= inner.reads(generator.iter)
            inner.bind_loop(generator.target, generator.iter, node)
            for condition in generator.ifs:
                found |= inner.reads(condition)
        parts = [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
        for part in parts:
            found |= inner.reads(part)
        # An index named by the comprehension's own variables means nothing
        # outside it.
        local = set(inner.names)
        return {
            replace(
                read,
                whole=False,
                steps=tuple(
                    None if isinstance(step, ast.Name) and step.id in local else step
                    for step in read.steps
                ),
            )
            for read in found
        }

    @staticmethod
    def _partial(reads: set[_Read]) -> set[_Read]:
        return {replace(read, whole=False) for read in reads}

    def multiple(self, name: str) -> bool:
        """Return whether several statements bind ``name``."""
        return len(self.binders.get(name, ())) > 1

    def bind(self, target: ast.expr, reads: set[_Read], binder: ast.AST) -> bool:
        """Add ``reads`` to the names ``target`` binds in the statement
        ``binder``, and report a change."""
        if isinstance(target, ast.Name):
            self.binders.setdefault(target.id, set()).add(id(binder))
            held = self.names.setdefault(target.id, set())
            before = len(held)
            held |= {
                replace(read, via=None, held=None, bound=id(binder)) for read in reads
            }
            return len(held) != before
        if isinstance(target, ast.Tuple | ast.List):
            changed = False
            for item in target.elts:
                changed |= self.bind(item, self._partial(reads), binder)
            return changed
        return False

    def bind_value(self, target: ast.expr, value: ast.expr, binder: ast.AST) -> bool:
        """Bind ``target`` to ``value``, pairing the items of two tuples."""
        if _paired(target, value):
            changed = False
            for item, part in zip(
                cast("ast.Tuple", target).elts,
                cast("ast.Tuple", value).elts,
                strict=True,
            ):
                changed |= self.bind_value(item, part, binder)
            return changed
        return self.bind(target, self.reads(value), binder)

    def bind_loop(
        self,
        target: ast.expr,
        iterable: ast.expr,
        binder: ast.AST,
        index: ast.expr | None = None,
    ) -> bool:
        """Bind a loop or comprehension target to the items it walks.

        ``index`` is the ``enumerate()`` counter that numbers those items.
        """
        if isinstance(iterable, ast.Call) and iterable.args:
            name = _call_name(iterable.func)
            if (
                name == "enumerate"
                and isinstance(target, ast.Tuple)
                and len(target.elts) == 2
                and isinstance(target.elts[0], ast.Name)
            ):
                counter = target.elts[0]
                self.bind(counter, set(), binder)
                return self.bind_loop(target.elts[1], iterable.args[0], binder, counter)
            if name == "zip" and _paired(target, ast.Tuple(iterable.args)):
                changed = False
                for item, part in zip(
                    cast("ast.Tuple", target).elts, iterable.args, strict=True
                ):
                    changed |= self.bind_loop(item, part, binder, index)
                return changed
        items = {
            read.narrowed([index]) if read.whole else read
            for read in self.reads(iterable)
        }
        return self.bind(target, items, binder)


def _paired(target: ast.expr, value: ast.expr) -> bool:
    """Return whether a tuple target unpacks a tuple of as many plain items."""
    return (
        isinstance(target, ast.Tuple | ast.List)
        and isinstance(value, ast.Tuple | ast.List)
        and len(target.elts) == len(value.elts)
        and not any(
            isinstance(item, ast.Starred) for item in (*target.elts, *value.elts)
        )
    )


class _Module:
    """The scopes and statements of one project file.

    ``statements`` maps each line to the innermost statement on it, or to the
    header of a compound statement, with the scope its names resolve in.
    """

    def __init__(self, path: Path) -> None:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        self.statements: dict[int, tuple[ast.stmt, _Scope]] = {}
        self._reads: dict[int, set[_Read]] = {}
        self._plans: dict[int, object] = {}
        scope = _Scope(tree, None, _Readers.of(tree))
        # Imported names hold modules, functions, and classes, never shapes.
        self.imported = frozenset(
            (alias.asname or alias.name).split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import | ast.ImportFrom)
            for alias in node.names
        )
        self._settle(tree, scope)
        self._index(tree, scope)

    def plan(self, line: int) -> _Plan | None:
        """Return the plan of the statement on ``line``."""
        plan = self._plans.get(line, _MISSING)
        if plan is _MISSING:
            found = self.statements.get(line)
            plan = None
            if found:
                statement, scope = found
                binds = tuple(
                    name for name in _bound_names(statement) if scope.multiple(name)
                )
                plan = _Plan.of(
                    statement, scope, self.reads(statement, scope), binds, self.imported
                )
                if isinstance(statement, ast.For | ast.AsyncFor | ast.While):
                    # A loop whose body never changes a shape needs no pass marks.
                    self._plans[line] = plan
                    body = [
                        node
                        for child in [*statement.body, *statement.orelse]
                        for node in ast.walk(child)
                        if isinstance(node, ast.stmt)
                    ]
                    plans = [self.plan(node.lineno) for node in body]
                    if all(item is None or item.inert for item in plans):
                        plan = replace(plan, loop=False)
            self._plans[line] = plan
        return cast("_Plan | None", plan)

    def reads(self, statement: ast.stmt, scope: _Scope) -> set[_Read]:
        """Return the reads a statement uses, apart from the names it assigns."""
        cached = self._reads.get(id(statement))
        if cached is None:
            cached = set()
            for part in _parts(statement):
                if isinstance(part, ast.Assign | ast.AnnAssign | ast.AugAssign):
                    cached |= scope.reads(part.value)
                elif isinstance(part, ast.stmt):
                    for child in ast.iter_child_nodes(part):
                        cached |= scope.reads(child)
                else:
                    cached |= scope.reads(part)
            self._reads[id(statement)] = cached
        return cached

    def _settle(self, node: ast.AST, scope: _Scope) -> None:
        # Names can be bound after their first use in a loop, so bind until
        # the scope stops changing.
        for _ in range(4):
            if not self._bind(node, scope):
                break

    def _bind(
        self, node: ast.AST, scope: _Scope, statement: ast.AST | None = None
    ) -> bool:
        changed = False
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                continue
            # A name a comprehension or ``:=`` binds belongs to its statement.
            binder = child if isinstance(child, ast.stmt) else statement or child
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    changed |= scope.bind_value(target, child.value, binder)
            elif isinstance(child, ast.AnnAssign | ast.AugAssign) and child.value:
                changed |= scope.bind(child.target, scope.reads(child.value), binder)
            elif isinstance(child, ast.For | ast.AsyncFor):
                changed |= scope.bind_loop(child.target, child.iter, binder)
            elif isinstance(child, _COMPREHENSIONS):
                # A comprehension's names stay inside it.
                continue
            elif isinstance(child, ast.NamedExpr):
                changed |= scope.bind(child.target, scope.reads(child.value), binder)
            changed |= self._bind(child, scope, binder)
        return changed

    def _index(self, node: ast.AST, scope: _Scope) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                inner = _Scope(child, scope, scope.readers)
                inner.shadow(child.args)
                self._settle(child, inner)
                self._index(child, inner)
                continue
            if isinstance(child, ast.stmt):
                last = child.lineno if _compound(child) else child.end_lineno
                for line in range(child.lineno, (last or child.lineno) + 1):
                    current = self.statements.get(line)
                    # A one-line ``if test: body`` runs its body only sometimes,
                    # so the header keeps the line.
                    if current is not None and _compound(current[0]):
                        continue
                    if current is None or _span(child) <= _span(current[0]):
                        self.statements[line] = (child, scope)
            self._index(child, scope)


def _compound(node: ast.stmt) -> bool:
    return isinstance(
        node,
        ast.For
        | ast.AsyncFor
        | ast.While
        | ast.If
        | ast.With
        | ast.AsyncWith
        | ast.Try
        | ast.FunctionDef
        | ast.AsyncFunctionDef
        | ast.ClassDef,
    )


def _span(node: ast.stmt) -> int:
    return (node.end_lineno or node.lineno) - node.lineno


def _parts(statement: ast.stmt) -> list[ast.AST]:
    """Return the expressions of a statement, or of a compound statement's header."""
    if isinstance(statement, ast.For | ast.AsyncFor):
        return [statement.target, statement.iter]
    if isinstance(statement, ast.While | ast.If):
        return [statement.test]
    if isinstance(statement, ast.With | ast.AsyncWith):
        return [item.context_expr for item in statement.items]
    if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return []
    if isinstance(statement, ast.Try):
        return []
    return [statement]


@dataclass(frozen=True)
class _Plan:
    """What the tracer does with one statement each time it runs.

    ``assigned`` names the shapes an assignment binds, ``receivers`` the
    shapes the statement calls a method on, such as ``dot`` in
    ``dot.animate.move_to(...)``, and ``items`` the receivers it indexes, such
    as ``squares[i]``. Shapes the statement passes as arguments only anchor or
    animate the call, so its reads stay off them. A statement with none of
    these changes no shape, and the tracer skips it.
    """

    statement: ast.stmt
    reads: tuple[_Read, ...]
    assigned: tuple[str, ...]
    # Each receiver with the reads of its own calls, so ``run_time=d`` in
    # ``self.play(dot.animate.shift(UP), run_time=d)`` stays off ``dot``.
    receivers: tuple[tuple[str, tuple[_Read, ...]], ...]
    items: tuple[tuple[ast.Subscript, tuple[_Read, ...]], ...]
    adopting: tuple[ast.Call, ...]
    name: str | None
    # A loop header runs before each pass, which marks where a pass starts.
    loop: bool = False
    # The names with several binding statements that this statement binds.
    binds: tuple[str, ...] = ()
    # The shapes the statement copies, as ``bar`` in ``target = bar.copy()``.
    copies: tuple[ast.expr, ...] = ()

    @property
    def inert(self) -> bool:
        # A call without reads changes no shape's reads, as ``dot.move_to(point)``
        # does not.
        changes = any(reads for _, reads in (*self.receivers, *self.items))
        return not (changes or self.assigned or self.adopting or self.binds)

    @classmethod
    def of(
        cls,
        statement: ast.stmt,
        scope: _Scope,
        reads: Iterable[_Read],
        binds: tuple[str, ...] = (),
        imported: frozenset[str] = frozenset(),
    ) -> _Plan:
        nodes = [node for part in _parts(statement) for node in ast.walk(part)]
        assigned: list[str] = []
        if isinstance(statement, ast.Assign | ast.AnnAssign | ast.AugAssign):
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )
            assigned = [
                node.id
                for target in targets
                for node in ast.walk(target)
                if isinstance(node, ast.Name)
            ]
        assigned += [
            node.target.id
            for node in nodes
            if isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name)
        ]
        receivers: dict[str, set[_Read]] = {}
        items: dict[int, tuple[ast.Subscript, set[_Read]]] = {}
        copies: list[ast.expr] = []
        # A call in a branch of ``a if test else b`` may never run.
        branches = {
            id(inner)
            for node in nodes
            if isinstance(node, ast.IfExp)
            for branch in (node.body, node.orelse)
            for inner in ast.walk(branch)
        }
        for node in nodes:
            if id(node) in branches:
                continue
            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue
            if node.func.attr in ("copy", "deepcopy"):
                copied = _receiver(node.func.value)
                if copied is not None:
                    copies.append(copied)
            if not _query(node.func.attr) and node.func.attr not in _PLACING:
                receiver = _receiver(node.func.value)
                if isinstance(receiver, ast.Name) and receiver.id not in imported:
                    receivers.setdefault(receiver.id, set()).update(scope.reads(node))
                elif isinstance(receiver, ast.Subscript):
                    held = items.setdefault(id(receiver), (receiver, set()))[1]
                    held.update(scope.reads(node))
        return cls(
            statement,
            tuple(reads),
            tuple(dict.fromkeys(assigned)),
            tuple(
                (name, tuple(held))
                for name, held in receivers.items()
                if name not in assigned
            ),
            tuple((node, tuple(held)) for node, held in items.values()),
            tuple(
                node
                for node in nodes
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in _ADOPTING
                and node.args
            ),
            _assigned_name(statement),
            isinstance(statement, ast.For | ast.AsyncFor | ast.While),
            binds,
            tuple(copies),
        )


def _query(method: str) -> bool:
    return method in _QUERIES or method.startswith(_QUERY_PREFIXES)


def _bound_names(statement: ast.stmt) -> list[str]:
    """Return the names a statement binds, including in its comprehensions."""
    targets: list[ast.expr] = []
    if isinstance(statement, ast.Assign):
        targets += statement.targets
    elif isinstance(statement, ast.AnnAssign | ast.AugAssign | ast.For | ast.AsyncFor):
        targets.append(statement.target)
    for part in _parts(statement):
        for node in ast.walk(part):
            if isinstance(node, ast.NamedExpr):
                targets.append(node.target)
    return [
        node.id
        for target in targets
        for node in ast.walk(target)
        if isinstance(node, ast.Name)
    ]


def _receiver(node: ast.expr) -> ast.expr | None:
    """Return the shape a chain of calls starts from, such as ``a`` in
    ``a.animate.shift(UP).scale(2)``, or ``squares[i]`` in ``squares[i].copy()``."""
    while True:
        if isinstance(node, ast.Attribute) and node.attr == "animate":
            node = node.value
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            # The calls after ``copy()`` change the copy.
            if _query(node.func.attr):
                return None
            node = node.func.value
        else:
            break
    if isinstance(node, ast.Name) or (
        isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
    ):
        return node
    return None


class _Names:
    """The names one frame resolves at one moment.

    Reading ``frame.f_locals`` copies every local before Python 3.13, so an
    event reads it once. Before Python 3.12 a comprehension runs in a frame of
    its own, so its names fall back to the frame that runs it.
    """

    __slots__ = ("frame", "globals", "locals", "outer")

    def __init__(self, frame: FrameType) -> None:
        self.frame = frame
        self.locals = frame.f_locals
        self.globals = frame.f_globals
        self.outer: Mapping[str, Any] | None = None
        if frame.f_code.co_name in _COMPREHENSION_FRAMES and frame.f_back:
            self.outer = frame.f_back.f_locals

    def get(self, name: str, default: Any = None) -> Any:
        found = self.locals.get(name, _MISSING)
        if found is _MISSING and self.outer is not None:
            found = self.outer.get(name, _MISSING)
        if found is _MISSING:
            found = self.globals.get(name, default)
        return found

    def __getitem__(self, name: str) -> Any:
        found = self.get(name, _MISSING)
        if found is _MISSING:
            raise LookupError(name)
        return found


_MISSING = object()
_COMPREHENSION_FRAMES = frozenset(
    {"<listcomp>", "<setcomp>", "<dictcomp>", "<genexpr>"}
)
_NONE: frozenset[str] = frozenset()


def _item(names: _Names, base: ast.expr, index: ast.expr) -> Any:
    """Return ``base[index]`` for a list, tuple, or group of shapes.

    Other containers can change or load data when indexed, so the tracer
    leaves them alone.
    """
    from manimlib import Mobject

    container = _evaluate(base, names)
    key = _evaluate(index, names)
    if isinstance(container, list | tuple):
        return container[key]
    # Indexing a shape by text builds a new group of its parts, so only an
    # integer reaches its submobjects.
    if isinstance(container, Mobject) and type(key) is int:
        return container.submobjects[key]
    raise LookupError("unsupported container")


def _kind(shape: Any) -> str:
    """Return a shape's class, and the start of its text when it has some."""
    kind = type(shape).__name__
    text = getattr(shape, "text", None)
    if isinstance(text, str) and text.strip():
        snippet = " ".join(text.split())
        kind = f'{kind} "{snippet[:48]}{"…" if len(snippet) > 48 else ""}"'
    return kind


def _assigned_name(statement: ast.stmt) -> str | None:
    """Return the one name an assignment binds, such as ``bars`` in ``bars = ...``."""
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        target = statement.targets[0]
    elif isinstance(statement, ast.AnnAssign | ast.AugAssign):
        target = statement.target
    else:
        return None
    return target.id if isinstance(target, ast.Name) else None


def _evaluate(node: ast.expr | None, names: _Names) -> Any:
    """Evaluate a simple index expression, or raise ``LookupError``."""
    if isinstance(node, ast.Name):
        return names[node.id]
    if isinstance(node, ast.Constant) and isinstance(node.value, int | str):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](
            _evaluate(node.left, names), _evaluate(node.right, names)
        )
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_evaluate(node.operand, names)
    raise LookupError("unsupported index")


def _step(value: Any) -> str | None:
    if hasattr(value, "__index__") and not isinstance(value, bool):
        index = int(value.__index__())
        return f"[{index}]" if index >= 0 else None
    if isinstance(value, str):
        # Studio's selectors name ASCII identifiers that do not start with an
        # underscore as fields, and every other key in brackets.
        plain = value.isascii() and value.isidentifier() and not value.startswith("_")
        return f".{value}" if plain else f"[{json.dumps(value, ensure_ascii=False)}]"
    return None


def _same(local: Any, expected: Any) -> bool:
    """Return whether a local holds the notebook value ``expected``."""
    import numpy as np

    try:
        ours, theirs = np.asarray(local), np.asarray(expected)
        if ours.dtype.kind in "biuf" and theirs.dtype.kind in "biuf":
            return ours.shape == theirs.shape and bool(
                np.allclose(ours, theirs, equal_nan=True)
            )
    except (TypeError, ValueError):
        pass
    try:
        return bool(local == expected)
    except Exception:
        return False


def _specific(selectors: Iterable[str]) -> frozenset[str]:
    """Keep each selector that no other selector narrows."""
    found = set(selectors)
    if len(found) < 2:
        return frozenset(found)
    narrowed = {
        selector[:index]
        for selector in found
        for index, character in enumerate(selector)
        if index and character in "[."
    }
    return frozenset(found - narrowed)


@dataclass
class _Shape:
    """What the tracer knows about one shape.

    ``key`` names the shape's runs after the shape itself is gone.
    """

    key: int
    kind: str
    source: tuple[str, int, int]
    name: str | None = None
    created: frozenset[str] = frozenset()
    changed: frozenset[str] = frozenset()
    epoch: int = -1
    reads: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        reads = _specific(self.created | self.changed)
        if reads != self.reads:
            self.reads = reads


@dataclass
class _Pending:
    """An assignment a frame is running, with the reads it shows.

    ``first`` is the key the next created shape takes, and ``inherited`` holds
    the reads of the shapes the statement calls methods on, which a copy such
    as ``target = bar.copy()`` keeps.
    """

    plan: _Plan
    reads: frozenset[str]
    first: int
    inherited: frozenset[str]


_Box = tuple[float, float, float, float]


@dataclass
class _Run:
    box: _Box
    reads: frozenset[str]
    start: int
    end: int
    # A run that kept its box for half a second or longer, where a reader who
    # pauses the movie finds the shape exactly.
    still: bool = False


@dataclass
class SceneLineage:
    """Trace the shapes of one scene run beneath the project ``root``.

    ``values`` are the notebook values the scene reads, which confirm that a
    name still holds the part of a read the tracer attributes to it.
    """

    root: Path
    values: Mapping[str, Any] = field(default_factory=dict)
    shapes: WeakKeyDictionary[Any, _Shape] = field(default_factory=WeakKeyDictionary)
    epoch: int = 0
    disabled: bool = False
    every: int = 1
    _modules: dict[str, Any] = field(default_factory=dict)
    _project: dict[CodeType, bool] = field(default_factory=dict)
    _pending: dict[FrameType, _Pending] = field(default_factory=dict)
    # The statement each frame runs, so the later lines of a statement that
    # spans several lines continue it.
    _at: dict[FrameType, ast.stmt] = field(default_factory=dict)
    # The last statement that bound each name with several binding statements.
    _bound: dict[FrameType, dict[str, int]] = field(default_factory=dict)
    _quiet: set[int] = field(default_factory=set)
    _misses: dict[int, int] = field(default_factory=dict)
    _closed: dict[CodeType, dict[str, int]] = field(default_factory=dict)
    _specifics: dict[frozenset[str], frozenset[str]] = field(default_factory=dict)
    _groups: dict[int, tuple[tuple[_Read, ...], list[Any]]] = field(
        default_factory=dict
    )
    _known: dict[int, _Shape] = field(default_factory=dict)
    _runs: dict[int, list[_Run]] = field(default_factory=dict)
    _frames: int = 0
    _checked: dict[tuple[str, int], tuple[Any, bool]] = field(default_factory=dict)
    _paths: dict[str, str] = field(default_factory=dict)
    _last: list[tuple[int, _Box]] = field(default_factory=list)

    # Static analysis

    def _module(self, filename: str) -> _Module | None:
        if filename not in self._modules:
            try:
                self._modules[filename] = _Module(Path(filename))
            except Exception:
                self._modules[filename] = None
        return self._modules[filename]

    def _in_project(self, code: CodeType) -> bool:
        known = self._project.get(code)
        if known is None:
            try:
                path = Path(code.co_filename).resolve()
                known = path.is_relative_to(self.root) and not any(
                    part.startswith(".") for part in path.relative_to(self.root).parts
                )
            except (OSError, ValueError):
                known = False
            self._project[code] = known
        return known

    def _plan(self, frame: FrameType) -> _Plan | None:
        return self._plan_at(frame.f_code.co_filename, frame.f_lineno)

    def _plan_at(self, filename: str, line: int) -> _Plan | None:
        module = self._modules.get(filename, _MISSING)
        if module is _MISSING:
            module = self._module(filename)
        return module.plan(line) if module is not None else None

    def _selectors(
        self,
        reads: tuple[_Read, ...],
        names: _Names,
        frame: FrameType,
        statement: ast.stmt,
    ) -> frozenset[str]:
        """Return the selectors of ``reads`` as the frame's locals narrow them.

        A read reached through a name that holds a shape is that shape's own
        lineage, which the tracer follows through the shape itself. A name
        that several statements bind holds the reads of the one that ran last.
        """
        from manimlib import Mobject

        groups = self._groups.get(id(reads))
        if groups is None or groups[0] is not reads:
            groups = self._groups[id(reads)] = (reads, self._group(reads))
        bound = self._bound.get(frame)
        current_statement = id(statement)
        kept: set[str] = set()
        for via, group in groups[1]:
            local = None
            current = None
            if via is not None:
                local = names.get(via)
                if isinstance(local, Mobject):
                    continue
                table = bound
                # An updater or comprehension reads the name of the frame that
                # encloses it.
                if via in frame.f_code.co_freevars:
                    table = self._enclosing(frame, via)
                current = table.get(via) if table else None
            for read, fixed in group:
                if (
                    current is not None
                    and read.bound not in (None, current_statement)
                    and current != read.bound
                ):
                    continue
                if fixed:
                    kept.add(read.selector)
                else:
                    selector = self._selector(read, names, local)
                    if selector is not None:
                        kept.add(selector)
        if len(kept) < 2:
            return frozenset(kept)
        key = frozenset(kept)
        specific = self._specifics.get(key)
        if specific is None:
            if len(self._specifics) > 4_096:
                self._specifics.clear()
            specific = self._specifics[key] = _specific(kept)
        return specific

    def _group(
        self, reads: tuple[_Read, ...]
    ) -> list[tuple[str | None, list[tuple[_Read, bool]]]]:
        """Group reads by the name they are reached through, and mark the ones
        whose selector is fixed: without an index to evaluate, such as
        people[None] for a loop over every row, or a check against the
        notebook."""
        groups: dict[str | None, list[tuple[_Read, bool]]] = {}
        for read in reads:
            fixed = not (read.steps and read.steps[0] is not None) and not (
                read.held is not None and read.selector in self.values
            )
            groups.setdefault(read.via, []).append((read, fixed))
        return list(groups.items())

    def _enclosing(self, frame: FrameType, name: str) -> dict[str, int] | None:
        """Return the binding statements of the nearest calling frame that
        tracks ``name``, or of the returned frame that defined this code."""
        outer = frame.f_back
        for _ in range(64):
            if outer is None:
                break
            table = self._bound.get(outer)
            if table is not None and name in table:
                return table
            outer = outer.f_back
        return self._closed.get(frame.f_code)

    def _selector(self, read: _Read, names: _Names, local: Any) -> str | None:
        """Return the selector of ``read``, as far as its index steps evaluate.

        A name that holds a part of a value read must hold the notebook's value
        of that part, so a loop name reused for another read, or an index that
        moved on, drops the read.
        """
        selector = read.selector
        keys: list[int | str] = []
        for node in read.steps:
            try:
                key = _evaluate(node, names)
                step = _step(key)
            except Exception:
                break
            if step is None:
                break
            selector += step
            keys.append(key if isinstance(key, str) else int(key.__index__()))
        if (
            read.held is None
            or read.selector not in self.values
            or len(keys) < read.held
        ):
            return selector
        part = read.selector + "".join(_step(key) or "" for key in keys[: read.held])
        cached = self._checked.get((part, id(local)))
        if cached is None or cached[0] is not local:
            expected = self.values[read.selector]
            try:
                for key in keys[: read.held]:
                    expected = expected[key]
                same = local is expected or _same(local, expected)
            except (LookupError, TypeError):
                same = False
            if len(self._checked) > 4_096:
                self._checked.clear()
            cached = self._checked[part, id(local)] = (local, same)
        return selector if cached[1] else None

    # Runtime tracing

    def _source(self, frame: FrameType, plan: _Plan | None) -> tuple[str, int, int]:
        column = plan.statement.col_offset + 1 if plan else 1
        filename = frame.f_code.co_filename
        path = self._paths.get(filename)
        if path is None:
            path = self._paths[filename] = (
                Path(filename).resolve().relative_to(self.root).as_posix()
            )
        return (path, plan.statement.lineno if plan else frame.f_lineno, column)

    def _shape(
        self, shape: Any, frame: FrameType, plan: _Plan | None, reads: frozenset[str]
    ) -> _Shape:
        traced = self.shapes[shape] = _Shape(
            len(self._known), _kind(shape), self._source(frame, plan), created=reads
        )
        self._known[traced.key] = traced
        return traced

    def created(self, shape: Any) -> None:
        """Record where the scene's code created ``shape``, and what it read."""
        if self.disabled or shape in self.shapes:
            return
        try:
            frame = sys._getframe(2)
            while frame is not None and not self._in_project(frame.f_code):
                frame = frame.f_back
            if frame is not None:
                plan = self._plan(frame)
                reads = (
                    self._selectors(plan.reads, _Names(frame), frame, plan.statement)
                    if plan
                    else _NONE
                )
                self._shape(shape, frame, plan, reads)
        except Exception as error:
            self._disable(error)

    def _line(self, frame: FrameType, filename: str, line: int) -> bool:
        """Follow the statement starting on ``frame``'s line, and report
        whether the line can never change a shape."""
        plan = self._plan_at(filename, line)
        if plan is None:
            return True
        statement = plan.statement
        if self._at.get(frame) is statement:
            return False
        self._at[frame] = statement
        names = None
        pending = self._pending.pop(frame, None)
        if pending is not None:
            names = _Names(frame)
            self._assign(frame, names, pending)
        if plan.inert or id(statement) in self._quiet:
            return not plan.loop
        names = names or _Names(frame)
        # Assignments keep the statement's reads, and a call reads its own.
        reads = (
            self._selectors(plan.reads, names, frame, statement)
            if plan.reads and plan.assigned
            else _NONE
        )
        if plan.binds:
            bound = self._bound.get(frame)
            if bound is None:
                bound = self._bound[frame] = {}
            for name in plan.binds:
                bound[name] = id(statement)
        # The shapes a statement calls methods on exist before it runs, so it
        # changes them now, before any frame it writes, such as a play() call's.
        inherited = (
            self._receive(frame, names, plan, reads)
            if plan.receivers or plan.items or plan.adopting
            else _NONE
        )
        for node in plan.copies:
            with suppress(Exception):
                copied = (
                    _item(names, node.value, node.slice)
                    if isinstance(node, ast.Subscript)
                    else _evaluate(node, names)
                )
                shape = self.shapes.get(copied)
                if shape is not None:
                    inherited = inherited | shape.reads
        if plan.assigned:
            self._pending[frame] = _Pending(plan, reads, len(self._known), inherited)
        return False

    def _returned(self, frame: FrameType) -> None:
        pending = self._pending.pop(frame, None)
        if pending is not None:
            self._assign(frame, _Names(frame), pending)
        self._at.pop(frame, None)
        table = self._bound.pop(frame, None)
        if table:
            # An updater defined in the frame can run after it returns, as the
            # poster's last update does, and its names keep these bindings.
            nested = [frame.f_code]
            while nested:
                code = nested.pop()
                for constant in code.co_consts:
                    if isinstance(constant, CodeType):
                        self._closed[constant] = table
                        nested.append(constant)

    def _receive(
        self, frame: FrameType, names: _Names, plan: _Plan, reads: frozenset[str]
    ) -> frozenset[str]:
        """Give the shapes a statement calls methods on the reads of those calls,
        and return the reads those shapes held."""
        from manimlib import Mobject

        shapes, statement = self.shapes, plan.statement
        receivers: list[tuple[Any, tuple[_Read, ...]]] = []
        for name, held in plan.receivers:
            item = names.get(name)
            if isinstance(item, Mobject):
                receivers.append((item, held))
        for node, held in plan.items:
            with suppress(Exception):
                item = _item(names, node.value, node.slice)
                if isinstance(item, Mobject):
                    receivers.append((item, held))
        inherited = _NONE
        for item, _ in receivers:
            shape = shapes.get(item)
            if shape is not None:
                inherited = inherited | shape.reads
        for item, held in receivers:
            changes = self._selectors(held, names, frame, statement) if held else _NONE
            shape = shapes.get(item)
            if shape is None:
                self._shape(item, frame, plan, changes | inherited)
            elif changes:
                self._change(shape, changes)
        for node in plan.adopting:
            receiver = cast("ast.Attribute", node.func).value
            if isinstance(receiver, ast.Attribute) and receiver.attr == "animate":
                receiver = receiver.value
            try:
                if isinstance(receiver, ast.Subscript):
                    target = _item(names, receiver.value, receiver.slice)
                else:
                    target = _evaluate(receiver, names)
                source = _evaluate(node.args[0], names)
            except Exception:
                continue
            shape, adopted = shapes.get(target), shapes.get(source)
            if shape is not None and adopted is not None and adopted.reads:
                self._change(shape, adopted.reads)
        return inherited

    def _assign(self, frame: FrameType, names: _Names, pending: _Pending) -> None:
        """Name the shapes an assignment bound, once it ran.

        A shape created after the statement started, such as one a helper
        builds in ``bar = make(heights[0])``, also takes the reads of the line
        that called the helper.
        """
        from manimlib import Mobject

        plan, reads = pending.plan, pending.reads
        shaped = False
        for name in plan.assigned:
            item = names.locals.get(name)
            if not isinstance(item, Mobject):
                continue
            shaped = True
            shape = self.shapes.get(item)
            if shape is None:
                shape = self._shape(item, frame, plan, reads | pending.inherited)
            if shape.name is None:
                shape.name = plan.name
            if shape.key >= pending.first and not reads <= shape.created:
                shape.created |= reads
                shape.refresh()
        # An assignment that keeps binding no shape, such as ``phase = day % 1``
        # in an updater, stops reporting itself.
        if not shaped and not plan.binds and not (plan.receivers or plan.items):
            misses = self._misses[id(plan.statement)] = (
                self._misses.get(id(plan.statement), 0) + 1
            )
            if misses >= 16:
                self._quiet.add(id(plan.statement))

    def _change(self, shape: _Shape, reads: frozenset[str]) -> None:
        """Give ``shape`` the reads of a change in the current frame, in place of
        the reads of changes in earlier frames."""
        if shape.epoch != self.epoch:
            if shape.changed == reads:
                shape.epoch = self.epoch
                return
            shape.changed, shape.epoch = reads, self.epoch
        elif reads <= shape.changed:
            return
        else:
            shape.changed = shape.changed | reads
        shape.refresh()

    def _local(
        self, frame: FrameType, event: str, arg: Any
    ) -> Callable[..., Any] | None:
        del arg
        if self.disabled:
            return None
        try:
            if event == "line":
                self._line(frame, frame.f_code.co_filename, frame.f_lineno)
            elif event == "return":
                self._returned(frame)
        except Exception as error:
            self._disable(error)
            return None
        return self._local

    def _global(
        self, frame: FrameType, event: str, arg: Any
    ) -> Callable[..., Any] | None:
        del arg
        if not self.disabled and event == "call" and self._in_project(frame.f_code):
            return self._local
        return None

    def _disable(self, error: Exception) -> None:
        # A tracing problem must never change what the scene renders.
        self.disabled = True
        self._pending.clear()
        self._at.clear()
        self._bound.clear()
        print(f"Scene lineage stopped: {error!r}", file=sys.stderr)

    @contextmanager
    def trace(self) -> Generator[None, None, None]:
        """Trace mobject creation and the scene's statements while active."""
        from manimlib import Mobject

        original = Mobject.__init__
        lineage = self

        def init(shape: Any, *args: Any, **kwargs: Any) -> None:
            original(shape, *args, **kwargs)
            lineage.created(shape)

        Mobject.__init__ = init  # type: ignore[method-assign]
        release = self._monitor() or self._settrace()
        try:
            yield
        finally:
            release()
            Mobject.__init__ = original  # type: ignore[method-assign]

    def _monitor(self) -> Callable[[], None] | None:
        """Watch the lines of project code with ``sys.monitoring``.

        Python 3.12 and newer stop reporting calls into a function once it
        starts outside the project, so ManimGL and NumPy run at full speed.
        """
        monitoring = getattr(sys, "monitoring", None)
        if monitoring is None:
            return None
        tool = next(
            (item for item in (3, 4) if monitoring.get_tool(item) is None), None
        )
        if tool is None:
            return None
        events = monitoring.events
        watched: list[CodeType] = []

        def started(code: CodeType, offset: int) -> Any:
            del offset
            if not self.disabled and self._in_project(code):
                watched.append(code)
                monitoring.set_local_events(
                    tool, code, events.LINE | events.PY_RETURN | events.PY_YIELD
                )
            return monitoring.DISABLE

        def line(code: CodeType, number: int) -> Any:
            if self.disabled:
                return monitoring.DISABLE
            try:
                # A line that changes no shape stops reporting itself.
                if self._line(sys._getframe(1), code.co_filename, number):
                    return monitoring.DISABLE
            except Exception as error:
                self._disable(error)
            return None

        def returned(code: CodeType, offset: int, value: object) -> None:
            del code, offset, value
            self._local(sys._getframe(1), "return", None)

        def unwound(code: CodeType, offset: int, error: BaseException) -> None:
            # A frame that an exception ends never reports its return.
            del code, offset, error
            frame = sys._getframe(1)
            self._pending.pop(frame, None)
            self._at.pop(frame, None)
            self._bound.pop(frame, None)

        monitoring.use_tool_id(tool, "manim-marimo lineage")
        monitoring.register_callback(tool, events.PY_START, started)
        monitoring.register_callback(tool, events.LINE, line)
        monitoring.register_callback(tool, events.PY_RETURN, returned)
        monitoring.register_callback(tool, events.PY_YIELD, returned)
        monitoring.register_callback(tool, events.PY_UNWIND, unwound)
        monitoring.set_events(tool, events.PY_START | events.PY_UNWIND)

        def release() -> None:
            monitoring.set_events(tool, events.NO_EVENTS)
            for code in watched:
                monitoring.set_local_events(tool, code, events.NO_EVENTS)
            for event in (
                events.PY_START,
                events.LINE,
                events.PY_RETURN,
                events.PY_YIELD,
                events.PY_UNWIND,
            ):
                monitoring.register_callback(tool, event, None)
            monitoring.free_tool_id(tool)

        return release

    def _settrace(self) -> Callable[[], None]:
        """Watch the lines of project code with ``sys.settrace``.

        A debugger or coverage tool that owns the trace function keeps it, so
        that run records where each shape was created, and not how statements
        change it.
        """
        if sys.gettrace() is not None:
            return lambda: None
        sys.settrace(self._global)
        return lambda: sys.settrace(None)

    # Frames

    def frame(self, scene: Any) -> None:
        """Record the screen box of every traced shape in the frame just written.

        Every ``every``-th frame records boxes, and its runs last until the
        next one. Boxes follow a camera that looks straight at the scene, as in
        2D scenes. A frame from a turned camera records no boxes.
        """
        if not self.disabled and self._frames % self.every == 0:
            try:
                self._record(self._shown(scene))
            except Exception as error:
                self._disable(error)
        self._frames += 1
        # Changes after this frame replace the reads of the changes before it.
        self.epoch += 1

    def poster(self, scene: Any) -> None:
        """Record the shapes of the scene's last frame, which the poster shows."""
        if self.disabled:
            return
        try:
            self._last = self._shown(scene)
        except Exception as error:
            self._disable(error)

    def _shown(self, scene: Any) -> list[tuple[int, _Box]]:
        """Return the box of each traced shape the scene shows that reads."""
        camera = scene.camera.frame
        if any(abs(float(angle)) > 1e-6 for angle in camera.get_euler_angles()):
            return []
        center = camera.get_center()
        width, height = float(camera.get_width()), float(camera.get_height())
        left, top = float(center[0]) - width / 2, float(center[1]) + height / 2
        shapes = self.shapes
        shown: list[tuple[int, _Box]] = []
        seen: set[int] = set()
        family = [shape for group in scene.mobjects for shape in group.get_family()]
        # ManimGL also groups shapes to batch their rendering, so only groups in
        # the scene count as parents.
        members = {id(shape) for shape in family}
        for shape in family:
            traced = shapes.get(shape)
            if traced is None or not traced.reads or traced.key in seen:
                continue
            seen.add(traced.key)
            # The parts a line creates with their shape belong to its region,
            # when the shape shows reads of its own.
            if any(
                id(parent) in members
                and (above := shapes.get(parent)) is not None
                and above.source == traced.source
                and above.reads
                for parent in shape.parents
            ):
                continue
            box = _box(shape, left, top, width, height)
            if box is not None:
                shown.append((traced.key, box))
        return shown

    def _record(self, shown: list[tuple[int, _Box]]) -> None:
        index, until = self._frames, self._frames + self.every
        for key, box in shown:
            reads = self._known[key].reads
            runs = self._runs.get(key)
            if runs is None:
                runs = self._runs[key] = []
            last = runs[-1] if runs else None
            if (
                last is not None
                and last.end == index
                and (last.reads is reads or last.reads == reads)
                and abs(last.box[0] - box[0]) < _MOVE
                and abs(last.box[1] - box[1]) < _MOVE
                and abs(last.box[2] - box[2]) < _MOVE
                and abs(last.box[3] - box[3]) < _MOVE
            ):
                last.end = until
                # Half a second at rest is a moment a reader pauses on.
                last.still = until - last.start >= 6 * self.every
            else:
                runs.append(_Run(box, reads, index, until))

    # Records

    def _label(self, key: int) -> str:
        traced = self._known[key]
        return f"{traced.name}: {traced.kind}" if traced.name else traced.kind

    def _record_of(self, key: int, box: _Box, reads: frozenset[str]) -> dict[str, Any]:
        path, line, column = self._known[key].source
        return {
            "box": [round(value, 4) for value in box],
            "reads": sorted(reads)[:MAX_READS],
            "source": {"path": path, "line": line, "column": column},
            "label": self._label(key),
        }

    def records(self) -> dict[str, Any]:
        """Return the regions of the video and its last frame as JSON data.

        Studio keeps a bounded number of regions, and the page loads them with
        the movie. A shape that moves on every frame has a run per recorded
        frame, so while the regions exceed those bounds, adjacent runs of a
        shape merge into one run over both frame ranges with the union of their
        boxes. Each round merges the pairs whose targets loosen least, so large
        shapes coarsen before small moving ones. A shape that holds still keeps
        its exact box, and every frame keeps a target for every shape.
        """
        last = [
            self._record_of(key, box, self._known[key].reads) for key, box in self._last
        ][:MAX_REGIONS]

        def records(runs: Iterable[tuple[int, _Run]]) -> list[dict[str, Any]]:
            return [
                {
                    **self._record_of(key, run.box, run.reads),
                    "start": run.start,
                    "end": None if run.end >= self._frames else run.end,
                }
                for key, run in runs
            ]

        def excess(regions: list[dict[str, Any]]) -> int:
            """Return how many regions to merge away to fit both bounds."""
            over = len(last) + len(regions) - MAX_REGIONS
            size = len(json.dumps([last, regions]))
            if size > MAX_BYTES:
                over = max(over, -(-(size - MAX_BYTES) * len(regions) // size))
            return max(over, 0)

        shapes = {key: list(items) for key, items in self._runs.items()}
        while True:
            runs = [(key, run) for key, items in shapes.items() for run in items]
            regions = records(runs)
            needed = excess(regions)
            if not needed:
                break
            pairs = sorted(
                (_growth(first, second), key, index)
                for key, items in shapes.items()
                for index, (first, second) in enumerate(pairwise(items))
                if first.end == second.start
            )
            # Still runs merge only once every moving run has.
            if pairs and pairs[0][0] == math.inf:
                pairs = sorted(
                    (_growth(_moving(first), _moving(second)), key, index)
                    for _, key, index in pairs
                    for first, second in [shapes[key][index : index + 2]]
                )
            if not pairs:
                # Runs apart in time stay apart, so keep the longest.
                runs.sort(key=lambda item: item[1].start - item[1].end)
                while runs and excess(regions):
                    runs = runs[: len(runs) * 3 // 4]
                    regions = records(runs)
                break
            chosen: dict[int, set[int]] = {}
            for cost, key, index in pairs:
                if cost == math.inf:
                    break
                taken = chosen.setdefault(key, set())
                if index in taken or index - 1 in taken or index + 1 in taken:
                    continue
                taken.add(index)
                needed -= 1
                if not needed:
                    break
            for key, indexes in chosen.items():
                items = shapes[key]
                for index in sorted(indexes, reverse=True):
                    items[index : index + 2] = [_union(items[index], items[index + 1])]
        return {"frames": self._frames, "regions": regions, "last": last}


def _box(
    shape: Any, left: float, top: float, width: float, height: float
) -> _Box | None:
    """Return the box of a visible shape in fractions of the camera frame."""
    family = shape.family_members_with_points()
    if not family:
        return None
    with suppress(Exception):
        if max(float(item.get_opacity()) for item in family) < 0.02:
            return None
    low, _, high = shape.get_bounding_box()
    # A line drawn between two equal points has no direction, and no box.
    if not (math.isfinite(low[0] + low[1] + high[0] + high[1])):
        return None
    x0 = max((float(low[0]) - left) / width, 0.0)
    x1 = min((float(high[0]) - left) / width, 1.0)
    y0 = max((top - float(high[1])) / height, 0.0)
    y1 = min((top - float(low[1])) / height, 1.0)
    if x1 - x0 < 0.002 or y1 - y0 < 0.002:
        # Lines and points still get a box a reader can point at.
        x0, x1 = max(x0 - 0.004, 0.0), min(x1 + 0.004, 1.0)
        y0, y1 = max(y0 - 0.004, 0.0), min(y1 + 0.004, 1.0)
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1 - x0, y1 - y0)


def _growth(first: _Run, second: _Run) -> float:
    """Return how much merging two runs loosens their targets: each run's box
    grows to the union for as many frames as the run lasts. Runs that show
    different reads cost one frame more."""
    if first.still or second.still:
        return math.inf
    union = _union(first, second).box
    cost = float(first.reads != second.reads)
    for run in (first, second):
        area = max(run.box[2] * run.box[3], 1e-6)
        cost += (union[2] * union[3] / area - 1) * (run.end - run.start)
    return cost


def _moving(run: _Run) -> _Run:
    return replace(run, still=False)


def _union(first: _Run, second: _Run) -> _Run:
    """Return one run over two adjacent runs, with the union of their boxes."""
    x0 = min(first.box[0], second.box[0])
    y0 = min(first.box[1], second.box[1])
    x1 = max(first.box[0] + first.box[2], second.box[0] + second.box[2])
    y1 = max(first.box[1] + first.box[3], second.box[1] + second.box[3])
    return _Run(
        (x0, y0, x1 - x0, y1 - y0),
        _specific(first.reads | second.reads),
        first.start,
        second.end,
    )
