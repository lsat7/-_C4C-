# C4C 教学说明 —— 安装、使用与支持范围

> 作者：lsa ｜ 日期：2026-10-07
> 面向对象：想用本技能自动求解作业的同学 / 评审人

---

## 1. 这是什么

一个**端到端作业自动求解与排版流水线**：输入一份数学作业文件（Markdown / PDF / Word / 图片），
自动完成「读取 → 解析 → 求解 → 验证 → 排版 → 编译 PDF」，一条命令产出可直接提交的答案 PDF。

核心能力：**SymPy 确定性求解**（计算题，精确可复现）+ **国产大模型推理**（证明/概念题，Qwen/Kimi）
+ **答案自动验证** + **中文 PDF 排版**。

---

## 2. 安装步骤

### 2.1 环境要求

- Python 3.10+（开发验证环境 3.13）
- （可选）XeLaTeX 用于编译 PDF；Windows 推荐 [MiKTeX](https://miktex.org/download)
- （可选）国产模型 API Key，用于证明/概念题推理

### 2.2 安装 Python 依赖

```bash
cd lsa_C4C_homework-solver
pip install -r requirements.txt
# 等价于：pip install sympy pyyaml pdfplumber python-docx
```

### 2.3 安装 LaTeX（用于生成 PDF，可选但强烈推荐）

- **Windows（MiKTeX）**：官网安装后，首次使用需要 `ctex` 宏包（中文排版），
  命令：`mpm --install=ctex`（MiKTeX 包管理器），或编译时按提示自动安装。
- **macOS**：`brew install --cask mactex-no-gui`
- **Ubuntu**：`sudo apt install texlive-xetex texlive-lang-chinese`

> 流水线会自动发现已安装的 LaTeX 引擎（MiKTeX/TeX Live/tectonic/PATH），无需手动配置。

### 2.4 （可选）配置国产大模型 API Key

```bash
# 通义千问 Qwen（推荐）
export DASHSCOPE_API_KEY=sk-你的key       # 获取：https://dashscope.aliyuncs.com
export C4C_LLM_PROVIDER=qwen

# 或 Kimi
export MOONSHOT_API_KEY=sk-你的key        # 获取：https://api.moonshot.cn
export C4C_LLM_PROVIDER=kimi
```

> **不配置也能用**：计算题全部由 SymPy 本地求解，不依赖任何 API；
> 证明/概念题在无 Key 时自动降级为离线知识库模板，流水线不中断。

---

## 3. 使用方法

### 3.1 一条命令跑通

```bash
python scripts/pipeline.py <输入作业文件> <输出目录> [选项]
```

**最小示例（Markdown 输入，英文）：**

```bash
python scripts/pipeline.py examples/sample_homework.md output/
```

**真实作业（中文，生成 PDF）：**

```bash
python scripts/pipeline.py ../lsa_C4C_作业原件.md ../lsa_C4C_output \
    --compile --chinese \
    --course "线性代数" --student "lsa" --title "线性代数 作业三 解答"
```

**PDF / Word 输入：**

```bash
python scripts/pipeline.py homework.pdf  output/ --compile --chinese
python scripts/pipeline.py homework.docx output/ --compile --chinese
```

### 3.2 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `input` | （必填） | 作业文件路径（.md / .pdf / .docx / .png / .jpg） |
| `output_dir` | （必填） | 输出目录 |
| `--compile` | 关闭 | 编译 LaTeX → PDF |
| `--chinese` | 关闭 | 中文排版（ctexart + xelatex） |
| `--course` | Mathematics | 课程名（页眉 + 标题） |
| `--student` | Student | 学生姓名 |
| `--title` | Homework Solutions | 文档标题 |
| `--no-validate` | 关闭 | 跳过 Stage 3.5 答案验证 |

### 3.3 输出文件

| 文件 | 内容 |
|------|------|
| `1_ingested.json` | 文档摄入结果（分段） |
| `2_parsed.json` | 结构化题目（题号/公式/分类） |
| `3_solutions.json` | 解答（步骤 + 答案 + 求解状态） |
| `4_validation.json` | 答案验证报告 |
| `homework.tex` | LaTeX 源文件（可上传 Overleaf） |
| `homework.pdf` | 编译后的 PDF（`--compile` 时） |

### 3.4 作业文件怎么写（题号格式）

解析器识别以下题号格式：

```
Problem 1 / 题 1 / 1. / 1) / Q1 / Exercise 1
子题：(a) (b) (c) 或 a) b) c)
分段：## Questions / ## Problems / ## Additional Problems / ## Part A
```

数学公式用 LaTeX 写在 `$...$`（行内）或 `$$...$$`（独立行）内；矩阵用
`\begin{pmatrix} ... \end{pmatrix}`（也可 `bmatrix/matrix`）。

示例（线性代数）：

```markdown
Problem 3. 求二阶行列式 $\det(A)$，其中
$$A = \begin{pmatrix} 3 & 1 \\ 4 & 2 \end{pmatrix}.$$
```

---

## 4. 支持哪些课程 / 题型

| 领域 | 支持的题型 |
|------|-----------|
| **线性代数** | 矩阵加/乘/转置/秩、行列式（2×2/3×3）、逆矩阵、特征值、特征值+特征向量、线性方程组、向量点积/叉积/模长 |
| **微分方程** | 一阶线性、二阶常系数齐次（dsolve，可含初始条件） |
| **大学物理** | 牛顿第二定律 F=ma、库仑定律、自由落体/匀加速运动 |
| **微积分（基线）** | 极限（单侧/DNE/夹逼/无穷）、ε-δ 邻域与计算、切线、导数/积分/级数、概念题模板（连续性/IVT/洛必达等） |
| **证明/概念题** | 由国产 LLM 引擎（Qwen/Kimi）推理；无 Key 时离线模板给证明框架 |

---

## 5. 常见问题（FAQ）

**Q1：没有 API Key 能跑吗？**
能。计算题（作业主体）由 SymPy 本地求解；证明/概念题降级为离线知识库模板，
输出会标注 `solver=llm_offline`，结果确定可复现。

**Q2：为什么 PDF 编译失败？**
先确认已安装 LaTeX（MiKTeX/TeX Live）。中文排版需要 ctex 宏包（MiKTeX 执行 `mpm --install=ctex`）。
也可把生成的 `homework.tex` 直接上传 [Overleaf](https://www.overleaf.com) 在线编译。

**Q3：扫描版 PDF / 拍照的作业能识别吗？**
文本型 PDF 用 pdfplumber 直接提取；扫描版/图片用 Qwen-VL（需 DashScope Key）或本地 Tesseract。
数学公式的 OCR 精度有限，推荐 Qwen-VL 路径（见 `ingest.py` 的 `_ocr_via_qwen_vl`）。

**Q4：如何新增一门课？**
1. 新建 `domain_skills/你的领域.yaml`（参照 `linear_algebra.yaml` 的 concepts/solution_methods/classification_rules）；
2. 在 `solvers_extended.py` 写求解函数并在 `solve.py` 的 `SOLVERS` 注册；
3. 分类→求解链路自动生效。

**Q5：怎么切换国产模型？**
`export C4C_LLM_PROVIDER=qwen` 或 `kimi` / `deepseek`，配合对应 API Key 即可。

---

## 6. 目录速览

```
lsa_C4C_homework-solver/
├── SKILL.md            ← 技能总说明
├── README.md           ← 快速上手
├── requirements.txt
├── scripts/            ← 流水线（ingest/parse/solve/validate/render/compile）
├── domain_skills/      ← 4 个领域本体（极限/线代/ODE/物理）
├── solver_templates/   ← 基线求解模板
├── oracles/            ← 知识源（教材/讲义/范例）
├── examples/           ← 示例作业
├── references/         ← LaTeX 模板 + SymPy 速查
└── test_cases/         ← 基线测试 + 扩展测试
```
