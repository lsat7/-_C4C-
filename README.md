# Homework Auto-Solver & Formatter

**作业自动求解与排版流水线 —— 国产大模型迁移扩展版**

> 输入一份数学作业文件，一条命令产出可直接提交的答案 PDF。
> 求解能力由领域知识驱动，而非硬编码正则。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![SymPy](https://img.shields.io/badge/SymPy-1.12%2B-green)](https://www.sympy.org/)
[![LaTeX](https://img.shields.io/badge/LaTeX-XeLaTeX%20%2B%20ctex-orange)](https://miktex.org/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](#许可证)

---

## 项目简介

本项目是 **SIAS AI+X Elite 20 — Coding for Cognition Challenge（C4C）** 的完整交付物。

它把「拿到作业 → 手动解题 → 手动排版 → 提交 PDF」这条原本需要数小时的链路，
压缩成**一条命令、全自动、结果可核验**的流水线。项目在 Claude Code 基线
（starter kit）之上完成两件核心工作：

| 主线 | 内容 |
|------|------|
| **1. 引擎迁移** | 推理引擎从 Claude 迁移到**国产大模型**（Qwen / Kimi / DeepSeek，OpenAI 兼容接口），并内置**确定性离线降级** —— 无 API Key、断网时流水线依然可运行、结果可复现 |
| **2. 学科扩展** | 学科覆盖从「微积分极限」扩展到**线性代数 / 微分方程 / 大学物理**，并新增 **PDF、Word、图片摄入** 与 **答案自动验证** |

核心设计原则（继承自 starter kit，已被实证验证）：

```
Solve rate = domain knowledge coverage（领域知识覆盖率）
```

求解能力由**领域知识**（`domain_skills/*.yaml`）决定，而不是代码复杂度。
要解更多题 → 新增领域 YAML + 求解器模板，而不是堆正则表达式。

---

## 主要功能

### 五阶段流水线（+1 个验证阶段）

```
Input (.md / .pdf / .docx / 图片)
   │
   ▼
Stage 1   ingest.py            文档摄入：Markdown 直读 / PDF→pdfplumber
   │                           Word→python-docx / 图片→Tesseract·Qwen-VL
   ▼
Stage 2   parse_problems.py    题目解析：题号·子题·公式提取
   │     classify.py           T-box 多领域本体分类 + 关键词回退
   ▼
Stage 3   solve.py             混合求解引擎
   │     solvers_extended.py   ├─ SymPy（确定性）：极限/矩阵/行列式/特征值/
   │     llm_solver.py         │   逆矩阵/方程组/向量/ODE/物理公式
   │                           └─ 国产 LLM（推理）：证明题/概念题/多步推理
   ▼
Stage 3.5 validate.py          答案自动验证：特征值回代 det(A−λI)≈0、
   │                           A·A⁻¹=I、方程组回代残差（输出 4_validation.json）
   ▼
Stage 4   render_latex.py      LaTeX 生成：题目+解答交替、\boxed 答案、
   │                           矩阵排版；--chinese 时用 ctexart
   ▼
Stage 5   compile_pdf()        PDF 编译：自动发现 MiKTeX/TeX Live/tectonic，
                              xelatex 优先（中文最佳），编译 3 遍
```

### 功能特性

- **混合求解引擎** —— 能用确定性计算就不用 LLM：
  - **SymPy 引擎（计算题）**：精确、可复现、零 API 成本
  - **国产 LLM 引擎（推理题）**：证明题、概念题、多步文字推理
- **三层兜底降级** —— 保证流水线永不中断：
  ```
  证明/概念题 → ① 在线 API（Qwen/Kimi）
             → ② 离线知识库模板 OFFLINE_TEMPLATES（确定性答案）
             → ③ 明确标注"需 LLM 求解"，不假装解出（诚实输出）
  ```
- **多格式文档摄入** —— Markdown / 文本型 PDF / Word（含表格）/ 图片（OCR）
- **答案自动验证** —— Stage 3.5 数值回代校验，让"正确率"可核验、可复现
- **中文 PDF 排版** —— `ctexart` + XeLaTeX，中文题面与数学公式（含矩阵）正确渲染
- **LaTeX 引擎自动发现** —— 探测 MiKTeX（用户级/机器级）/ TeX Live / tectonic / PATH，无需手动配置
- **多领域本体** —— 微积分极限、线性代数、微分方程、大学物理四个领域 YAML
- **一键接入国产模型** —— 环境变量切换 Qwen / Kimi / DeepSeek，无需引入 `openai` SDK

### 已验证的求解能力

| 测试集 | 领域 | 引擎 | 结果 |
|--------|------|------|------|
| Berkeley Math 1A Worksheet 3–4（基线回归） | 微积分极限 | SymPy | 17/18 = **94.4%**（与 Claude 基线一致，零退化） |
| **线性代数 作业三**（主交付作业，非极限） | 线性代数 | SymPy | **10/10 = 100%**，自动验证 13/13 通过 |
| **扩展领域测试** | ODE + 大学物理 | SymPy | **6/6 = 100%** |
| **推理类题目测试** | 证明题 | 国产 LLM 引擎（离线降级） | **3/3 = 100%** |

---

## 环境要求

| 项目 | 要求 | 说明 |
|------|------|------|
| **Python** | 3.10+（开发验证环境 3.13） | 核心运行环境 |
| **Python 依赖** | `sympy>=1.12`、`pyyaml>=6.0` | 必需 |
| **扩展输入依赖** | `pdfplumber>=0.9`、`python-docx>=0.8` | PDF / Word 摄入 |
| **LaTeX**（可选，用于 PDF） | MiKTeX / TeX Live + `ctex` 宏包 | Windows 推荐 [MiKTeX](https://miktex.org/download) |
| **OCR**（可选） | Tesseract 或 DashScope API Key | 图片/扫描件摄入 |
| **国产模型 API Key**（可选） | `DASHSCOPE_API_KEY` / `MOONSHOT_API_KEY` | 启用 LLM 求解证明题 |

> **无 LaTeX、无 API Key 也能跑通** —— 计算题由 SymPy 本地求解；
> 证明/概念题自动降级为离线模板；生成 `.tex` 后可上传 [Overleaf](https://www.overleaf.com) 在线编译。

---

## 安装步骤

### 1. 获取代码

```bash
git clone https://github.com/lsat7/-_C4C-.git
cd --_-C4C-/lsa_C4C_homework-solver
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
# 等价于：pip install sympy pyyaml pdfplumber python-docx
```

### 3. 安装 LaTeX（可选，但强烈推荐）

```bash
# Windows（MiKTeX）：官网安装后，中文排版需要 ctex 宏包
mpm --install=ctex

# macOS
brew install --cask mactex-no-gui

# Ubuntu / Debian
sudo apt install texlive-xetex texlive-lang-chinese
```

> 流水线会自动发现已安装的 LaTeX 引擎，无需手动配置 PATH。

### 4. 配置国产大模型 API Key（可选）

```bash
# 通义千问 Qwen（推荐，数学推理强）
export DASHSCOPE_API_KEY=sk-你的key       # https://dashscope.aliyuncs.com
export C4C_LLM_PROVIDER=qwen

# 或 Kimi（长上下文、复杂推理）
export MOONSHOT_API_KEY=sk-你的key        # https://api.moonshot.cn
export C4C_LLM_PROVIDER=kimi
```

---

## 使用方法

### 基础用法

```bash
python scripts/pipeline.py <输入作业文件> <输出目录> [选项]
```

### 常用示例

```bash
# ① 示例作业（微积分极限，验证基线）
python scripts/pipeline.py examples/sample_homework.md output/

# ② 中文作业 + 编译 PDF（推荐）
python scripts/pipeline.py 作业.md output/ --compile --chinese \
    --course "线性代数" --student "张三" --title "线性代数 作业三 解答"

# ③ PDF / Word 输入
python scripts/pipeline.py homework.pdf  output/ --compile --chinese
python scripts/pipeline.py homework.docx output/ --compile --chinese
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `input` | （必填） | 作业文件路径（`.md` / `.pdf` / `.docx` / `.png` / `.jpg`） |
| `output_dir` | （必填） | 输出目录 |
| `--compile` | 关闭 | 编译 LaTeX → PDF |
| `--chinese` | 关闭 | 中文排版（`ctexart` + XeLaTeX） |
| `--course` | `Mathematics` | 课程名（页眉 + 标题） |
| `--student` | `Student` | 学生姓名 |
| `--title` | `Homework Solutions` | 文档标题 |
| `--no-validate` | 关闭 | 跳过 Stage 3.5 答案验证 |

### 作业文件的格式要求

解析器识别以下题号格式：

```
题号：Problem 1 / 题 1 / 1. / 1) / Q1 / Exercise 1
子题：(a) (b) (c) 或 a) b) c)
分段：## Questions / ## Problems / ## Additional Problems / ## Part A
```

数学公式用 LaTeX 写在 `$...$`（行内）或 `$$...$$`（独立行）内；
矩阵使用 `\begin{pmatrix} ... \end{pmatrix}`（也支持 `bmatrix` / `matrix`）。

示例：

```markdown
Problem 3. 求二阶行列式 $\det(A)$，其中
$$A = \begin{pmatrix} 3 & 1 \\ 4 & 2 \end{pmatrix}.$$
```

### 输出文件

| 文件 | 内容 |
|------|------|
| `1_ingested.json` | 文档摄入结果（含分段边界） |
| `2_parsed.json` | 结构化题目（题号 / 公式 / 分类） |
| `3_solutions.json` | 解答（步骤 + 答案 + 求解状态） |
| `4_validation.json` | 答案验证报告（特征值回代、逆矩阵校验等） |
| `homework.tex` | 格式化 LaTeX 源文件（可上传 Overleaf） |
| `homework.pdf` | 编译后的 PDF（使用 `--compile` 时生成） |

### 支持的课程 / 题型

| 领域 | 支持的题型 |
|------|-----------|
| **线性代数** | 矩阵加 / 乘 / 转置 / 秩、行列式（2×2 / 3×3）、逆矩阵、特征值与特征向量、线性方程组、向量点积 / 叉积 / 模长 |
| **微分方程** | 一阶线性、二阶常系数齐次（`dsolve`，可含初始条件） |
| **大学物理** | 牛顿第二定律 F=ma、库仑定律、自由落体 / 匀加速运动 |
| **微积分（基线）** | 极限（单侧 / DNE / 夹逼 / 无穷）、ε-δ 邻域与计算、切线、导数 / 积分 / 级数、概念题模板 |
| **证明 / 概念题** | 由国产 LLM 引擎（Qwen / Kimi）推理；无 Key 时离线模板给出证明框架 |

> 画图题会被明确标注「需图形工具」，诚实跳过而非产出错误结果。

### 如何新增一门课程

1. 新建 `domain_skills/你的领域.yaml`（参照 `linear_algebra.yaml` 的
   `concepts` / `solution_methods` / `classification_rules` 三段结构）；
2. 在 `solvers_extended.py` 实现求解函数，并在 `solve.py` 的 `SOLVERS` 字典中注册；
3. 分类 → 检索 → 求解链路自动生效，无需改动其他模块。

---

## 目录结构

```
-_-C4C-/
├── README.md                          ← 本文件
├── lsa_C4C_方案设计.md                ← 方案设计与架构说明
├── lsa_C4C_验证报告.md                ← 正确性验证报告（逐题对比 + 基线回归）
├── lsa_C4C_教学说明.md                ← 安装 / 使用 / 支持范围 / FAQ
├── lsa_C4C_拿来说明.md                ← 拿来主义说明（复用与改动清单）
├── lsa_C4C_AI日志.md                  ← AI 使用全程记录
├── lsa_C4C_AAR.md                     ← 复盘（失败清单 + 改进方案）
├── lsa_C4C_作业原件.md                ← 主作业原件（线性代数 10 题）
├── lsa_C4C_output.pdf                 ← 主输出 PDF（中文排版，10/10 解答）
├── lsa_C4C_扩展测试解答.pdf           ← 扩展领域测试 PDF（ODE + 物理 6/6）
├── lsa_C4C_Word摄入测试.docx          ← Word 摄入测试件
├── lsa_C4C_homework-solver.skill      ← 技能包（zip 打包，含完整源码）
│
├── lsa_C4C_homework-solver/           ← 源代码目录
│   ├── SKILL.md                       ← 技能总说明（架构 + 用法 + 测试结果）
│   ├── CHALLENGE.md                   ← 挑战指南
│   ├── requirements.txt               ← 依赖清单
│   ├── scripts/                       ← 五阶段流水线
│   │   ├── pipeline.py                ← 一键流水线（入口）
│   │   ├── config.py                  ← 配置系统 + LaTeX 引擎自动发现
│   │   ├── bootstrap.py               ← 依赖自举
│   │   ├── ingest.py                  ← Stage 1：摄入（md / pdf / docx / 图片）
│   │   ├── parse_problems.py          ← Stage 2：解析 + 分类
│   │   ├── classify.py                ← T-box 分类器（多领域）
│   │   ├── retrieve.py                ← T-box 检索器
│   │   ├── solve.py                   ← Stage 3：求解路由 + SymPy 引擎
│   │   ├── solvers_extended.py        ← 线代 / ODE / 物理 求解器
│   │   ├── llm_solver.py              ← 国产 LLM 引擎（Provider 抽象 + 离线降级）
│   │   ├── validate.py                ← Stage 3.5：答案验证
│   │   └── render_latex.py            ← Stage 4/5：LaTeX 生成 + PDF 编译
│   ├── domain_skills/                 ← 领域本体（YAML）
│   │   ├── calculus_limits.yaml       ← 微积分极限（基线领域）
│   │   ├── linear_algebra.yaml        ← 线性代数（新增）
│   │   ├── differential_equations.yaml← 微分方程（新增）
│   │   └── physics_mechanics.yaml     ← 大学物理（新增）
│   ├── solver_templates/              ← 参数化求解模板（基线）
│   ├── oracles/                       ← 知识源（教材 / 学习指南 / 讲义 / 范例）
│   ├── references/                    ← LaTeX 模板 + SymPy 速查
│   ├── examples/                      ← 示例作业 + 示例输出
│   └── test_cases/                    ← 测试集
│       ├── test1_tangent_epsilon_delta.md   ← Berkeley Worksheet 3（基线）
│       ├── test2_limits.md                  ← Berkeley Worksheet 4（基线）
│       ├── extension_ode_physics.md         ← 扩展领域测试（新增）
│       └── llm_reasoning_test.md            ← 推理 / 证明题路由测试（新增）
│
├── lsa_C4C_output/                    ← 主作业流水线中间产物 + PDF
├── lsa_C4C_ext_output/                ← 扩展领域测试输出
├── lsa_C4C_llm_output/                ← 推理题测试输出
└── lsa_C4C_docx_output/               ← Word 摄入测试输出
```

---

## 常见问题

**Q1：没有 API Key 能跑吗？**
能。计算题（作业主体）由 SymPy 本地求解；证明 / 概念题降级为离线知识库模板，
输出会标注 `solver=llm_offline`，结果确定可复现。

**Q2：PDF 编译失败怎么办？**
先确认已安装 LaTeX（MiKTeX / TeX Live）。中文排版需要 `ctex` 宏包
（MiKTeX 执行 `mpm --install=ctex`）。也可把生成的 `homework.tex` 直接上传 Overleaf 在线编译。
> 注意：MiKTeX 首次编译需预热（可能超过 60 秒），请耐心等待或调高超时设置。

**Q3：扫描版 PDF / 拍照的作业能识别吗？**
文本型 PDF 用 `pdfplumber` 直接提取；扫描件 / 图片走 Qwen-VL（需 DashScope Key）或本地 Tesseract。
数学公式的 OCR 精度有限，推荐 Qwen-VL 路径。

**Q4：怎么切换国产模型？**
`export C4C_LLM_PROVIDER=qwen`（或 `kimi` / `deepseek`），配合对应 API Key 即可。

---

## 已知限制

| 限制 | 说明 |
|------|------|
| LLM 引擎需 API Key | 无 Key 时降级为离线模板（证明题给完整框架，不保证覆盖所有题型） |
| 扫描件公式 OCR | Tesseract 对数学公式识别较弱；推荐 Qwen-VL |
| 图片摄入 | 需本地安装 Tesseract 或配置 DashScope API Key |
| 画图题 | 暂不自动绘图，诚实标注「需图形工具」（后续可用 matplotlib 扩展） |

---

## 许可证

本项目基于 **MIT License** 发布，可自由用于学习、研究与二次开发。

> 本项目为 **SIAS AI+X Elite 20 — Coding for Cognition Challenge（C4C）** 的挑战交付物。
> 所继承的 starter kit 资产（解析器、T-box 机制、微积分极限求解器、LaTeX 渲染骨架、知识源）
> 详见 [lsa_C4C_拿来说明.md](lsa_C4C_拿来说明.md) 的逐文件说明。
