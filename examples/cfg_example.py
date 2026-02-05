"""
CFG Visualizer Example

Demonstrates how to use the CFG visualizer to analyze control flow
in Python functions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.cfg_visualizer import visualize_cfg, extract_basic_blocks


def example_if(x):
    """Simple if-else statement"""
    if x > 0:
        return x
    else:
        return -x


def example_for(n):
    """For loop with accumulation"""
    total = 0
    for i in range(n):
        total += i
    return total


def example_while(n):
    """While loop with counter"""
    i = 0
    while i < n:
        i += 1
    return i


def example_nested(x, y):
    """Nested control flow"""
    if x > 0:
        for i in range(y):
            if i % 2 == 0:
                x += i
    return x


def example_complex(n):
    """Complex control flow with multiple paths"""
    result = 0
    for i in range(n):
        if i % 2 == 0:
            result += i
        elif i % 3 == 0:
            result -= i
        else:
            result *= 2
    return result


if __name__ == "__main__":
    print("CFG Visualizer Examples\n")
    print("=" * 60)

    examples = [
        (example_if, "Simple if-else"),
        (example_for, "For loop"),
        (example_while, "While loop"),
        (example_nested, "Nested control flow"),
        (example_complex, "Complex control flow"),
    ]

    for func, description in examples:
        print(f"\n{description}: {func.__name__}")
        print("-" * 60)

        blocks = extract_basic_blocks(func)
        print(f"Basic blocks: {len(blocks)}")

        for offset, block in sorted(blocks.items()):
            print(
                f"  Block {offset:3d}: {len(block.instructions):2d} instructions -> {block.successors}"
            )

        try:
            output_path = f"outputs/cfg/{func.__name__}.png"
            visualize_cfg(func, output_path, title=f"CFG: {description}")
            print(f"✓ Generated: {output_path}")
        except Exception as e:
            print(f"✗ Failed to generate image: {e}")
            print("  (Install Graphviz to enable image generation)")

    print("\n" + "=" * 60)
    print("Done!")
