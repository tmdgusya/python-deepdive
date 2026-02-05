"""
Bytecode Tracer - 파이썬 바이트코드 실행 시뮬레이션 및 스택 상태 추적

바이트코드 명령어별로 스택 상태 변화를 시뮬레이션하고
rich 테이블로 시각화합니다.

주의: 실제 코드를 실행하지 않고 시뮬레이션만 수행합니다.
"""

import dis
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Optional

from rich.console import Console
from rich.table import Table


@dataclass
class ExecutionStep:
    """단일 바이트코드 명령어 실행 단계"""

    offset: int
    opcode: str
    arg: str
    stack_before: list
    stack_after: list
    locals_snapshot: dict


class StackSimulator:
    """
    바이트코드 스택 시뮬레이터

    각 명령어의 스택 효과를 시뮬레이션합니다.
    실제 값 대신 심볼릭 값을 사용합니다.
    """

    def __init__(self, func: Callable, args: tuple = (), kwargs: Optional[dict] = None):
        self.func = func
        self.code = func.__code__
        self.args = args
        self.kwargs = kwargs or {}

        # 스택과 지역변수 초기화
        self.stack: list = []
        self.locals: dict = {}

        # 함수 인자로 지역변수 초기화
        self._init_locals()

        # 상수 테이블
        self.consts = self.code.co_consts
        # 이름 테이블 (전역 변수)
        self.names = self.code.co_names
        # 지역변수 이름 테이블
        self.varnames = self.code.co_varnames

        # 임시 결과 카운터 (연산 결과 표현용)
        self._result_counter = 0

    def _init_locals(self):
        """함수 인자로 지역변수 초기화"""
        sig = inspect.signature(self.func)
        params = list(sig.parameters.keys())

        # 위치 인자 바인딩
        for i, arg in enumerate(self.args):
            if i < len(params):
                self.locals[params[i]] = arg

        # 키워드 인자 바인딩
        for key, value in self.kwargs.items():
            self.locals[key] = value

        # 기본값 바인딩 (아직 설정되지 않은 파라미터)
        for param_name, param in sig.parameters.items():
            if (
                param_name not in self.locals
                and param.default is not inspect.Parameter.empty
            ):
                self.locals[param_name] = param.default

    def _next_result(self, op: str = "result") -> str:
        """연산 결과를 위한 심볼릭 이름 생성"""
        self._result_counter += 1
        return f"<{op}_{self._result_counter}>"

    def _get_stack_copy(self) -> list:
        """현재 스택의 복사본 반환"""
        return list(self.stack)

    def _get_locals_copy(self) -> dict:
        """현재 지역변수의 복사본 반환"""
        return dict(self.locals)

    def simulate_instruction(self, inst: dis.Instruction) -> ExecutionStep:
        """
        단일 명령어 시뮬레이션

        Args:
            inst: dis.Instruction 객체

        Returns:
            ExecutionStep 객체
        """
        stack_before = self._get_stack_copy()
        opname = inst.opname

        # 인자 문자열 준비
        arg_str = str(inst.argrepr) if inst.argrepr else ""

        # 명령어별 스택 조작
        if opname == "RESUME":
            pass  # 스택 변화 없음

        elif opname == "LOAD_CONST":
            # 상수 푸시
            const_val = self.consts[inst.arg] if inst.arg is not None else None
            self.stack.append(const_val)

        elif opname == "LOAD_FAST":
            # 지역변수 푸시
            if inst.arg is not None and inst.arg < len(self.varnames):
                var_name = self.varnames[inst.arg]
                val = self.locals.get(var_name, f"<{var_name}>")
                self.stack.append(val)

        elif opname == "LOAD_FAST_LOAD_FAST":
            # Python 3.13+ 두 지역변수를 한번에 푸시
            # argrepr은 "a, b" 형태
            if inst.argrepr:
                var_names = [v.strip() for v in inst.argrepr.split(",")]
                for var_name in var_names:
                    val = self.locals.get(var_name, f"<{var_name}>")
                    self.stack.append(val)
            elif inst.arg is not None:
                # arg 바이트에서 두 변수 인덱스 추출 (하위/상위 4비트)
                idx1 = inst.arg & 0x0F
                idx2 = (inst.arg >> 4) & 0x0F
                for idx in [idx1, idx2]:
                    if idx < len(self.varnames):
                        var_name = self.varnames[idx]
                        val = self.locals.get(var_name, f"<{var_name}>")
                        self.stack.append(val)

        elif opname == "LOAD_GLOBAL":
            # 전역 변수 푸시 (+ NULL for method call in 3.11+)
            # argrepr에서 이름 추출
            name = inst.argrepr.split()[0] if inst.argrepr else "global"
            self.stack.append(f"<{name}>")
            # Python 3.11+에서는 LOAD_GLOBAL이 NULL도 푸시 가능
            if "+ NULL" in str(inst.argrepr):
                self.stack.append(None)  # NULL

        elif opname == "STORE_FAST":
            # 스택에서 팝하여 지역변수에 저장
            if inst.arg is not None and inst.arg < len(self.varnames) and self.stack:
                var_name = self.varnames[inst.arg]
                val = self.stack.pop()
                self.locals[var_name] = val

        elif opname == "STORE_FAST_STORE_FAST":
            # Python 3.13+ 두 변수를 한번에 저장
            if inst.argrepr:
                var_names = [v.strip() for v in inst.argrepr.split(",")]
                for var_name in reversed(var_names):  # 스택은 LIFO
                    if self.stack:
                        val = self.stack.pop()
                        self.locals[var_name] = val

        elif opname == "BINARY_OP":
            # 이항 연산: 두 값을 팝하고 결과 푸시
            if len(self.stack) >= 2:
                right = self.stack.pop()
                left = self.stack.pop()
                op_symbol = inst.argrepr if inst.argrepr else "op"

                # 값이 숫자면 실제 계산 시도
                try:
                    if isinstance(left, (int, float)) and isinstance(
                        right, (int, float)
                    ):
                        if op_symbol == "+":
                            result = left + right
                        elif op_symbol == "-":
                            result = left - right
                        elif op_symbol == "*":
                            result = left * right
                        elif op_symbol == "/":
                            result = left / right
                        elif op_symbol == "//":
                            result = left // right
                        elif op_symbol == "%":
                            result = left % right
                        elif op_symbol == "**":
                            result = left**right
                        else:
                            result = f"({left} {op_symbol} {right})"
                    else:
                        result = f"({left} {op_symbol} {right})"
                except:
                    result = f"({left} {op_symbol} {right})"

                self.stack.append(result)

        elif opname == "UNARY_NEGATIVE":
            if self.stack:
                val = self.stack.pop()
                if isinstance(val, (int, float)):
                    self.stack.append(-val)
                else:
                    self.stack.append(f"(-{val})")

        elif opname == "UNARY_NOT":
            if self.stack:
                val = self.stack.pop()
                self.stack.append(f"(not {val})")

        elif opname in ("COMPARE_OP", "CONTAINS_OP", "IS_OP"):
            # 비교 연산: 두 값을 팝하고 결과 푸시
            if len(self.stack) >= 2:
                right = self.stack.pop()
                left = self.stack.pop()
                op_str = inst.argrepr if inst.argrepr else "cmp"
                self.stack.append(f"({left} {op_str} {right})")

        elif opname == "CALL":
            # 함수 호출: n개 인자와 callable을 팝, 결과 푸시
            n_args = inst.arg if inst.arg is not None else 0
            args = []
            for _ in range(n_args):
                if self.stack:
                    args.insert(0, self.stack.pop())

            # NULL 체크 (메서드 호출용)
            if self.stack and self.stack[-1] is None:
                self.stack.pop()  # NULL 제거

            # callable 팝
            if self.stack:
                func = self.stack.pop()
                args_str = ", ".join(str(a) for a in args)
                self.stack.append(f"{func}({args_str})")

        elif opname == "CALL_FUNCTION":
            # 레거시 함수 호출 (Python 3.10 이하)
            n_args = inst.arg if inst.arg is not None else 0
            args = []
            for _ in range(n_args):
                if self.stack:
                    args.insert(0, self.stack.pop())
            if self.stack:
                func = self.stack.pop()
                args_str = ", ".join(str(a) for a in args)
                self.stack.append(f"{func}({args_str})")

        elif opname == "RETURN_VALUE":
            # 스택 탑을 반환값으로 사용 (스택에서 팝)
            if self.stack:
                self.stack.pop()

        elif opname == "RETURN_CONST":
            # Python 3.12+ 상수 직접 반환
            pass  # 스택 변화 없음 (상수가 직접 반환됨)

        elif opname == "POP_TOP":
            # 스택 탑 제거
            if self.stack:
                self.stack.pop()

        elif opname == "DUP_TOP":
            # 스택 탑 복제
            if self.stack:
                self.stack.append(self.stack[-1])

        elif opname == "BUILD_LIST":
            # 리스트 생성
            n = inst.arg if inst.arg else 0
            items = []
            for _ in range(n):
                if self.stack:
                    items.insert(0, self.stack.pop())
            self.stack.append(items)

        elif opname == "BUILD_TUPLE":
            # 튜플 생성
            n = inst.arg if inst.arg else 0
            items = []
            for _ in range(n):
                if self.stack:
                    items.insert(0, self.stack.pop())
            self.stack.append(tuple(items))

        elif opname == "BUILD_MAP":
            # 딕셔너리 생성
            n = inst.arg if inst.arg else 0
            d = {}
            for _ in range(n):
                if len(self.stack) >= 2:
                    val = self.stack.pop()
                    key = self.stack.pop()
                    d[key] = val
            self.stack.append(d)

        elif opname in (
            "JUMP_FORWARD",
            "JUMP_BACKWARD",
            "JUMP_IF_TRUE_OR_POP",
            "JUMP_IF_FALSE_OR_POP",
            "POP_JUMP_IF_TRUE",
            "POP_JUMP_IF_FALSE",
            "POP_JUMP_IF_NONE",
            "POP_JUMP_IF_NOT_NONE",
        ):
            # 점프 명령어: 조건부 점프는 스택을 팝할 수 있음
            if "POP_JUMP" in opname and self.stack:
                self.stack.pop()

        elif opname == "GET_ITER":
            # 이터레이터 획득
            if self.stack:
                val = self.stack.pop()
                self.stack.append(f"iter({val})")

        elif opname == "FOR_ITER":
            # 이터레이터 다음 값
            self.stack.append("<next_item>")

        elif opname == "PUSH_NULL":
            # Python 3.11+ NULL 푸시
            self.stack.append(None)

        elif opname == "COPY":
            # 스택 복사
            n = inst.arg if inst.arg else 1
            if len(self.stack) >= n:
                self.stack.append(self.stack[-n])

        elif opname == "SWAP":
            # 스택 교환
            n = inst.arg if inst.arg else 2
            if len(self.stack) >= n:
                self.stack[-1], self.stack[-n] = self.stack[-n], self.stack[-1]

        else:
            # 알려지지 않은 명령어: dis.stack_effect 사용
            try:
                effect = dis.stack_effect(inst.opcode, inst.arg or 0)
                if effect < 0:
                    for _ in range(-effect):
                        if self.stack:
                            self.stack.pop()
                elif effect > 0:
                    for _ in range(effect):
                        self.stack.append(f"<{opname}_result>")
            except:
                pass  # 스택 효과를 알 수 없음

        stack_after = self._get_stack_copy()

        return ExecutionStep(
            offset=inst.offset,
            opcode=opname,
            arg=arg_str,
            stack_before=stack_before,
            stack_after=stack_after,
            locals_snapshot=self._get_locals_copy(),
        )


def trace_execution(
    func: Callable,
    args: tuple = (),
    kwargs: Optional[dict] = None,
    show_table: bool = True,
) -> list[ExecutionStep]:
    """
    함수의 바이트코드 실행을 시뮬레이션하고 각 단계의 스택 상태 추적

    Args:
        func: Python 함수 객체
        args: 함수 인자 (위치 인자)
        kwargs: 키워드 인자
        show_table: 테이블 출력 여부

    Returns:
        각 단계의 상태를 담은 ExecutionStep 리스트

    Example:
        >>> def add(a, b):
        ...     return a + b
        >>> steps = trace_execution(add, (1, 2))
    """
    if kwargs is None:
        kwargs = {}

    # 시뮬레이터 생성
    simulator = StackSimulator(func, args, kwargs)

    # 바이트코드 명령어 추출
    instructions = list(dis.get_instructions(func))

    # 각 명령어 시뮬레이션
    steps: list[ExecutionStep] = []
    for inst in instructions:
        step = simulator.simulate_instruction(inst)
        steps.append(step)

    # 테이블 출력
    if show_table:
        _print_trace_table(func, args, kwargs, steps)

    return steps


def _format_stack(stack: list) -> str:
    """스택을 문자열로 포맷팅"""
    if not stack:
        return "[]"

    items = []
    for item in stack:
        if item is None:
            items.append("NULL")
        elif isinstance(item, str) and item.startswith("<"):
            items.append(item)
        else:
            items.append(repr(item))

    return f"[{', '.join(items)}]"


def _print_trace_table(
    func: Callable, args: tuple, kwargs: dict, steps: list[ExecutionStep]
) -> None:
    """rich 테이블로 추적 결과 출력"""
    console = Console()

    # 함수 정보 헤더
    func_name = func.__name__
    args_str = ", ".join(repr(a) for a in args)
    kwargs_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    all_args = ", ".join(filter(None, [args_str, kwargs_str]))

    console.print(f"\n[bold cyan]Bytecode Trace:[/bold cyan] {func_name}({all_args})")
    console.print(f"[dim]Code object: {func.__code__.co_filename}[/dim]\n")

    # 테이블 생성
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Offset", justify="right", style="cyan", width=7)
    table.add_column("Opcode", style="green", width=22)
    table.add_column("Arg", style="yellow", width=15)
    table.add_column("Stack Before", style="blue", width=30)
    table.add_column("Stack After", style="blue", width=30)

    for step in steps:
        table.add_row(
            str(step.offset),
            step.opcode,
            step.arg or "",
            _format_stack(step.stack_before),
            _format_stack(step.stack_after),
        )

    console.print(table)

    # 최종 지역변수 상태
    if steps:
        final_locals = steps[-1].locals_snapshot
        if final_locals:
            console.print("\n[bold cyan]Final Locals:[/bold cyan]")
            for name, value in final_locals.items():
                console.print(f"  {name} = {value!r}")


def trace_code(
    code: str,
    func_name: str = "main",
    args: tuple = (),
    kwargs: Optional[dict] = None,
    show_table: bool = True,
) -> list[ExecutionStep]:
    """
    소스 코드 문자열에서 함수를 추출하여 추적

    Args:
        code: Python 소스 코드 문자열
        func_name: 추적할 함수 이름
        args: 함수 인자
        kwargs: 키워드 인자
        show_table: 테이블 출력 여부

    Returns:
        각 단계의 상태를 담은 ExecutionStep 리스트
    """
    # 코드 컴파일 및 실행하여 함수 객체 획득
    namespace: dict = {}
    exec(code, namespace)

    if func_name not in namespace:
        raise ValueError(f"Function '{func_name}' not found in code")

    func = namespace[func_name]
    return trace_execution(func, args, kwargs, show_table)


if __name__ == "__main__":
    # 테스트 함수들
    def simple_add(a, b):
        return a + b

    def with_locals(a, b):
        x = a + b
        y = x * 2
        return y

    def with_const(n):
        return n + 10

    console = Console()

    console.print("[bold underline]Test 1: Simple Addition[/bold underline]")
    trace_execution(simple_add, (1, 2))

    console.print("\n" + "=" * 80 + "\n")

    console.print("[bold underline]Test 2: With Local Variables[/bold underline]")
    trace_execution(with_locals, (3, 4))

    console.print("\n" + "=" * 80 + "\n")

    console.print("[bold underline]Test 3: With Constant[/bold underline]")
    trace_execution(with_const, (5,))
