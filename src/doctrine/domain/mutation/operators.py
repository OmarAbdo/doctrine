"""Mutants: copies of a module with one small deliberate break on a changed line. A test suite that
still passes on a mutant doesn't check that line's behaviour."""

import ast
from collections.abc import Callable, Iterator
from dataclasses import dataclass

SWAPS: dict[type, tuple[type, str, str]] = {
    ast.Eq: (ast.NotEq, "==", "!="),
    ast.NotEq: (ast.Eq, "!=", "=="),
    ast.Lt: (ast.GtE, "<", ">="),
    ast.GtE: (ast.Lt, ">=", "<"),
    ast.Gt: (ast.LtE, ">", "<="),
    ast.LtE: (ast.Gt, "<=", ">"),
    ast.In: (ast.NotIn, "in", "not in"),
    ast.NotIn: (ast.In, "not in", "in"),
    ast.Is: (ast.IsNot, "is", "is not"),
    ast.IsNot: (ast.Is, "is not", "is"),
    ast.And: (ast.Or, "and", "or"),
    ast.Or: (ast.And, "or", "and"),
    ast.Add: (ast.Sub, "+", "-"),
    ast.Sub: (ast.Add, "-", "+"),
    ast.Mult: (ast.Div, "*", "/"),
    ast.Div: (ast.Mult, "/", "*"),
}

Change = Callable[[ast.AST], None]


@dataclass(frozen=True)
class Mutant:
    line: int
    description: str
    source: str


def swap_operator(node: ast.AST) -> tuple[str, Change] | None:
    holder = node.ops if isinstance(node, ast.Compare) and len(node.ops) == 1 else None
    current = holder[0] if holder else getattr(node, "op", None)
    if type(current) not in SWAPS or isinstance(node, ast.UnaryOp):
        return None
    replacement, before, after = SWAPS[type(current)]

    def change(target: ast.AST) -> None:
        if isinstance(target, ast.Compare):
            target.ops = [replacement()]
        elif isinstance(target, (ast.BoolOp, ast.BinOp)):
            target.op = replacement()

    return f"{before} became {after}", change


def drop_negation(node: ast.AST) -> tuple[str, Change] | None:
    if not (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not)):
        return None

    def change(target: ast.AST) -> None:
        assert isinstance(target, ast.UnaryOp)
        target.operand = ast.UnaryOp(op=ast.Not(), operand=target.operand)

    return "not removed", change


def empty_return(node: ast.AST) -> tuple[str, Change] | None:
    if not isinstance(node, ast.Return) or node.value is None:
        return None
    if isinstance(node.value, ast.Constant) and node.value.value is None:
        return None
    return "return value became None", lambda target: setattr(target, "value", ast.Constant(None))


def change_constant(node: ast.AST) -> tuple[str, Change] | None:
    if not isinstance(node, ast.Constant):
        return None
    value = node.value
    if isinstance(value, bool):
        return f"{value} became {not value}", lambda target: setattr(target, "value", not value)
    if isinstance(value, int):
        return f"{value} became {value + 1}", lambda target: setattr(target, "value", value + 1)
    return None


OPERATORS = (empty_return, swap_operator, drop_negation, change_constant)


def sites(tree: ast.Module, lines: set[int]) -> Iterator[tuple[int, int, int, str, Change]]:
    """(line, column, node index, description, change) for every mutation on the given lines."""
    on_lines: list[tuple[int, ast.expr | ast.stmt]] = [
        (index, node)
        for index, node in enumerate(ast.walk(tree))
        if isinstance(node, (ast.expr, ast.stmt)) and node.lineno in lines
    ]
    for index, node in on_lines:
        found = [mutation for operator in OPERATORS if (mutation := operator(node))]
        yield from ((node.lineno, node.col_offset, index, *mutation) for mutation in found)


def mutants(source: str, lines: set[int]) -> list[Mutant]:
    found = []
    for line, _column, index, description, change in sorted(sites(ast.parse(source), lines)):
        tree = ast.parse(source)
        change(list(ast.walk(tree))[index])
        found.append(Mutant(line=line, description=description, source=ast.unparse(tree)))
    return found
