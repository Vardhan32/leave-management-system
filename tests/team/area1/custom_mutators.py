"""Custom mutation operators for the Leave Management System.

These operators target domain-specific business rules that generic
mutation tools (like mutmut) do not cover.

Operator 1 - BalanceBoundaryMutator (BR-1):
  Mutates the leave-balance boundary check by shifting the threshold
  by +1 or -1, simulating off-by-one errors in balance validation.

Operator 2 - WeekendSkipMutator (BR-4):
  Mutates the weekday check in working_days() by shifting the
  weekend threshold, simulating errors where Saturday is counted
  as a working day or Friday is excluded.

Usage:
    python custom_mutators.py
"""
import ast
import copy
import importlib
import subprocess
import sys
import textwrap
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent.parent.parent / "backend"
SERVICES = BACKEND / "app" / "services.py"
TESTS = Path(__file__).resolve().parent / "test_services.py"


class BalanceBoundaryMutator(ast.NodeTransformer):
    """BR-1: Shift balance boundary by +/- 1.

    Targets comparisons of the form `balance.remaining_days < days`
    and replaces them with `balance.remaining_days < days + 1`
    (or days - 1), simulating an off-by-one error in the leave
    balance boundary check.
    """

    def __init__(self, direction=1):
        self.direction = direction
        self.mutations_applied = 0

    def visit_Compare(self, node):
        if (
            isinstance(node.left, ast.Attribute)
            and node.left.attr == "remaining_days"
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Lt)
            and len(node.comparators) == 1
        ):
            original = node.comparators[0]
            node.comparators[0] = ast.BinOp(
                left=original,
                op=ast.Add(),
                right=ast.Constant(value=self.direction),
            )
            self.mutations_applied += 1
        return node


class WeekendSkipMutator(ast.NodeTransformer):
    """BR-4: Shift the weekday boundary.

    Targets comparisons of the form `cursor.weekday() < 5`
    and replaces the constant 5 with 4 (excludes Friday)
    or 6 (includes Saturday), simulating business-rule errors
    in what counts as a working day.
    """

    def __init__(self, new_threshold=6):
        self.new_threshold = new_threshold
        self.mutations_applied = 0

    def visit_Compare(self, node):
        if (
            isinstance(node.left, ast.Call)
            and isinstance(node.left.func, ast.Attribute)
            and node.left.func.attr == "weekday"
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Lt)
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Constant)
            and node.comparators[0].value == 5
        ):
            node.comparators[0] = ast.Constant(value=self.new_threshold)
            self.mutations_applied += 1
        return node


def apply_mutator_and_test(mutator_cls, label, **kwargs):
    """Apply a mutation to services.py, run the test suite, report result."""
    source = SERVICES.read_text(encoding="utf-8")
    tree = ast.parse(source)

    mutator = mutator_cls(**kwargs)
    mutated_tree = mutator.visit(tree)
    ast.fix_missing_locations(mutated_tree)

    if mutator.mutations_applied == 0:
        print(f"  [{label}] No matching AST nodes found -- skipped.")
        return None

    mutated_code = ast.unparse(mutated_tree)

    backup = source
    try:
        SERVICES.write_text(mutated_code, encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                str(TESTS), "-x", "-q", "--no-header", "--tb=line",
            ],
            capture_output=True, text=True, cwd=str(BACKEND),
            env={**__import__("os").environ, "SQLALCHEMY_DISABLE_CEXT": "1"},
            timeout=120,
        )
        killed = result.returncode != 0
        status = "KILLED" if killed else "SURVIVED"
        print(f"  [{label}] {mutator.mutations_applied} mutation(s) applied -> {status}")
        if killed:
            failing = [l for l in result.stdout.splitlines() if "FAILED" in l]
            if failing:
                print(f"    Caught by: {failing[0].strip()}")
        return killed
    finally:
        SERVICES.write_text(backup, encoding="utf-8")


def main():
    print("=" * 60)
    print("Custom Mutation Operators -- LeaveDesk Leave Management System")
    print("=" * 60)

    results = []

    print("\n--- Operator 1: BalanceBoundaryMutator (BR-1) ---")
    print("Targets: `remaining_days < days` -> `remaining_days < days + 1`")
    r = apply_mutator_and_test(BalanceBoundaryMutator, "balance+1", direction=1)
    results.append(("Balance boundary (days+1)", r))

    print("\nTargets: `remaining_days < days` -> `remaining_days < days - 1`")
    r = apply_mutator_and_test(BalanceBoundaryMutator, "balance-1", direction=-1)
    results.append(("Balance boundary (days-1)", r))

    print("\n--- Operator 2: WeekendSkipMutator (BR-4) ---")
    print("Targets: `weekday() < 5` -> `weekday() < 6`  (counts Saturday)")
    r = apply_mutator_and_test(WeekendSkipMutator, "weekend=6", new_threshold=6)
    results.append(("Weekend threshold 5->6", r))

    print("\nTargets: `weekday() < 5` -> `weekday() < 4`  (excludes Friday)")
    r = apply_mutator_and_test(WeekendSkipMutator, "weekend=4", new_threshold=4)
    results.append(("Weekend threshold 5->4", r))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    total = len([r for _, r in results if r is not None])
    killed = len([r for _, r in results if r is True])
    for label, r in results:
        mark = "KILLED" if r else ("SURVIVED" if r is False else "SKIPPED")
        print(f"  {label:40s} {mark}")
    print(f"\n  Mutation score: {killed}/{total} = {killed/total*100:.1f}%")


if __name__ == "__main__":
    main()
