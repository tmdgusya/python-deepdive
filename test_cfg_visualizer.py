"""
Test suite for CFG Visualizer

Tests the basic block extraction and CFG construction logic
without requiring Graphviz installation.
"""

import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.cfg_visualizer import extract_basic_blocks, BasicBlock


def test_simple_if():
    """Test CFG extraction for simple if statement"""

    def simple_if(x):
        if x > 0:
            return x
        else:
            return -x

    blocks = extract_basic_blocks(simple_if)

    assert len(blocks) >= 3, f"Expected at least 3 blocks, got {len(blocks)}"

    entry_block = blocks[min(blocks.keys())]
    assert len(entry_block.successors) > 0, "Entry block should have successors"

    print(f"✓ simple_if: {len(blocks)} blocks extracted")
    for offset, block in sorted(blocks.items()):
        print(
            f"  Block {offset}: {len(block.instructions)} instructions, successors: {block.successors}"
        )


def test_for_loop():
    """Test CFG extraction for for loop"""

    def for_loop(n):
        total = 0
        for i in range(n):
            total += i
        return total

    blocks = extract_basic_blocks(for_loop)

    assert len(blocks) >= 3, f"Expected at least 3 blocks, got {len(blocks)}"

    has_for_iter = any(
        any(instr.opname == "FOR_ITER" for instr in block.instructions)
        for block in blocks.values()
    )
    assert has_for_iter, "Should have FOR_ITER instruction"

    print(f"✓ for_loop: {len(blocks)} blocks extracted")
    for offset, block in sorted(blocks.items()):
        print(
            f"  Block {offset}: {len(block.instructions)} instructions, successors: {block.successors}"
        )


def test_while_loop():
    """Test CFG extraction for while loop"""

    def while_loop(n):
        i = 0
        while i < n:
            i += 1
        return i

    blocks = extract_basic_blocks(while_loop)

    assert len(blocks) >= 3, f"Expected at least 3 blocks, got {len(blocks)}"

    has_jump = any(
        any("JUMP" in instr.opname for instr in block.instructions)
        for block in blocks.values()
    )
    assert has_jump, "Should have JUMP instructions"

    print(f"✓ while_loop: {len(blocks)} blocks extracted")
    for offset, block in sorted(blocks.items()):
        print(
            f"  Block {offset}: {len(block.instructions)} instructions, successors: {block.successors}"
        )


def test_nested_control_flow():
    """Test CFG extraction for nested control flow"""

    def nested(x, y):
        if x > 0:
            for i in range(y):
                if i % 2 == 0:
                    x += i
        return x

    blocks = extract_basic_blocks(nested)

    assert len(blocks) >= 5, (
        f"Expected at least 5 blocks for nested control flow, got {len(blocks)}"
    )

    print(f"✓ nested: {len(blocks)} blocks extracted")
    for offset, block in sorted(blocks.items()):
        print(
            f"  Block {offset}: {len(block.instructions)} instructions, successors: {block.successors}"
        )


def test_block_properties():
    """Test basic block properties"""

    def sample(x):
        if x > 0:
            return x
        return -x

    blocks = extract_basic_blocks(sample)

    for offset, block in blocks.items():
        assert isinstance(block, BasicBlock)
        assert block.start_offset == offset
        assert len(block.instructions) > 0
        assert block.end_offset >= block.start_offset

        for succ in block.successors:
            assert succ in blocks, f"Successor {succ} not in blocks"

    print(f"✓ block_properties: All blocks valid")


if __name__ == "__main__":
    print("Testing CFG Visualizer (without rendering)...\n")

    test_simple_if()
    print()

    test_for_loop()
    print()

    test_while_loop()
    print()

    test_nested_control_flow()
    print()

    test_block_properties()
    print()

    print("All tests passed!")
    print("\nNote: To generate actual CFG images, install Graphviz:")
    print("  sudo apt-get install graphviz")
    print("  # or on macOS: brew install graphviz")
