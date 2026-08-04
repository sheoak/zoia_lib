import ast
import os
import unittest

PACKAGE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _boolean_except_handlers():
    """Finds every `except A or B:` in the package.

    Written against the syntax tree rather than the text so that neither
    formatting nor the exception names involved can hide an occurrence.
    """

    found = []
    for root, _, files in os.walk(PACKAGE):
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and isinstance(
                    node.type, ast.BoolOp
                ):
                    found.append(
                        "{}:{}".format(os.path.relpath(path, PACKAGE), node.lineno)
                    )
    return found


class BooleanExceptClauseTest(unittest.TestCase):
    """`except A or B:` catches A only, and says otherwise.

    The expression is evaluated before `except` sees it, and a class is
    truthy, so the whole thing collapses to `A`. Every site in this package
    guarded a filesystem call meant to be translated into a domain error, so
    the second exception reached the UI raw instead.
    """

    def test_no_except_clause_uses_a_boolean_operator(self):
        self.assertEqual(
            _boolean_except_handlers(),
            [],
            "these handlers only catch their first exception; use a tuple",
        )

    def test_the_check_itself_works(self):
        tree = ast.parse("try:\n    pass\nexcept KeyError or ValueError:\n    pass\n")
        handler = tree.body[0].handlers[0]
        self.assertIsInstance(handler.type, ast.BoolOp)

    def test_a_tuple_is_not_flagged(self):
        tree = ast.parse("try:\n    pass\nexcept (KeyError, ValueError):\n    pass\n")
        handler = tree.body[0].handlers[0]
        self.assertNotIsInstance(handler.type, ast.BoolOp)
