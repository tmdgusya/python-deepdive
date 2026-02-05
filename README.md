# CPython 내부 구조 실습 학습

> Python이 어떻게 컴파일되고 실행되는지 직접 눈으로 확인하며 학습하는 대화형 가이드

Python의 마법을 벗겨내고, 토큰화부터 메모리 관리까지 CPython의 핵심 메커니즘을 시각화하며 이해합니다.

## 설치

### 필수 요구사항
- Python 3.11+ (권장: 3.13)
- pip
- graphviz (시스템 패키지)

### 설치 방법

#### 1. Python 패키지 설치
```bash
pip install -r requirements.txt
```

#### 2. Graphviz 시스템 패키지 설치

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install graphviz
```

**macOS:**
```bash
brew install graphviz
```

**Windows (Chocolatey):**
```bash
choco install graphviz
```

또는 [graphviz 공식 사이트](https://graphviz.org/download/)에서 직접 다운로드

#### 3. 설치 확인
```bash
python -c "import graphviz; print('✓ graphviz 설치 완료')"
```

## 학습 순서

각 모듈은 독립적으로 학습할 수 있지만, 순서대로 진행하면 CPython의 전체 파이프라인을 이해할 수 있습니다.

| # | 모듈 | 주제 | 예상 시간 | 파일 |
|---|------|------|----------|------|
| 1 | 토큰화 | 소스 코드를 토큰으로 분해 | 1-2시간 | `notebooks/01_tokenization.ipynb` |
| 2 | AST 분석 | 토큰을 추상 구문 트리로 변환 | 2-3시간 | `notebooks/02_ast_visualization.ipynb` |
| 3 | 바이트코드 | 바이트코드 생성 및 분석 | 2-3시간 | `notebooks/03_bytecode_deep_dive.ipynb` |
| 4 | 스택 VM | 가상 머신의 스택 기반 실행 | 2-3시간 | `notebooks/04_stack_vm_simulation.ipynb` |
| 5 | 최적화 | CPython의 최적화 기법 | 1-2시간 | `notebooks/05_optimization.ipynb` |
| 6 | 메모리 & GC | 메모리 관리 및 가비지 컬렉션 | 2-3시간 | `notebooks/06_memory_gc.ipynb` |

**총 예상 학습 시간: 10-16시간**

## 도구

프로젝트에 포함된 시각화 도구들입니다.

| 도구 | 설명 | 사용법 |
|------|------|--------|
| `ast_visualizer` | AST를 그래프로 시각화 | `from tools.ast_visualizer import visualize_ast` |
| `cfg_visualizer` | 제어 흐름 그래프 시각화 | `from tools.cfg_visualizer import visualize_cfg` |
| `bytecode_tracer` | 바이트코드 실행 추적 | `from tools.bytecode_tracer import trace_bytecode` |
| `stack_animator` | 스택 VM 애니메이션 | `from tools.stack_animator import animate_stack` |

## 빠른 시작

### Jupyter Notebook 실행
```bash
jupyter notebook
```

그 후 `notebooks/` 디렉토리에서 원하는 모듈을 선택하여 시작합니다.

### 도구 사용 예시

#### AST 시각화
```python
from tools.ast_visualizer import visualize_ast

code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

visualize_ast(code, output_file="fib_ast.png")
```

#### 바이트코드 추적
```python
from tools.bytecode_tracer import trace_bytecode

code = "x = 1 + 2"
trace_bytecode(code)
```

#### 스택 VM 시뮬레이션
```python
from tools.stack_animator import animate_stack

code = "2 + 3 * 4"
animate_stack(code, output_file="stack_animation.gif")
```

## 프로젝트 구조

```
python-debug/
├── notebooks/                          # 6개 학습 모듈
│   ├── 01_tokenization.ipynb           # 토큰화 학습
│   ├── 02_ast_visualization.ipynb      # AST 분석
│   ├── 03_bytecode_deep_dive.ipynb     # 바이트코드
│   ├── 04_stack_vm_simulation.ipynb    # 스택 VM
│   ├── 05_optimization.ipynb           # 최적화 기법
│   ├── 06_memory_gc.ipynb              # 메모리 관리
│   └── outputs/                        # 생성된 시각화 이미지
│
├── tools/                              # 시각화 도구
│   ├── __init__.py
│   ├── ast_visualizer.py               # AST 시각화
│   ├── cfg_visualizer.py               # 제어 흐름 그래프
│   ├── bytecode_tracer.py              # 바이트코드 추적
│   └── stack_animator.py               # 스택 애니메이션
│
├── outputs/                            # 생성된 이미지 저장소
│
├── examples/                           # 예제 코드
│
├── CPython_Internals_Guide.md          # 이론 가이드 (상세 설명)
├── requirements.txt                    # 의존성
└── README.md                           # 이 파일
```

## 학습 팁

1. **순서대로 진행하세요**: 각 모듈은 이전 모듈의 개념을 기반으로 합니다.
2. **직접 실험하세요**: 노트북의 코드를 수정하고 결과를 확인해보세요.
3. **시각화를 활용하세요**: 복잡한 개념도 그래프로 보면 이해하기 쉬워집니다.
4. **CPython_Internals_Guide.md를 참고하세요**: 각 모듈의 이론적 배경을 더 깊이 있게 설명합니다.

## 참고 자료

- **[CPython_Internals_Guide.md](./CPython_Internals_Guide.md)** - 상세한 이론 가이드
- **[Python 공식 문서](https://docs.python.org/)** - 공식 Python 문서
- **[CPython GitHub](https://github.com/python/cpython)** - CPython 소스 코드
- **[Python AST 모듈](https://docs.python.org/3/library/ast.html)** - AST 관련 문서
- **[Python dis 모듈](https://docs.python.org/3/library/dis.html)** - 바이트코드 분석 도구

## 문제 해결

### graphviz 설치 오류
```
graphviz.backend.ExecutableNotFound: "dot" not found in PATH
```

**해결책**: 시스템 graphviz 패키지를 설치하세요 (위의 "Graphviz 시스템 패키지 설치" 참고)

### Jupyter 실행 오류
```bash
# Jupyter 재설치
pip install --upgrade jupyter
```

### 모듈 import 오류
```bash
# 프로젝트 루트에서 실행
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.

## 기여

버그 리포트나 개선 제안은 이슈를 통해 제출해주세요.

---

**Happy Learning! 🐍**
