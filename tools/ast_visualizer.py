"""
AST Visualizer - Python 코드의 AST를 시각화하는 도구

Python 코드를 파싱하여 AST(Abstract Syntax Tree)를 생성하고,
Graphviz를 사용하여 시각적인 트리 다이어그램으로 변환합니다.
"""

import ast
from pathlib import Path
from typing import Optional
import graphviz


# 노드 타입별 색상 매핑
NODE_COLORS = {
    # Module, Function, Class - 파란색 계열
    "Module": "#E3F2FD",
    "FunctionDef": "#BBDEFB",
    "AsyncFunctionDef": "#BBDEFB",
    "ClassDef": "#90CAF9",
    "Lambda": "#64B5F6",
    # Statements - 주황색 계열
    "If": "#FFE0B2",
    "For": "#FFCC80",
    "While": "#FFB74D",
    "Return": "#FFA726",
    "Assign": "#FF9800",
    "AugAssign": "#FB8C00",
    "AnnAssign": "#F57C00",
    "With": "#FFE0B2",
    "AsyncWith": "#FFE0B2",
    "AsyncFor": "#FFCC80",
    "Try": "#FFAB91",
    "Raise": "#FF7043",
    "Assert": "#FF5722",
    "Import": "#FFCCBC",
    "ImportFrom": "#FFCCBC",
    "Break": "#BCAAA4",
    "Continue": "#BCAAA4",
    "Pass": "#D7CCC8",
    "Delete": "#FF8A65",
    "Expr": "#FFE0B2",
    # Expressions - 녹색 계열
    "BinOp": "#C8E6C9",
    "UnaryOp": "#A5D6A7",
    "BoolOp": "#81C784",
    "Compare": "#66BB6A",
    "Call": "#4CAF50",
    "Attribute": "#43A047",
    "Subscript": "#388E3C",
    "Name": "#C8E6C9",
    "List": "#A5D6A7",
    "Tuple": "#A5D6A7",
    "Dict": "#81C784",
    "Set": "#81C784",
    "ListComp": "#66BB6A",
    "DictComp": "#66BB6A",
    "SetComp": "#66BB6A",
    "GeneratorExp": "#66BB6A",
    "IfExp": "#4CAF50",
    "Starred": "#43A047",
    "Yield": "#388E3C",
    "YieldFrom": "#388E3C",
    "Await": "#2E7D32",
    "FormattedValue": "#A5D6A7",
    "JoinedStr": "#A5D6A7",
    # Literals - 회색 계열
    "Constant": "#E0E0E0",
    "Num": "#E0E0E0",
    "Str": "#E0E0E0",
    "Bytes": "#BDBDBD",
    "NameConstant": "#9E9E9E",
    "Ellipsis": "#757575",
    # 기타
    "arguments": "#F5F5F5",
    "arg": "#EEEEEE",
    "keyword": "#E0E0E0",
    "alias": "#D6D6D6",
}

# 기본 색상
DEFAULT_COLOR = "#FAFAFA"


def get_node_label(node: ast.AST) -> str:
    """AST 노드의 레이블 생성"""
    node_type = node.__class__.__name__

    # 노드 타입별 추가 정보
    if isinstance(node, ast.Name):
        return f"{node_type}\\n'{node.id}'"
    elif isinstance(node, ast.Constant):
        value = repr(node.value)
        if len(value) > 20:
            value = value[:17] + "..."
        return f"{node_type}\\n{value}"
    elif isinstance(node, (ast.Num, ast.Str)):
        # Python 3.7 이하 호환성
        value = repr(node.n if isinstance(node, ast.Num) else node.s)
        if len(value) > 20:
            value = value[:17] + "..."
        return f"{node_type}\\n{value}"
    elif isinstance(node, ast.FunctionDef):
        return f"{node_type}\\n'{node.name}'"
    elif isinstance(node, ast.ClassDef):
        return f"{node_type}\\n'{node.name}'"
    elif isinstance(node, ast.Attribute):
        return f"{node_type}\\n'.{node.attr}'"
    elif isinstance(node, ast.BinOp):
        op = node.op.__class__.__name__
        return f"{node_type}\\n{op}"
    elif isinstance(node, ast.UnaryOp):
        op = node.op.__class__.__name__
        return f"{node_type}\\n{op}"
    elif isinstance(node, ast.BoolOp):
        op = node.op.__class__.__name__
        return f"{node_type}\\n{op}"
    elif isinstance(node, ast.Compare):
        ops = ", ".join(op.__class__.__name__ for op in node.ops)
        return f"{node_type}\\n{ops}"
    elif isinstance(node, ast.arg):
        return f"{node_type}\\n'{node.arg}'"
    elif isinstance(node, ast.keyword):
        arg_name = node.arg if node.arg else "**"
        return f"{node_type}\\n'{arg_name}'"
    elif isinstance(node, ast.alias):
        name = node.name
        if node.asname:
            name += f" as {node.asname}"
        return f"{node_type}\\n'{name}'"

    return node_type


def get_node_color(node: ast.AST) -> str:
    """AST 노드의 색상 반환"""
    node_type = node.__class__.__name__
    return NODE_COLORS.get(node_type, DEFAULT_COLOR)


def add_ast_nodes(
    graph: graphviz.Digraph,
    node: ast.AST,
    parent_id: Optional[str] = None,
    counter: list = [0],
) -> str:
    """
    AST 노드를 그래프에 재귀적으로 추가

    Args:
        graph: Graphviz 그래프 객체
        node: AST 노드
        parent_id: 부모 노드 ID
        counter: 노드 ID 생성용 카운터

    Returns:
        현재 노드의 ID
    """
    # 현재 노드 ID 생성
    counter[0] += 1
    node_id = f"node_{counter[0]}"

    # 노드 레이블과 색상
    label = get_node_label(node)
    color = get_node_color(node)

    # 노드 추가
    graph.node(
        node_id,
        label,
        style="filled",
        fillcolor=color,
        shape="box",
        fontname="monospace",
    )

    # 부모와 연결
    if parent_id:
        graph.edge(parent_id, node_id)

    # 자식 노드 처리
    for field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    add_ast_nodes(graph, item, node_id, counter)
        elif isinstance(value, ast.AST):
            add_ast_nodes(graph, value, node_id, counter)

    return node_id


def visualize_ast(
    code: str,
    output: str,
    title: Optional[str] = None,
) -> str:
    """
    Python 코드의 AST를 시각화하여 이미지로 저장

    Args:
        code: Python 소스 코드 문자열
        output: 출력 파일 경로 (png, svg, pdf 등)
        title: 그래프 제목 (선택)

    Returns:
        생성된 이미지 파일 경로

    Raises:
        SyntaxError: 코드 파싱 실패
        Exception: 그래프 생성 실패

    Example:
        >>> code = '''
        ... def factorial(n):
        ...     if n <= 1:
        ...         return 1
        ...     return n * factorial(n - 1)
        ... '''
        >>> visualize_ast(code, 'outputs/ast/factorial.png')
        'outputs/ast/factorial.png'
    """
    # 코드 파싱
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SyntaxError(f"Failed to parse code: {e}")

    # 출력 경로 처리
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 파일 형식 추출
    format_ext = output_path.suffix.lstrip(".")
    if not format_ext:
        format_ext = "png"

    # Graphviz 그래프 생성
    graph = graphviz.Digraph(
        name="AST",
        format=format_ext,
        graph_attr={
            "rankdir": "TB",  # Top to Bottom
            "bgcolor": "white",
            "dpi": "150",
        },
        node_attr={
            "fontsize": "10",
        },
        edge_attr={
            "color": "#666666",
        },
    )

    # 제목 추가
    if title:
        graph.attr(label=title, labelloc="t", fontsize="14", fontname="monospace")

    # AST 노드 추가
    counter = [0]
    add_ast_nodes(graph, tree, None, counter)

    # 파일 저장
    output_without_ext = str(output_path.with_suffix(""))
    try:
        graph.render(output_without_ext, cleanup=True)
    except Exception as e:
        raise Exception(f"Failed to render graph: {e}")

    return str(output_path)


if __name__ == "__main__":
    # 테스트 코드
    test_code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

    print("Testing AST Visualizer...")
    output_file = visualize_ast(
        test_code, "outputs/ast/test_factorial.png", title="Factorial Function AST"
    )
    print(f"✓ Generated: {output_file}")
