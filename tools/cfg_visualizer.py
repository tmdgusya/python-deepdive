"""
CFG Visualizer - Python 함수의 제어 흐름 그래프(CFG)를 시각화하는 도구

함수의 바이트코드를 분석하여 기본 블록(Basic Block)을 추출하고,
점프 명령어를 기반으로 제어 흐름을 파악하여 Graphviz로 시각화합니다.
"""

import dis
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple
import graphviz


# 점프 명령어 목록
JUMP_OPCODES = {
    "JUMP_FORWARD",
    "JUMP_BACKWARD",
    "JUMP_ABSOLUTE",
    "POP_JUMP_IF_FALSE",
    "POP_JUMP_IF_TRUE",
    "JUMP_IF_FALSE_OR_POP",
    "JUMP_IF_TRUE_OR_POP",
    "FOR_ITER",
    "JUMP_IF_NOT_EXC_MATCH",
    # Python 3.11+
    "POP_JUMP_FORWARD_IF_FALSE",
    "POP_JUMP_FORWARD_IF_TRUE",
    "POP_JUMP_BACKWARD_IF_FALSE",
    "POP_JUMP_BACKWARD_IF_TRUE",
    "POP_JUMP_FORWARD_IF_NONE",
    "POP_JUMP_BACKWARD_IF_NONE",
    "POP_JUMP_FORWARD_IF_NOT_NONE",
    "POP_JUMP_BACKWARD_IF_NOT_NONE",
}

# 블록 종료 명령어 (제어 흐름 변경)
BLOCK_END_OPCODES = JUMP_OPCODES | {
    "RETURN_VALUE",
    "RAISE_VARARGS",
    "RERAISE",
}


class BasicBlock:
    """기본 블록 - 순차적으로 실행되는 명령어 시퀀스"""

    def __init__(self, start_offset: int):
        self.start_offset = start_offset
        self.end_offset = start_offset
        self.instructions: List[dis.Instruction] = []
        self.successors: List[int] = []  # 후속 블록의 시작 오프셋
        self.is_conditional: Dict[int, bool] = {}  # 후속 블록이 조건부인지 여부

    def add_instruction(self, instr: dis.Instruction):
        """명령어 추가"""
        self.instructions.append(instr)
        self.end_offset = instr.offset

    def add_successor(self, offset: int, is_conditional: bool = False):
        """후속 블록 추가"""
        if offset not in self.successors:
            self.successors.append(offset)
            self.is_conditional[offset] = is_conditional

    def __repr__(self):
        return f"Block({self.start_offset}-{self.end_offset}, {len(self.instructions)} instrs)"


def extract_basic_blocks(func) -> Dict[int, BasicBlock]:
    """
    함수의 바이트코드에서 기본 블록 추출

    Args:
        func: Python 함수 객체

    Returns:
        오프셋을 키로 하는 기본 블록 딕셔너리
    """
    # 바이트코드 명령어 추출
    instructions = list(dis.get_instructions(func))
    if not instructions:
        return {}

    # 블록 시작 오프셋 찾기
    block_starts: Set[int] = {instructions[0].offset}  # 첫 명령어는 항상 블록 시작

    # 점프 대상과 점프 다음 명령어를 블록 시작으로 표시
    for i, instr in enumerate(instructions):
        # 점프 명령어의 대상
        if instr.opname in JUMP_OPCODES and instr.argval is not None:
            if isinstance(instr.argval, int):
                block_starts.add(instr.argval)

        # 점프 명령어 다음 명령어 (fall-through)
        if instr.opname in JUMP_OPCODES:
            if i + 1 < len(instructions):
                block_starts.add(instructions[i + 1].offset)

    # 블록 생성
    blocks: Dict[int, BasicBlock] = {}
    current_block = None

    for instr in instructions:
        # 새 블록 시작
        if instr.offset in block_starts:
            if current_block:
                blocks[current_block.start_offset] = current_block
            current_block = BasicBlock(instr.offset)

        # 현재 블록에 명령어 추가
        if current_block:
            current_block.add_instruction(instr)

    # 마지막 블록 추가
    if current_block:
        blocks[current_block.start_offset] = current_block

    # 블록 간 엣지 생성
    for offset, block in blocks.items():
        if not block.instructions:
            continue

        last_instr = block.instructions[-1]

        # 점프 명령어 처리
        if last_instr.opname in JUMP_OPCODES:
            # 점프 대상
            if isinstance(last_instr.argval, int):
                is_conditional = (
                    "IF" in last_instr.opname or last_instr.opname == "FOR_ITER"
                )
                block.add_successor(last_instr.argval, is_conditional=is_conditional)

            # Fall-through (조건부 점프의 경우)
            if "IF" in last_instr.opname or last_instr.opname == "FOR_ITER":
                # 다음 블록으로 fall-through
                next_offset = last_instr.offset + 2  # 명령어 크기는 2바이트
                # 실제 다음 블록 찾기
                for next_block_offset in sorted(blocks.keys()):
                    if next_block_offset > last_instr.offset:
                        block.add_successor(next_block_offset, is_conditional=True)
                        break

        # 무조건 점프가 아니고 RETURN/RAISE가 아니면 다음 블록으로 fall-through
        elif last_instr.opname not in {"RETURN_VALUE", "RAISE_VARARGS", "RERAISE"}:
            # 다음 블록 찾기
            for next_block_offset in sorted(blocks.keys()):
                if next_block_offset > offset:
                    block.add_successor(next_block_offset, is_conditional=False)
                    break

    return blocks


def format_instruction(instr: dis.Instruction) -> str:
    """명령어를 문자열로 포맷팅"""
    parts = [instr.opname]

    if instr.arg is not None:
        parts.append(str(instr.arg))

    if instr.argval is not None and instr.argval != instr.arg:
        if isinstance(instr.argval, str):
            argval_str = repr(instr.argval)
            if len(argval_str) > 20:
                argval_str = argval_str[:17] + "..."
            parts.append(f"({argval_str})")
        else:
            parts.append(f"({instr.argval})")

    return " ".join(parts)


def create_block_label(block: BasicBlock) -> str:
    """기본 블록의 레이블 생성"""
    lines = [f"Block {block.start_offset}"]
    lines.append("─" * 30)

    for instr in block.instructions:
        instr_str = format_instruction(instr)
        # 긴 명령어는 줄바꿈
        if len(instr_str) > 30:
            instr_str = instr_str[:27] + "..."
        lines.append(instr_str)

    return "\\n".join(lines)


def get_block_color(block: BasicBlock) -> str:
    """블록의 색상 결정"""
    if not block.instructions:
        return "#FAFAFA"

    first_instr = block.instructions[0]
    last_instr = block.instructions[-1]

    # Entry block (첫 블록)
    if first_instr.offset == 0 or first_instr.opname == "RESUME":
        return "#E3F2FD"  # 파란색 - 시작

    # Exit block (RETURN)
    if last_instr.opname == "RETURN_VALUE":
        return "#C8E6C9"  # 녹색 - 정상 종료

    # Exception block (RAISE)
    if last_instr.opname in {"RAISE_VARARGS", "RERAISE"}:
        return "#FFCDD2"  # 빨간색 - 예외

    # Conditional block (조건부 점프)
    if any("IF" in instr.opname for instr in block.instructions):
        return "#FFE0B2"  # 주황색 - 조건

    # Loop block (FOR_ITER)
    if any(instr.opname == "FOR_ITER" for instr in block.instructions):
        return "#FFF9C4"  # 노란색 - 반복

    # Default
    return "#F5F5F5"  # 회색 - 일반


def visualize_cfg(
    func,
    output: str,
    title: Optional[str] = None,
) -> str:
    """
    함수의 CFG를 시각화하여 이미지로 저장

    Args:
        func: Python 함수 객체
        output: 출력 파일 경로 (png, svg, pdf 등)
        title: 그래프 제목 (선택)

    Returns:
        생성된 이미지 파일 경로

    Raises:
        ValueError: 함수가 아닌 객체 전달
        Exception: 그래프 생성 실패

    Example:
        >>> def example(x):
        ...     if x > 0:
        ...         return x
        ...     else:
        ...         return -x
        >>> visualize_cfg(example, 'outputs/cfg/example.png')
        'outputs/cfg/example.png'
    """
    # 함수 검증
    if not callable(func):
        raise ValueError(f"Expected a function, got {type(func)}")

    # 기본 블록 추출
    blocks = extract_basic_blocks(func)

    if not blocks:
        raise ValueError(f"No bytecode found for function {func.__name__}")

    # 출력 경로 처리
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 파일 형식 추출
    format_ext = output_path.suffix.lstrip(".")
    if not format_ext:
        format_ext = "png"

    # Graphviz 그래프 생성
    graph = graphviz.Digraph(
        name="CFG",
        format=format_ext,
        graph_attr={
            "rankdir": "TB",  # Top to Bottom
            "bgcolor": "white",
            "dpi": "150",
        },
        node_attr={
            "fontsize": "10",
            "fontname": "monospace",
            "shape": "box",
        },
        edge_attr={
            "fontsize": "9",
        },
    )

    # 제목 추가
    if title:
        graph.attr(label=title, labelloc="t", fontsize="14", fontname="monospace")
    else:
        graph.attr(
            label=f"CFG: {func.__name__}()",
            labelloc="t",
            fontsize="14",
            fontname="monospace",
        )

    # 블록 노드 추가
    for offset, block in blocks.items():
        node_id = f"block_{offset}"
        label = create_block_label(block)
        color = get_block_color(block)

        graph.node(
            node_id,
            label,
            style="filled",
            fillcolor=color,
        )

    # 엣지 추가
    for offset, block in blocks.items():
        node_id = f"block_{offset}"

        for succ_offset in block.successors:
            succ_id = f"block_{succ_offset}"
            is_conditional = block.is_conditional.get(succ_offset, False)

            # 조건부 엣지는 다른 스타일
            if is_conditional:
                # 조건부 엣지 - 점선, 레이블 추가
                last_instr = block.instructions[-1] if block.instructions else None
                if last_instr:
                    # True/False 분기 판단
                    if "IF_TRUE" in last_instr.opname:
                        label = "True" if succ_offset == last_instr.argval else "False"
                    elif "IF_FALSE" in last_instr.opname:
                        label = "False" if succ_offset == last_instr.argval else "True"
                    elif last_instr.opname == "FOR_ITER":
                        label = "iter" if succ_offset == last_instr.argval else "next"
                    else:
                        # 일반 조건부 점프
                        label = "jump" if succ_offset == last_instr.argval else "fall"

                    graph.edge(
                        node_id,
                        succ_id,
                        label=label,
                        style="dashed",
                        color="#FF9800",
                    )
                else:
                    graph.edge(node_id, succ_id, style="dashed", color="#FF9800")
            else:
                # 무조건 엣지 - 실선
                graph.edge(node_id, succ_id, color="#666666")

    # 파일 저장
    output_without_ext = str(output_path.with_suffix(""))
    try:
        graph.render(output_without_ext, cleanup=True)
    except Exception as e:
        raise Exception(f"Failed to render graph: {e}")

    return str(output_path)


if __name__ == "__main__":
    # 테스트 코드
    def test_if(x):
        if x > 0:
            return x
        else:
            return -x

    def test_loop(n):
        total = 0
        for i in range(n):
            total += i
        return total

    def test_while(n):
        i = 0
        while i < n:
            i += 1
        return i

    print("Testing CFG Visualizer...")

    # Test 1: if문
    output1 = visualize_cfg(
        test_if, "outputs/cfg/test_if.png", title="CFG: if statement"
    )
    print(f"✓ Generated: {output1}")

    # Test 2: for문
    output2 = visualize_cfg(
        test_loop, "outputs/cfg/test_loop.png", title="CFG: for loop"
    )
    print(f"✓ Generated: {output2}")

    # Test 3: while문
    output3 = visualize_cfg(
        test_while, "outputs/cfg/test_while.png", title="CFG: while loop"
    )
    print(f"✓ Generated: {output3}")
