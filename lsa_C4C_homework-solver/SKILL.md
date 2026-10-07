# Homework Auto-Solver & Formatter（C4C 迁移扩展版）

> 从作业文件到可提交 PDF，一条命令搞定。
> Ontology-grounded, retrieval-augmented homework solving.
>
> **本版本在 Claude Code 基线（starter kit）之上完成两件事：**
> 1. **引擎迁移**：求解引擎从 Claude 迁移到国产大模型（Qwen 3.6 / Kimi 2.5，OpenAI 兼容接口），
>    并内置**确定性离线降级**——无 API Key、断网时流水线依然可运行、结果可复现。
> 2. **学科扩展**：从「微积分极限」扩展到**线性代数、微分方程、大学物理（力学/静电学）**，
>    并新增 **PDF / Word 文件摄入** 与**答案自动验证**。

## Skill Invocation

**Triggers:** "solve this homework", "auto-solve worksheet", "run the homework solver", "求解作业", "自动解题", or when a user provides a math worksheet (.md, .pdf, .docx, .png) and asks for solutions.

**Usage:** When triggered, the agent should:

1. **Locate the input file.** The user may upload a file, paste text, or point to a path. If text is pasted, save it as a temporary `.md` file first.

2. **Run the pipeline:**
```bash
SKILL_DIR="<path-to-this-skill-directory>"
python "$SKILL_DIR/scripts/pipeline.py" <input_file> <output_dir> [--compile] [--chinese] \
    [--course "线性代数"] [--student "张三"]
```

3. **Report results.** Show the solve rate (X/Y solved), validation pass rate, list any unsolved problems, and provide the output files (`.tex` and optionally `.pdf`).

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `input` | (required) | Path to homework file (.md, .pdf, .docx, image) |
| `output_dir` | (required) | Where to write output files |
| `--compile` | off | Compile LaTeX to PDF (requires pdflatex/xelatex) |
| `--chinese` | off | 中文排版（xelatex + ctex） |
| `--course` | "Mathematics" | Course name for header |
| `--student` | "Student" | Student name for header |
| `--title` | "Homework Solutions" | Title for the document |
| `--no-validate` | off | 跳过 Stage 3.5 答案验证 |

**Output files:**
| File | Content |
|------|---------|
| `1_ingested.json` | Raw text extraction with section boundaries |
| `2_parsed.json` | Structured problems with classifications |
| `3_solutions.json` | Solutions with steps, answers, and solve status |
| `4_validation.json` | 答案验证报告（特征值回代、逆矩阵校验等） |
| `homework.tex` | Formatted LaTeX document |
| `homework.pdf` | Compiled PDF (if `--compile` used) |

**Dependencies:** `pip install sympy pyyaml`（可选：`pdfplumber python-docx`，见 `requirements.txt`）

---

## 架构总览（迁移后）

```
Input (.md/.pdf/.docx/图片)
   │
   ▼
Stage 1  ingest.py            文档摄入：Markdown 直接读；PDF→pdfplumber；Word→python-docx；
   │                          图片→Tesseract OCR / Qwen-VL（国产模型 Vision）
   ▼
Stage 2  parse_problems.py    题目解析 + 分类：关键词分类 + T-box 本体（多领域 YAML）
   │                          （classify.py 加载 domain_skills/*.yaml 全部领域）
   ▼
Stage 3  solve.py             求解路由（混合引擎）：
   │     solvers_extended.py    ├─ SymPy 引擎：极限/微积分/矩阵/行列式/特征值/
   │     llm_solver.py          │   线性方程组/ODE/物理公式（确定性，可核验）
   │                            └─ 国产 LLM 引擎：证明题/概念题/多步推理
   │                                （Qwen 3.6 / Kimi 2.5，无 Key 时离线知识库降级）
   ▼
Stage 3.5 validate.py         答案验证：特征值回代 det(A-λI)=0、A·A⁻¹=I、
   │                          方程组回代残差（输出 4_validation.json）
   ▼
Stage 4  render_latex.py      LaTeX 生成：作业模板、题目+解答交替、\boxed 答案、
   │                          矩阵/公式排版；use_chinese 时用 ctexart
   ▼
Stage 5  compile_pdf()        PDF 编译：自动发现 MiKTeX/TeX Live/tectonic，
                              xelatex 优先（中文支持），编译 3 遍
```

**核心设计原则（继承自 starter kit）：** Solve rate = domain coverage。
求解能力由领域知识（`domain_skills/*.yaml`）决定，而不是硬编码正则。扩展新学科 = 新增领域 YAML + 求解器模板。

## Quick Start

```bash
# 安装依赖
pip install -r requirements.txt

# 英文示例作业（微积分极限——回归验证 Claude 基线）
python scripts/pipeline.py examples/sample_homework.md output/

# 线性代数真实作业（中文，编译 PDF）
python scripts/pipeline.py 作业.md output/ --compile --chinese \
    --course "线性代数" --student "张三"

# PDF / Word 输入
python scripts/pipeline.py homework.pdf output/ --compile
python scripts/pipeline.py homework.docx output/ --compile
```

### 接入国产大模型（可选）

证明题/概念题自动交给 LLM 引擎。默认 Qwen，可用环境变量切换：

```bash
# 通义千问（推荐，数学推理强）
export DASHSCOPE_API_KEY=sk-xxxx        # https://dashscope.aliyuncs.com
export C4C_LLM_PROVIDER=qwen

# Kimi（长上下文、复杂推理）
export MOONSHOT_API_KEY=sk-xxxx          # https://api.moonshot.cn
export C4C_LLM_PROVIDER=kimi
```

> **无 API Key 也能跑**：LLM 引擎不可用时自动降级为离线知识库模板
> （`llm_solver.py: OFFLINE_TEMPLATES`），流水线不中断、结果确定可复现。
> 计算题（约占作业主体）始终由 SymPy 确定性求解，不依赖任何 API。

## Five-Stage Pipeline

### Stage 1 — Document Ingestion (`ingest.py`)

| Format | Status | Implementation |
|--------|--------|----------------|
| Markdown (.md) | ✅ | Direct parse |
| PDF (text) | ✅ **本次扩展** | pdfplumber |
| Word (.docx) | ✅ **本次扩展** | python-docx（含表格） |
| Image (.png/.jpg) | ✅ **本次扩展** | Tesseract OCR / Qwen-VL（国产模型 Vision） |

### Stage 2 — Problem Parsing (`parse_problems.py` + `classify.py`)

- 题号格式：`Problem N` / `题 N` / `N.` / `N)` / `Q1` / `Exercise 1`；子题 `(a) (b) (c)`
- 分类：关键词优先级 + **T-box 多领域本体**（`classify.py` 现加载 `domain_skills/` 下全部 YAML）
- 领域路由：`matrix` / `ode` / `physics` / `limit` / `epsilon_delta` / `tangent` / `proof` / `conceptual` …

### Stage 3 — Solving（混合引擎）

**SymPy 引擎（确定性，`solve.py` + `solvers_extended.py`）：**

| 领域 | 能力 |
|------|------|
| 微积分极限（基线） | 单侧极限、DNE、夹逼、ε-δ、切线 |
| **线性代数（新）** | 矩阵加/乘/转置/秩、行列式（2×2/3×3）、逆矩阵、特征值+特征向量、线性方程组、向量点积/叉积 |
| **微分方程（新）** | 一阶线性、二阶常系数（dsolve） |
| **大学物理（新）** | 牛顿第二定律、库仑定律、自由落体 |

**国产 LLM 引擎（推理，`llm_solver.py`）：** 证明题、概念题、SymPy 无法计算的多步推理。
Provider 抽象统一 Qwen / Kimi / DeepSeek（OpenAI 兼容 `/chat/completions`），仅用标准库实现。

### Stage 3.5 — Validation (`validate.py`, 新增)

- 特征值：数值回代验证 det(A−λI) ≈ 0
- 逆矩阵：验证 A·A⁻¹ = I
- 线性方程组/ODE：记录可复现的 SymPy 求解命令
- 输出 `4_validation.json`，让"正确率"可核验

### Stage 4 — LaTeX Generation (`render_latex.py`)

- 标准作业模板：课程/姓名/日期页眉、题目+解答交替、`\boxed{}` 答案
- 矩阵正确排版（`pmatrix/bmatrix/matrix` 均支持）
- `--chinese`：`ctexart` 文档类，xelatex 编译，原生中文排版

### Stage 5 — PDF Compilation

- 自动发现本机引擎：MiKTeX（用户级/机器级）、TeX Live、tectonic、PATH
- xelatex 优先（中文最佳），编译 3 遍；找不到引擎时给出安装/Overleaf 提示

## Adding a New Domain

1. 创建 `domain_skills/your_domain.yaml`（参照 `linear_algebra.yaml`：concepts + solution_methods + classification_rules）
2. 在 `solvers_extended.py` 实现求解函数，在 `solve.py` 的 `SOLVERS` 注册
3. 分类 → 检索 → 求解链路自动生效

## File Structure

```
c4c-homework-solver/
├── SKILL.md                        ← 本文件
├── CHALLENGE.md                    ← 挑战指南（L1→L4）
├── requirements.txt
├── scripts/
│   ├── bootstrap.py                ← 依赖自举
│   ├── ingest.py                   ← Stage 1: 摄入（md/pdf/docx/图片）
│   ├── parse_problems.py           ← Stage 2: 解析+分类
│   ├── classify.py                 ← T-box 分类器（多领域）
│   ├── retrieve.py                 ← T-box 检索器
│   ├── solve.py                    ← Stage 3: 求解路由 + SymPy 引擎
│   ├── solvers_extended.py         ← 线代/ODE/物理 求解器（新增）
│   ├── llm_solver.py               ← 国产 LLM 引擎（新增）
│   ├── validate.py                 ← Stage 3.5: 答案验证（新增）
│   ├── render_latex.py             ← Stage 4/5: LaTeX 生成 + PDF 编译
│   ├── config.py                   ← 配置系统 + 引擎发现（新增）
│   └── pipeline.py                 ← 一键流水线
├── domain_skills/
│   ├── calculus_limits.yaml        ← 微积分极限（基线领域）
│   ├── linear_algebra.yaml         ← 线性代数（新增）
│   ├── differential_equations.yaml ← 微分方程（新增）
│   └── physics_mechanics.yaml      ← 大学物理（新增）
├── solver_templates/               ← 参数化求解模板（基线）
├── oracles/                        ← 知识源（教材/学习指南/讲义）
├── references/                     ← LaTeX 模板 + SymPy 速查
├── examples/                       ← 示例作业 + 示例输出
└── test_cases/
    ├── test1_tangent_epsilon_delta.md  ← Berkeley Worksheet 3（基线）
    ├── test2_limits.md                 ← Berkeley Worksheet 4（基线）
    ├── extension_ode_physics.md        ← 扩展领域测试（新增）
    └── llm_reasoning_test.md           ← 推理/证明题路由测试（新增）
```

## Test Results

| 测试集 | 领域 | 引擎 | 结果 |
|--------|------|------|------|
| Berkeley Worksheet 3–4（starter 基线回归） | 微积分极限 | SymPy | 17/18 = **94.4%**（与 Claude 基线一致） |
| **线性代数 作业三（作业原件）** | 线性代数 | SymPy | **10/10 = 100%**，验证 13/13 通过 |
| **扩展领域测试** | ODE + 物理 | SymPy | **6/6 = 100%** |
| **推理类题目测试** | 证明题 | 国产 LLM 引擎（离线降级） | **3/3 = 100%** |

## Limitations

| 限制 | 说明 |
|------|------|
| LLM 引擎需 API Key | 无 Key 时降级为离线模板（证明题给框架不给全文） |
| 扫描件公式 OCR | Tesseract 对数学公式识别弱；推荐 Qwen-VL |
| 图片摄入 | 需本地 Tesseract 或 DashScope API Key |
