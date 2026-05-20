"""
Calculator Tool — safe math expression evaluator.
Uses Python's ast module — no eval() security risk.
"""

from __future__ import annotations
import ast
import operator

ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}


def calculate(expression: str) -> str:
    """
    Safely evaluate a math expression string.
    Example: calculate("(100 * 3.14) / 2") → "157.0"
    """
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        return str(result)
    except ZeroDivisionError:
        return "[Error] Division by zero"
    except Exception as e:
        return f"[Error] Invalid expression: {e}"


def _eval_node(node):
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPS:
            raise ValueError(f"Unsupported operator: {op_type}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return ALLOWED_OPS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPS:
            raise ValueError(f"Unsupported operator: {op_type}")
        return ALLOWED_OPS[op_type](_eval_node(node.operand))
    else:
        raise ValueError(f"Unsupported node type: {type(node)}")
