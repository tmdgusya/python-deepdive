"""
스택 애니메이터: 바이트코드 실행을 ASCII 박스로 시각화

바이트코드 실행의 각 스텝을 터미널에서 애니메이션으로 표시합니다.
프레임 스택, 평가 스택, 지역변수 상태를 시각화합니다.
"""

import dis
import time
from typing import Any, Callable, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text


class StackAnimator:
    """바이트코드 실행 스택 애니메이터"""

    def __init__(self, func: Callable, args: tuple = (), delay: float = 0.5):
        """
        Args:
            func: 시각화할 Python 함수
            args: 함수 인자
            delay: 스텝 간 지연 시간 (초)
        """
        self.func = func
        self.args = args
        self.delay = delay
        self.console = Console()

        # 바이트코드 명령어 추출
        self.instructions = list(dis.get_instructions(func))

        # 초기 상태
        self.stack = []
        self.locals = {}
        self.step = 0

        # 함수 인자를 지역변수로 초기화
        code = func.__code__
        for i, arg_name in enumerate(code.co_varnames[: code.co_argcount]):
            if i < len(args):
                self.locals[arg_name] = args[i]

    def _simulate_instruction(self, instr: dis.Instruction) -> bool:
        """
        명령어 실행 시뮬레이션

        Returns:
            True if execution should continue, False if RETURN_VALUE
        """
        opname = instr.opname
        arg = instr.argval

        # LOAD 명령어들
        if opname == "LOAD_FAST":
            self.stack.append(self.locals.get(arg, f"<{arg}>"))
        elif opname == "LOAD_FAST_LOAD_FAST":
            # Python 3.11+ specialized opcode: loads two variables
            if isinstance(arg, tuple) and len(arg) == 2:
                self.stack.append(self.locals.get(arg[0], f"<{arg[0]}>"))
                self.stack.append(self.locals.get(arg[1], f"<{arg[1]}>"))
        elif opname == "LOAD_CONST":
            self.stack.append(arg)
        elif opname == "LOAD_GLOBAL":
            self.stack.append(f"<global:{arg}>")

        # STORE 명령어들
        elif opname == "STORE_FAST":
            if self.stack:
                self.locals[arg] = self.stack.pop()

        # 이항 연산자
        elif opname == "BINARY_OP":
            if len(self.stack) >= 2:
                right = self.stack.pop()
                left = self.stack.pop()
                # 실제 연산 수행 (가능한 경우)
                try:
                    if arg == "+" or arg == 0:  # ADD
                        result = left + right
                    elif arg == "-" or arg == 1:  # SUBTRACT
                        result = left - right
                    elif arg == "*" or arg == 5:  # MULTIPLY
                        result = left * right
                    elif arg == "/" or arg == 11:  # TRUE_DIVIDE
                        result = left / right
                    else:
                        result = f"<{left} {arg} {right}>"
                    self.stack.append(result)
                except:
                    self.stack.append(f"<{left} op {right}>")

        # 비교 연산자
        elif opname == "COMPARE_OP":
            if len(self.stack) >= 2:
                right = self.stack.pop()
                left = self.stack.pop()
                try:
                    if arg == "<":
                        result = left < right
                    elif arg == "<=":
                        result = left <= right
                    elif arg == "==":
                        result = left == right
                    elif arg == "!=":
                        result = left != right
                    elif arg == ">":
                        result = left > right
                    elif arg == ">=":
                        result = left >= right
                    else:
                        result = f"<{left} {arg} {right}>"
                    self.stack.append(result)
                except:
                    self.stack.append(f"<{left} cmp {right}>")

        # 단항 연산자
        elif opname == "UNARY_NOT":
            if self.stack:
                value = self.stack.pop()
                self.stack.append(not value)
        elif opname == "UNARY_NEGATIVE":
            if self.stack:
                value = self.stack.pop()
                self.stack.append(-value)

        # 함수 호출 (간단한 시뮬레이션)
        elif opname == "CALL":
            # arg는 인자 개수
            num_args = arg if isinstance(arg, int) else 0
            args_list = []
            for _ in range(num_args):
                if self.stack:
                    args_list.insert(0, self.stack.pop())
            if self.stack:
                func = self.stack.pop()
                self.stack.append(f"<call {func}({', '.join(map(str, args_list))})>")

        # 반환
        elif opname == "RETURN_VALUE":
            return False

        # POP_TOP
        elif opname == "POP_TOP":
            if self.stack:
                self.stack.pop()

        # 점프 명령어들 (시뮬레이션에서는 무시)
        elif opname.startswith("JUMP") or opname.startswith("POP_JUMP"):
            pass

        return True

    def _create_stack_visual(self) -> Table:
        """스택 상태를 ASCII 박스로 시각화"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Stack", style="cyan")

        if not self.stack:
            table.add_row("[dim]<empty>[/dim]")
        else:
            # 스택은 위에서 아래로 (TOP이 위)
            for i in range(len(self.stack) - 1, -1, -1):
                value = self.stack[i]
                marker = " ← TOP" if i == len(self.stack) - 1 else ""
                table.add_row(f"┌─────────────┐")
                table.add_row(f"│ {str(value):^11} │{marker}")
                table.add_row(f"└─────────────┘")

        return table

    def _create_locals_visual(self) -> Table:
        """지역변수를 테이블로 시각화"""
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Variable", style="green")
        table.add_column("Value", style="yellow")

        if not self.locals:
            table.add_row("[dim]<none>[/dim]", "")
        else:
            for name, value in sorted(self.locals.items()):
                table.add_row(name, str(value))

        return table

    def _create_step_panel(self, current_idx: int) -> Panel:
        """현재 스텝의 전체 패널 생성"""
        if current_idx >= len(self.instructions):
            return Panel(
                "[bold green]Execution Complete[/bold green]",
                title="Final State",
                border_style="green",
            )

        current = self.instructions[current_idx]

        # 이전/다음 명령어
        prev_instr = ""
        if current_idx > 0:
            prev = self.instructions[current_idx - 1]
            prev_instr = f"[dim]Previous: {prev.opname}"
            if prev.argval is not None:
                prev_instr += f" ({prev.argval})"
            prev_instr += "[/dim]"

        next_instr = ""
        if current_idx < len(self.instructions) - 1:
            next = self.instructions[current_idx + 1]
            next_instr = f"[dim]Next: {next.opname}"
            if next.argval is not None:
                next_instr += f" ({next.argval})"
            next_instr += "[/dim]"

        # 현재 명령어
        current_text = Text()
        current_text.append(f"Step {current_idx + 1}: ", style="bold white")
        current_text.append(current.opname, style="bold yellow")
        if current.argval is not None:
            current_text.append(f" ({current.argval})", style="cyan")

        # 레이아웃 생성
        layout = Table.grid(padding=1)
        layout.add_column(justify="left")
        layout.add_column(justify="left")

        # 스택과 지역변수를 나란히 배치
        stack_visual = self._create_stack_visual()
        locals_visual = self._create_locals_visual()

        stack_panel = Panel(stack_visual, title="Stack", border_style="cyan")
        locals_panel = Panel(locals_visual, title="Locals", border_style="green")

        layout.add_row(stack_panel, locals_panel)

        # 전체 내용 구성
        content = Table.grid()
        content.add_row(current_text)
        content.add_row("")
        content.add_row(layout)
        content.add_row("")
        if prev_instr:
            content.add_row(prev_instr)
        if next_instr:
            content.add_row(next_instr)

        return Panel(
            content, title=f"[bold]{self.func.__name__}[/bold]", border_style="blue"
        )

    def animate(self) -> None:
        """애니메이션 실행"""
        if self.delay == 0:
            # delay=0이면 모든 스텝을 즉시 출력
            for idx, instr in enumerate(self.instructions):
                panel = self._create_step_panel(idx)
                self.console.print(panel)
                self.console.print()

                # 명령어 실행
                should_continue = self._simulate_instruction(instr)
                if not should_continue:
                    break

            # 최종 상태
            final_panel = self._create_step_panel(len(self.instructions))
            self.console.print(final_panel)

        else:
            # 애니메이션 모드
            with Live(
                self._create_step_panel(0), console=self.console, refresh_per_second=4
            ) as live:
                for idx, instr in enumerate(self.instructions):
                    live.update(self._create_step_panel(idx))
                    time.sleep(self.delay)

                    # 명령어 실행
                    should_continue = self._simulate_instruction(instr)
                    if not should_continue:
                        break

                # 최종 상태 표시
                live.update(self._create_step_panel(len(self.instructions)))
                time.sleep(self.delay)


def animate_execution(
    func: Callable,
    args: tuple = (),
    delay: float = 0.5,
) -> None:
    """
    함수의 바이트코드 실행을 애니메이션으로 시각화

    Args:
        func: Python 함수 객체
        args: 함수 인자
        delay: 스텝 간 지연 시간 (초). 0이면 즉시 모든 스텝 출력

    Example:
        >>> def add(a, b):
        ...     return a + b
        >>> animate_execution(add, args=(1, 2), delay=0.5)
    """
    animator = StackAnimator(func, args, delay)
    animator.animate()


if __name__ == "__main__":
    # 테스트 예제
    def add(a, b):
        return a + b

    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n - 1)

    print("Example 1: Simple addition")
    print("=" * 60)
    animate_execution(add, args=(1, 2), delay=0)

    print("\n\nExample 2: With local variable")
    print("=" * 60)

    def compute(x, y):
        result = x + y
        return result

    animate_execution(compute, args=(3, 4), delay=0)
