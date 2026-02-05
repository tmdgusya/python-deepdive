#!/usr/bin/env python3
"""
Test script for AST visualizer
Tests both successful visualization and error handling
"""

import sys
import os
from pathlib import Path

# Test code samples
test_code_simple = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

test_code_complex = """
class Calculator:
    def __init__(self, name):
        self.name = name
    
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        result = 0
        for i in range(b):
            result += a
        return result
"""


def test_import():
    """Test if ast_visualizer can be imported"""
    print("Test 1: Import module...")
    try:
        from tools.ast_visualizer import visualize_ast

        print("✓ Module imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_ast_parsing():
    """Test if AST parsing works"""
    print("\nTest 2: AST parsing...")
    try:
        import ast

        tree = ast.parse(test_code_simple)
        print(f"✓ AST parsed successfully: {len(list(ast.walk(tree)))} nodes")
        return True
    except Exception as e:
        print(f"✗ AST parsing failed: {e}")
        return False


def test_visualization():
    """Test visualization (may fail if graphviz binary not installed)"""
    print("\nTest 3: Visualization...")
    try:
        from tools.ast_visualizer import visualize_ast

        # Create output directory
        output_dir = Path("outputs/ast")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Try to visualize
        output_file = visualize_ast(
            test_code_simple,
            "outputs/ast/test_factorial.png",
            title="Factorial Function AST",
        )

        if Path(output_file).exists():
            print(f"✓ Visualization successful: {output_file}")
            print(f"  File size: {Path(output_file).stat().st_size} bytes")
            return True
        else:
            print(f"✗ Output file not created: {output_file}")
            return False

    except Exception as e:
        error_msg = str(e)
        if "graphviz" in error_msg.lower() or "dot" in error_msg.lower():
            print(f"⚠ Visualization failed (graphviz binary not installed): {e}")
            print(
                "  Note: Python graphviz package is installed, but system binary is missing"
            )
            print("  To fix: sudo apt install graphviz")
            return None  # Not a failure, just missing dependency
        else:
            print(f"✗ Visualization failed: {e}")
            return False


def test_node_colors():
    """Test node color mapping"""
    print("\nTest 4: Node color mapping...")
    try:
        from tools.ast_visualizer import get_node_color, NODE_COLORS
        import ast

        # Test various node types
        test_nodes = [
            (ast.Module(body=[], type_ignores=[]), "Module"),
            (
                ast.FunctionDef(name="test", args=None, body=[], decorator_list=[]),
                "FunctionDef",
            ),
            (ast.If(test=None, body=[], orelse=[]), "If"),
            (ast.BinOp(left=None, op=None, right=None), "BinOp"),
            (ast.Constant(value=42), "Constant"),
        ]

        all_ok = True
        for node, expected_type in test_nodes:
            color = get_node_color(node)
            if color:
                print(f"  ✓ {expected_type}: {color}")
            else:
                print(f"  ✗ {expected_type}: No color assigned")
                all_ok = False

        if all_ok:
            print(f"✓ All node types have colors ({len(NODE_COLORS)} types defined)")
            return True
        else:
            return False

    except Exception as e:
        print(f"✗ Node color test failed: {e}")
        return False


def test_node_labels():
    """Test node label generation"""
    print("\nTest 5: Node label generation...")
    try:
        from tools.ast_visualizer import get_node_label
        import ast

        # Test various node types with labels
        test_cases = [
            (ast.Name(id="variable", ctx=ast.Load()), "Name\\n'variable'"),
            (ast.Constant(value=42), "Constant\\n42"),
            (
                ast.FunctionDef(name="my_func", args=None, body=[], decorator_list=[]),
                "FunctionDef\\n'my_func'",
            ),
        ]

        all_ok = True
        for node, expected_pattern in test_cases:
            label = get_node_label(node)
            if expected_pattern.split("\\n")[0] in label:
                print(f"  ✓ {node.__class__.__name__}: {label}")
            else:
                print(
                    f"  ✗ {node.__class__.__name__}: Expected pattern '{expected_pattern}', got '{label}'"
                )
                all_ok = False

        if all_ok:
            print("✓ Node labels generated correctly")
            return True
        else:
            return False

    except Exception as e:
        print(f"✗ Node label test failed: {e}")
        return False


def main():
    print("=" * 60)
    print("AST Visualizer Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Import", test_import()))
    results.append(("AST Parsing", test_ast_parsing()))
    results.append(("Node Colors", test_node_colors()))
    results.append(("Node Labels", test_node_labels()))
    results.append(("Visualization", test_visualization()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)

    for name, result in results:
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⚠ SKIP"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")

    if failed > 0:
        print("\n⚠ Some tests failed!")
        return 1
    elif skipped > 0:
        print("\n⚠ Some tests skipped (graphviz binary not installed)")
        print("  Core functionality works, but image generation requires:")
        print("  sudo apt install graphviz")
        return 0
    else:
        print("\n✓ All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
