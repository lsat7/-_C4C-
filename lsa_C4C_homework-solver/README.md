# C4C 作业自动求解与排版（国产模型迁移扩展版）

**SIAS AI+X Elite 20 — Coding for Cognition Challenge**

在 Claude Code 基线（starter kit）之上构建的作业自动求解流水线：
**引擎迁移到国产大模型（Qwen 3.6 / Kimi 2.5）+ 学科扩展（线性代数 / 微分方程 / 大学物理）+ 答案自动验证 + 中文 PDF 排版**。

## 提交物对应测试结果

| 测试集 | 领域 | 结果 |
|--------|------|------|
| Berkeley Math 1A Worksheet 3–4（基线回归） | 微积分极限 | 17/18 = **94.4%**（与 Claude 基线一致） |
| **线性代数 作业三（真实作业，非极限）** | 线性代数 | **10/10 = 100%**，自动验证 13/13 通过 |
| 扩展领域测试 | ODE + 大学物理 | **6/6 = 100%** |

## Quick Start

```bash
# 1) 安装依赖（Python 3.10+）
pip install -r requirements.txt

# 2) 跑示例（微积分极限，验证基线）
python scripts/pipeline.py examples/sample_homework.md output/

# 3) 跑真实作业（线性代数，中文 PDF）
python scripts/pipeline.py 线代作业.md output/ --compile --chinese \
    --course "线性代数" --student "你的名字"

# 4) PDF / Word 输入（本次扩展）
python scripts/pipeline.py homework.pdf output/ --compile --chinese
```

## 两条主线（对应挑战要求）

**1. 引擎迁移（Claude → 国产模型）**
- 证明题 / 概念题 / 多步推理 → 国产 LLM 引擎（`llm_solver.py`）
- Provider 抽象：Qwen（DashScope）/ Kimi（Moonshot）/ DeepSeek，OpenAI 兼容接口，标准库实现
- 无 API Key 自动降级为确定性离线知识库模板——流水线永不中断、结果可复现
- 计算题始终由 SymPy 确定性求解（不依赖 API，答案可核验）

**2. 学科扩展（极限 → 线代/ODE/物理）**
- 领域知识驱动：新增 `domain_skills/linear_algebra.yaml`、`differential_equations.yaml`、`physics_mechanics.yaml`
- 求解器：`scripts/solvers_extended.py`（矩阵运算/行列式/逆/特征值/方程组/向量、dsolve、牛顿定律/库仑定律/自由落体）
- 输入扩展：`scripts/ingest.py` 新增 PDF（pdfplumber）、Word（python-docx）、图片（OCR / Qwen-VL）
- 验证扩展：`scripts/validate.py` 特征值回代、A·A⁻¹=I 等自动核验

## What's in the Repo

```
├── SKILL.md                  ← 技能说明（架构 + 用法）
├── requirements.txt
├── scripts/                  ← 五阶段流水线（ingest → parse → solve → validate → render → compile）
├── domain_skills/            ← 领域本体：calculus_limits + linear_algebra + ODE + physics
├── solver_templates/         ← 参数化求解模板（基线保留）
├── oracles/                  ← 知识源（教材 / 学习指南 / 讲义 / 范例）
├── test_cases/               ← Berkeley 基线测试 + 扩展领域测试
├── references/               ← LaTeX 模板 + SymPy 速查
└── examples/                 ← 示例作业
```

## Key Insight

```
Solve rate = domain knowledge coverage（领域知识覆盖率）
```

求解能力由领域知识决定，不由代码复杂度决定。要解更多题 → 扩展领域 YAML + 求解器模板，
而不是堆正则。这也是 starter kit 用 5 道进阶题（域外仅 40%）实证验证过的结论。

## Requirements

- Python 3.10+（开发验证环境：3.13）
- SymPy, PyYAML（核心）；pdfplumber, python-docx（扩展输入）
- XeLaTeX + ctex（中文 PDF 输出；Windows 推荐 MiKTeX）
- 可选：DASHSCOPE_API_KEY / MOONSHOT_API_KEY（启用国产 LLM 求解证明题）
