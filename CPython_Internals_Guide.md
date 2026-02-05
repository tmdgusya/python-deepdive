# CPython 납품 파이프라인 심층 학습 가이드

> Python이 어떻게 컴파일되고 실행되는지 시스템 레벨에서 이해하기

## 목차

1. [개요](#1-개요)
2. [전체 파이프라인](#2-전체-파이프라인)
3. [핵심 데이터 구조](#3-핵심-데이터-구조)
4. [컴파일 과정 상세](#4-컴파일-과정-상세)
5. [실행 엔진 (Eval Loop)](#5-실행-엔진-eval-loop)
6. [메모리 관리](#6-메모리-관리)
7. [GIL (Global Interpreter Lock)](#7-gil-global-interpreter-lock)
8. [실습 가이드](#8-실습-가이드)
9. [핵심 소스 파일 맵](#9-핵심-소스-파일-맵)
10. [학습 로드맵](#10-학습-로드맵)

---

## 1. 개요

이 가이드는 CPython(표준 Python 구현체)의 납품 파이프라인을 시스템 레벨에서 깊이 있게 이해하는 것을 목표로 합니다. 소스코드가 어떻게 토큰화되고, 파싱되며, AST로 변환되고, 바이트코드로 컴파일되어 실행되는지 단계별로 살펴 봅니다.

### 대상 독자

- Python 납품 메커니즘을 깊이 이해하고 싶은 개발자
- CPython 소스 코드를 분석하고 싶은 개발자
- 프로그래밍 언어 구현에 관심 있는 개발자

---

## 2. 전체 파이프라인

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CPython Compilation Pipeline                      │
└─────────────────────────────────────────────────────────────────────┘

소스코드 (.py)
    ↓
[Tokenizer] ──────────────────────→ 토큰 스트림
    ↓                                    Parser/tokenizer/
[Parser (PEG)] ───────────────────→ AST (추상 구문 트리)
    ↓                                    Parser/parser.c
[Compiler] ───────────────────────→ 바이트코드 (pseudo-instructions)
    ↓                                    Python/compile.c
[Flow Graph] ─────────────────────→ 최적화 (peephole)
    ↓                                    Python/flowgraph.c
[Assembler] ──────────────────────→ PyCodeObject (.pyc)
    ↓                                    Python/assemble.c
[Eval Loop] ──────────────────────→ 실행
                                       Python/ceval.c
```

### 단계별 설명

| 단계 | 파일 | 설명 |
|------|------|------|
| Tokenizer | `Parser/tokenizer/` | 소스코드를 토큰 스트림으로 변환 |
| Parser | `Parser/parser.c` | PEG 파서로 AST 생성 |
| Compiler | `Python/compile.c` | AST를 pseudo-instructions로 변환 |
| Flow Graph | `Python/flowgraph.c` | CFG 생성 및 최적화 |
| Assembler | `Python/assemble.c` | PyCodeObject 생성 |
| Eval Loop | `Python/ceval.c` | 바이트코드 실행 |

---

## 3. 핵심 데이터 구조

### 3.1 PyObject - 모든 Python 객체의 기반

**파일**: `Include/object.h`

```c
struct _object {
    // 참조 카운트 (메모리 관리)
    Py_ssize_t ob_refcnt;
    
    // 타입 객체 포인터
    PyTypeObject *ob_type;
};
```

**핵심 개념**:
- 모든 Python 객체는 `PyObject`로 시작하는 C 구조체
- `ob_refcnt`가 0이 되면 객체 해제
- `ob_type`이 가리키는 타입 객체에 메서드 테이블 존재

**참조 카운팅 매크로**:
```c
Py_INCREF(op)  // 참조 카운트 증가: op->ob_refcnt++
Py_DECREF(op)  // 참조 카운트 감소: op->ob_refcnt--, 0이면 해제
```

### 3.2 PyCodeObject - 바이트코드 저장소

**파일**: `Include/cpython/code.h`

```c
typedef struct {
    PyObject_VAR_HEAD
    
    // 가장 자주 접근하는 필드 (캐시 라인에 배치)
    PyObject *co_consts;           // 상수 튜플
    PyObject *co_names;            // 이름 튜플
    PyObject *co_exceptiontable;   // 예외 처리 테이블
    int co_flags;                  // 코드 플래그
    
    // 함수 서명 정보
    int co_argcount;               // 인자 개수 (excluding *args)
    int co_posonlyargcount;        // positional-only 인자 개수
    int co_kwonlyargcount;         // keyword-only 인자 개수
    int co_stacksize;              // 필요한 최대 스택 깊이
    int co_firstlineno;            // 첫 번째 소스 라인 번호
    
    // 변수 추적
    int co_nlocalsplus;            // locals + cells + free vars
    int co_framesize;              // 프레임 크기 (words)
    int co_nlocals;                // 지역 변수 개수
    int co_ncellvars;              // 셀 변수 개수
    int co_nfreevars;              // 자유 변수 개수
    uint32_t co_version;           // 최적화 버전
    
    // 이름 및 메타데이터
    PyObject *co_localsplusnames;  // 변수 이름 튜플
    PyObject *co_localspluskinds;  // 변수 종류 바이트열
    PyObject *co_filename;         // 소스 파일명
    PyObject *co_name;             // 함수 이름
    PyObject *co_qualname;         // 정규화된 이름
    PyObject *co_linetable;        // 라인 번호 정보 (압축됨)
    
    // 최적화 및 계측
    _PyExecutorArray *co_executors;        // Tier 2 실행기
    _PyCoCached *_co_cached;               // 캐시된 co_code 등
    uintptr_t _co_instrumentation_version; // 계측 버전
    _PyCoMonitoringData *_co_monitoring;   // 모니터링 데이터
    
    // 바이트코드 저장 (적응형)
    char co_code_adaptive[SIZE];   // 캐시 엔트리를 포함한 바이트코드
} PyCodeObject;
```

### 3.3 _PyInterpreterFrame - 실행 프레임

**파일**: `Include/internal/pycore_frame.h`

```c
typedef struct _PyInterpreterFrame {
    PyObject *f_executable;        // 코드 객체 (강한 참조)
    struct _PyInterpreterFrame *previous;  // 이전 프레임
    PyObject *f_funcobj;           // 함수 객체 (강한 참조)
    PyObject *f_globals;           // 전역 네임스페이스 (차용)
    PyObject *f_builtins;          // 내장 네임스페이스 (차용)
    PyObject *f_locals;            // 지역 네임스페이스 (강한 참조, NULL 가능)
    PyFrameObject *frame_obj;      // Python 프레임 객체 (강한 참조, NULL 가능)
    _Py_CODEUNIT *instr_ptr;       // 현재 명령어 포인터
    int stacktop;                  // 스택 탑 오프셋 (localsplus 기준)
    uint16_t return_offset;        // 함수 호출 후 복귀 위치
    char owner;                    // 프레임 소유자 (THREAD/GENERATOR 등)
    
    // 지역변수 + 평가 스택 저장소 (가변 길이)
    PyObject *localsplus[1];
} _PyInterpreterFrame;
```

**메모리 레이아웃**:
```
localsplus[0]     ← 지역 변수 0
...
localsplus[n-1]   ← 지역 변수 n-1
localsplus[n]     ← 스택 항목 0 (stacktop = n+1일 때)
localsplus[n+1]   ← 스택 항목 1 (stacktop = n+2일 때)
...
```

---

## 4. 컴파일 과정 상세

### 4.1 토큰화 (Tokenizer)

**파일**: `Parser/tokenizer/`

```python
# 예시: "x = 1 + 2" → 토큰 스트림
NAME(x) EQ NUMBER(1) PLUS NUMBER(2) NEWLINE
```

**주요 토큰 유형**:
- `NAME`: 식별자 (변수명, 함수명 등)
- `NUMBER`: 숫자 리터럴
- `STRING`: 문자열 리터럴
- `NEWLINE`: 줄바꿈
- `INDENT`/`DEDENT`: 들여쓰기/내어쓰기
- 연산자: `PLUS`, `MINUS`, `STAR`, `SLASH` 등

### 4.2 파싱 (PEG Parser)

**파일**: `Parser/parser.c` (자동 생성됨)

Python 3.9+부터 PEG(Parser Expression Grammar) 파서 사용:
- **입력**: 토큰 스트림
- **출력**: AST (추상 구문 트리)
- **특징**: 백트래킹 + 메모이제이션 지원

**문법 파일**: `Grammar/python.gram`

```
# 예시: import 문 규칙
import_name: 'import' dotted_as_names
```

### 4.3 AST (Abstract Syntax Tree)

**파일**: `Parser/Python.asdl`

```asdl
module Python
{
    stmt = FunctionDef(identifier name, arguments args, stmt* body,
                       expr* decorators, expr? returns, ...)
         | Return(expr? value)
         | Assign(expr* targets, expr value, ...)
         | If(expr test, stmt* body, stmt* orelse)
         | While(expr test, stmt* body, stmt* orelse)
         | ...
    
    expr = BinOp(expr left, operator op, expr right)
         | UnaryOp(unaryop op, expr operand)
         | Constant(constant value, ...)
         | Name(identifier id, expr_context ctx)
         | Call(expr func, expr* args, keyword* keywords)
         | ...
    
    operator = Add | Sub | Mult | Div | Mod | Pow | LShift | ...
}
```

**AST 노드 생성**: `Python/Python-ast.c` (자동 생성됨)

### 4.4 심볼 테이블 생성

**파일**: `Python/symtable.c`

```c
// 심볼 테이블 빌드
_PySymtable_Build(AST, filename, future)

// 주요 작업:
// 1. 변수 스코프 분석
// 2. 지역/전역/자유 변수 구분
// 3. 셀 변수(cell variables) 식별
```

**변수 종류**:
- **Local**: 함수 내에서만 사용되는 변수
- **Global**: 전역 변수
- **Free**: 외부 스코프에서 정의된 변수 (클로저)
- **Cell**: 클로저에서 사용되는 지역 변수

### 4.5 바이트코드 생성

**파일**: `Python/compile.c`

```c
// 예시: "x = 1 + 2" 컴파일 결과
LOAD_CONST     0    # 1을 스택에 푸시
LOAD_CONST     1    # 2를 스택에 푸시  
BINARY_OP      0    # ADD (스택에서 2개 팝, 결과 푸시)
STORE_FAST     0    # x에 저장 (스택에서 팝)
RETURN_CONST   2    # None 반환
```

**주요 컴파일러 매크로**:
```c
ADDOP(c, loc, opcode)                    // 오퍼레이션 추가
ADDOP_I(c, loc, opcode, oparg)          // 정수 인자가 있는 오퍼레이션
ADDOP_O(c, loc, opcode, obj, type)      // PyObject 인자가 있는 오퍼레이션
ADDOP_LOAD_CONST(c, loc, obj)           // LOAD_CONST 오퍼레이션
ADDOP_JUMP(c, loc, opcode, basicblock)  // 점프 오퍼레이션
```

### 4.6 제어 흐름 그래프 (CFG)

**파일**: `Python/flowgraph.c`

**기본 블록 (Basic Block)**:
- 단일 진입점, 단일 출구점을 가진 명령어 시퀀스
- 내부에서는 순차적 실행
- 마지막 명령어만 점프 가능

```python
# 예시: if 문의 CFG
if x < 10:          # Block A: x < 10 비교, 조건부 점프
    f1()            # Block B: f1() 호출
    f2()            #       : f2() 호출
else:               # Block C: g() 호출
    g()
end()               # Block D: end() 호출
```

**최적화**:
- 도달 불가능 코드 제거
- 불필요한 점프 제거
- 상수 폴딩 (compile-time constant evaluation)

### 4.7 어셈블리

**파일**: `Python/assemble.c`

```c
// pseudo-instructions → 실제 바이트코드 변환
_PyAssemble_MakeCodeObject(
    const char *filename,
    PyObject *code,
    PyObject *consts,
    PyObject *names,
    ...
)
```

**수행 작업**:
1. pseudo-instructions를 실제 명령어로 변환
2. 점프 타겟을 논리적 레이블에서 상대 오프셋으로 변환
3. 예외 테이블 생성
4. 위치 테이블 생성
5. `PyCodeObject` 생성 및 반환

---

## 5. 실행 엔진 (Eval Loop)

### 5.1 핵심 함수: `_PyEval_EvalFrameDefault()`

**파일**: `Python/ceval.c` (라인 685+)

```c
PyObject* _Py_HOT_FUNCTION
_PyEval_EvalFrameDefault(PyThreadState *tstate, 
                         _PyInterpreterFrame *frame, 
                         int throwflag)
{
    // 프레임 설정
    _Py_CODEUNIT *next_instr = frame->instr_ptr;
    PyObject **stack_pointer = _PyFrame_Stackbase(frame);
    
    // 메인 디스패치 루프
    DISPATCH();  // 첫 명령어로 점프
}
```

**핵심 변수**:
- `next_instr`: 현재 실행 중인 명령어를 가리킴
- `stack_pointer`: 평가 스택의 탑을 가리킴
- `opcode`: 현재 오퍼레이션 코드 (uint8_t)
- `oparg`: 현재 오퍼레이션 인자 (int)

### 5.2 디스패치 메커니즘

**Computed Gotos** (고성능 버전):

```c
// opcode_targets.h에 정의된 점프 테이블
static void *opcode_targets[256] = {
    &&TARGET_CACHE,
    &&TARGET_BINARY_OP_ADAPTIVE,
    &&TARGET_BINARY_OP_ADD_INT,
    &&TARGET_LOAD_CONST,
    &&TARGET_LOAD_FAST,
    // ... 256개의 오퍼레이션
};

// 디스패치 매크로
#define DISPATCH() \
    do { \
        opcode = next_instr->op.code; \
        next_instr++; \
        goto *opcode_targets[opcode]; \
    } while (0)

// 오퍼레이션 핸들러 예시
TARGET_LOAD_CONST: {
    value = GETITEM(FRAME_CO_CONSTS, oparg);
    Py_INCREF(value);
    PUSH(value);
    DISPATCH();
}
```

**명령어 실행 흐름**:
```
1. DISPATCH() → next_instr에서 opcode 로드
2. opcode_targets[opcode]로 점프
3. 오퍼레이션 핸들러 실행 (스택 조작)
4. 핸들러가 DISPATCH() 호출하여 다음 명령어 가져옴
5. 루프 계속
```

### 5.3 주요 오퍼레이션 구현

**파일**: `Python/bytecodes.c`

#### LOAD_CONST
```c
pure inst(LOAD_CONST, (-- value)) {
    value = GETITEM(FRAME_CO_CONSTS, oparg);
    Py_INCREF(value);
}
```
- `co_consts` 튜플에서 인덱스 `oparg`의 상수를 가져옴
- 참조 카운트 증가
- 스택에 푸시
- **성능**: O(1) - 직접 튜플 접근

#### LOAD_FAST
```c
replicate(8) pure inst(LOAD_FAST, (-- value)) {
    value = GETLOCAL(oparg);
    assert(value != NULL);
    Py_INCREF(value);
}
```
- `localsplus[oparg]`에서 지역 변수를 가져옴
- `replicate(8)`: 캐시 지역성을 위해 8개 복사본 생성
- **성능**: O(1) - 직접 배열 접근

#### BINARY_OP_ADD_INT (특수화된 버전)
```c
pure op(_BINARY_OP_ADD_INT, (left, right -- res)) {
    STAT_INC(BINARY_OP, hit);
    res = _PyLong_Add((PyLongObject *)left, 
                      (PyLongObject *)right);
    _Py_DECREF_SPECIALIZED(right, (destructor)PyObject_Free);
    _Py_DECREF_SPECIALIZED(left, (destructor)PyObject_Free);
    ERROR_IF(res == NULL, error);
}
```
- 스택에서 두 정수를 팝
- `_PyLong_Add()` 호출 (일반 `PyNumber_Add`보다 빠름)
- 입력 참조 카운트 감소
- 결과 푸시
- **특수화**: 타입 가드가 두 피연산자가 정확한 int 타입임을 검증한 후에만 실행

### 5.4 특수화 및 적응형 최적화

**3단계 시스템**:

1. **Tier 1 (바이트코드)**: 일반 오퍼레이션 + 적응형 카운터
   - `_SPECIALIZE_BINARY_OP`가 카운터 확인
   - 카운터가 임계값에 도달하면 `_Py_Specialize_BinaryOp()` 호출
   - 일반 오퍼레이션을 특수화된 버전으로 교체

2. **Tier 2 (Micro-ops)**: 핫 코드의 최적화된 트레이스
   - Tier 1 실행에서 옵티마이저가 생성
   - 전체 오퍼레이션 대신 micro-ops(uops) 사용
   - `_PyExecutorObject`에 저장

3. **Tier 3 (JIT)**: 머신 코드 (Python 3.13+)
   - 핫 트레이스를 네이티브 코드로 컴파일
   - `_Py_JIT` 플래그로 제어

**특수화 예시**:
```c
// 일반 버전 (Tier 1)
BINARY_OP → _SPECIALIZE_BINARY_OP + _BINARY_OP

// 특수화 후 (여전히 Tier 1, 더 빠름)
BINARY_OP_ADD_INT → _GUARD_BOTH_INT + _BINARY_OP_ADD_INT
```

### 5.5 오류 처리

```c
// 오퍼레이션 핸들러에서
ERROR_IF(res == NULL, error);

// error 레이블로 점프
error:
    /* 예외 상태 다시 확인 */
    assert(_PyErr_Occurred(tstate));
    
    /* co_exceptiontable에서 예외 핸들러 찾기 */
    if (get_exception_handler(...) == 0) {
        // 핸들러 없음 - 프레임 언와인드
        goto exit_unwind;
    }
    
    // 핸들러 찾음 - 스택 설정하고 점프
    PUSH(exc);
    next_instr = handler_address;
    DISPATCH();
```

**프레임 언와인딩**:
```c
exit_unwind:
    _Py_LeaveRecursiveCallPy(tstate);
    _PyInterpreterFrame *dying = frame;
    frame = tstate->current_frame = dying->previous;
    _PyEval_FrameClearAndPop(tstate, dying);
    return NULL;  // 예외 상위로 전파
```

---

## 6. 메모리 관리

### 6.1 참조 카운팅

**기본 원리**:
```c
// 객체 생성 시
PyObject *obj = PyObject_New(PyObject, &SomeType);
// ob_refcnt = 1

// 참조 추가
Py_INCREF(obj);  // ob_refcnt = 2

// 참조 제거
Py_DECREF(obj);  // ob_refcnt = 1
Py_DECREF(obj);  // ob_refcnt = 0 → 객체 해제
```

**사이클 감지의 한계**:
```python
# 참조 카운팅만으로는 해결 불가능한 순환 참조
a = []
b = []
a.append(b)  # b의 참조 카운트 = 2
b.append(a)  # a의 참조 카운트 = 2
del a, b     # 둘 다 참조 카운트 = 1, 하지만 접근 불가능
```

### 6.2 가비지 컬렉션 (GC)

**파일**: `Modules/gcmodule.c`

**세대별 GC**:
- **Gen 0**: 새로 생성된 객체
- **Gen 1**: Gen 0에서 살아남은 객체
- **Gen 2**: Gen 1에서 살아남은 객체 (장기 객체)

**GC 트리거**:
```c
// 할당 수가 임계값을 초과하면 GC 실행
if (allocations > threshold) {
    collect_generation(gen);
}
```

**사이클 탐지 알고리즘**:
1. 객체 그래프 탐색
2. 참조 카운트 감소 시뮬레이션
3. 참조 카운트가 0이 되는 객체들이 사이클의 일부
4. 사이클 내 객체들 해제

---

## 7. GIL (Global Interpreter Lock)

### 7.1 개념

**파일**: `Python/ceval_gil.c`

```c
// GIL 획득
PyEval_AcquireLock();

// Python 코드 실행
...

// GIL 해제
PyEval_ReleaseLock();
```

**핵심 특성**:
- 한 시점에 하나의 스레드만 Python 바이트코드 실행 가능
- 멀티코어 CPU를 활용한 병렬 처리 불가 (스레드 레벨)
- I/O 작업 시 GIL 자동 해제
- CPU 집약적 작업은 `sys.setswitchinterval`로 인터럽트

### 7.2 GIL과 성능

**GIL이 해제되는 경우**:
- 파일 I/O 작업
- 네트워크 I/O 작업
- `time.sleep()`
- C 확장 모듈이 명시적으로 GIL 해제

**GIL 우회 방법**:
- 멀티프로세싱 (`multiprocessing` 모듈)
- C 확장에서 `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS`
- `concurrent.futures.ProcessPoolExecutor`

---

## 8. 실습 가이드

### 8.1 바이트코드 확인하기

```bash
# 바이트코드 디스어셈블리
python -m dis script.py

# 상세 출력
python -m dis -v script.py
```

### 8.2 Python에서 바이트코드 분석

```python
import dis
import types

# 함수의 바이트코드 확인
def example():
    x = 1 + 2
    return x

# 바이트코드 바이트열
print("Bytecode:", example.__code__.co_code)

# 상수 튜플
print("Constants:", example.__code__.co_consts)

# 지역변수 이름
print("Variable names:", example.__code__.co_varnames)

# 전체 디스어셈블리
dis.dis(example)
```

**출력 예시**:
```
  2           0 LOAD_CONST               1 (1)
              2 LOAD_CONST               2 (2)
              4 BINARY_ADD
              6 STORE_FAST               0 (x)

  3           8 LOAD_FAST                0 (x)
             10 RETURN_VALUE
```

### 8.3 실행 추적하기

```bash
# 명령어별 실행 추적 (CPython 빌드 필요)
PYTHON_LLTRACE=5 python script.py
```

### 8.4 AST 확인하기

```python
import ast

# 소스코드 → AST
code = """
def add(a, b):
    return a + b
"""

tree = ast.parse(code)
print(ast.dump(tree, indent=2))
```

### 8.5 직접 CPython 소스 수정해보기

1. **CPython 소스 클론**:
```bash
git clone https://github.com/python/cpython.git
cd cpython
```

2. **빌드**:
```bash
./configure --with-pydebug
make -j$(nproc)
```

3. **오퍼레이션 추가 예시** (`Python/bytecodes.c`):
```c
inst(PRINT_HELLO, (--)) {
    printf("Hello from CPython!\n");
}
```

4. **케이스 생성기 실행**:
```bash
python Tools/cases_generator/generate_cases.py \
    --input Python/bytecodes.c \
    --output Python/generated_cases.c.h
```

5. **재빌드 및 테스트**:
```bash
make -j$(nproc)
./python -c "import dis; dis.dis('print(\"test\")')"
```

---

## 9. 핵심 소스 파일 맵

### Include/ - 헤더 파일

| 파일 | 설명 |
|------|------|
| `object.h` | PyObject 정의, 참조 카운팅 매크로 |
| `cpython/code.h` | PyCodeObject 정의 |
| `internal/pycore_frame.h` | _PyInterpreterFrame 구조체 |
| `internal/pycore_ast.h` | AST 구조체 |
| `internal/pycore_symtable.h` | 심볼 테이블 |
| `opcode.h` | 오퍼레이션 코드 정의 |

### Parser/ - 파서

| 파일 | 설명 |
|------|------|
| `Python.asdl` | AST 정의 (ASDL 언어) |
| `parser.c` | PEG 파서 (자동 생성됨) |
| `peg_api.c` | 파서 API |
| `tokenizer/` | 토크나이저 구현 |

### Python/ - 핵심 인터프리터

| 파일 | 설명 | 중요도 |
|------|------|--------|
| `ceval.c` | 메인 실행 루프 | ⭐⭐⭐ |
| `bytecodes.c` | 오퍼레이션 정의 | ⭐⭐⭐ |
| `compile.c` | AST → 바이트코드 컴파일러 | ⭐⭐⭐ |
| `flowgraph.c` | CFG 및 최적화 | ⭐⭐ |
| `assemble.c` | 코드 객체 생성 | ⭐⭐ |
| `symtable.c` | 심볼 테이블 | ⭐⭐ |
| `pyarena.c` | 메모리 관리 (Arena) | ⭐ |
| `specialize.c` | 오퍼레이션 특수화 | ⭐⭐ |

### Objects/ - 객체 구현

| 파일 | 설명 |
|------|------|
| `codeobject.c` | PyCodeObject 메서드 |
| `frameobject.c` | PyFrameObject 메서드 |
| `longobject.c` | int 구현 (임의 정밀도 정수) |
| `listobject.c` | list 구현 |
| `dictobject.c` | dict 구현 (해시 테이블) |
| `tupleobject.c` | tuple 구현 |
| `typeobject.c` | type 구현 (메타클래스) |

### Modules/ - 표준 라이브러리 모듈

| 파일 | 설명 |
|------|------|
| `gcmodule.c` | 가비지 컬렉터 |
| `_threadmodule.c` | 스레딩 지원 |

---

## 10. 학습 로드맵

### 단계 1: 바이트코드 읽기 (1-2일)
- [ ] `dis` 모듈로 간단한 함수의 바이트코드 확인
- [ ] 각 오퍼레이션의 의미 파악
- [ ] 스택 기반 VM의 동작 방식 이해

**실습**:
```python
# 다음 코드의 바이트코드를 분석해보세요
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

import dis
dis.dis(factorial)
```

### 단계 2: AST 이해하기 (1-2일)
- [ ] `ast` 모듈로 코드의 AST 생성
- [ ] AST 노드 유형 학습
- [ ] AST → 소스코드 변환 (`ast.unparse`)

**실습**:
```python
# 다양한 제어 구조의 AST를 비교해보세요
import ast

for code in ['if x:', 'for x in y:', 'while x:', 'try:', 'with x:']:
    tree = ast.parse(code + ' pass')
    print(f"{code:15} → {type(tree.body[0]).__name__}")
```

### 단계 3: Eval Loop 이해하기 (2-3일)
- [ ] `Python/ceval.c`의 DISPATCH 매크로 찾기
- [ ] 간단한 오퍼레이션의 구현 확인
- [ ] 프레임 스택의 동작 방식 이해

**실습**:
```bash
# CPython 소스에서 핵심 매크로 찾기
grep -n "DISPATCH()" Python/ceval.c | head -20
grep -n "TARGET(LOAD_CONST)" Python/ceval.c
```

### 단계 4: 객체 모델 이해하기 (2-3일)
- [ ] `PyObject` 구조체 분석
- [ ] 참조 카운팅 메커니즘 이해
- [ ] 타입 객체와 메서드 테이블 관계 파악

**실습**:
```python
# 객체의 참조 카운트 확인
import sys

a = "hello"
print(f"Ref count: {sys.getrefcount(a)}")

b = a
print(f"Ref count after assignment: {sys.getrefcount(a)}")
```

### 단계 5: 직접 CPython 소스 수정하기 (3-5일)
- [ ] CPython 소스 클론 및 빌드
- [ ] 간단한 디버그 출력 추가
- [ ] 새로운 오퍼레이션 추가 시도

**실습**:
```c
// Python/ceval.c의 DISPATCH 매크로에 디버그 출력 추가
#ifdef PY_DEBUG
    printf("Executing opcode: %d at offset %ld\n", 
           opcode, next_instr - _PyCode_CODE(frame->f_executable));
#endif
```

### 단계 6: 고급 주제 탐구 (지속)
- [ ] 오퍼레이션 특수화 메커니즘
- [ ] 가비지 컬렉션 알고리즘
- [ ] GIL과 스레딩 모델
- [ ] C 확장 모듈 작성

---

## 참고 자료

### 공식 문서
- [CPython Developer's Guide](https://devguide.python.org/)
- [CPython Internals Documentation](https://github.com/python/cpython/tree/main/InternalDocs)

### 추천 서적
- "CPython Internals" by Anthony Shaw
- "Python源码剖析" by 陈儒 (중국어)

### 온라인 리소스
- [Real Python - CPython Source Code Guide](https://realpython.com/cpython-source-code-guide/)
- [A Tour of CPython Compilation](https://dev.to/cwprogram/a-tour-of-cpython-compilation-cd5)
- [Python's Innards](https://tech.blog.aknin.name/category/pythons-innards/)

---

## 용어 정리

| 용어 | 설명 |
|------|------|
| **AST** | Abstract Syntax Tree (추상 구문 트리) |
| **Bytecode** | Python VM이 실행하는 중간 코드 |
| **CFG** | Control Flow Graph (제어 흐름 그래프) |
| **Frame** | 함수 실행 컨텍스트 (지역 변수, 스택 등) |
| **GIL** | Global Interpreter Lock |
| **Opcode** | Operation Code (명령어 코드) |
| **PEG** | Parsing Expression Grammar |
| **PyObject** | 모든 Python 객체의 기본 C 구조체 |
| **Reference Counting** | 참조 카운팅 (메모리 관리 기법) |
| **Tier 1/2/3** | CPython의 3단계 최적화 시스템 |

---

*이 가이드는 Python 3.12+ 기준으로 작성되었습니다.*
