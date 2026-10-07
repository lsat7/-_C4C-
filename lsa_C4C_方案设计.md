# C4C 方案设计 —— 作业自动求解与排版（Homework Auto-Solver & Formatter）

> 作者：lsa ｜ 挑战：C4C ｜ 日期：2026-10-07
>
> 一句话方案：**在 starter kit（Claude 基线）的"本体驱动五阶段流水线"之上，
> 把推理引擎迁移到国产大模型（Qwen 3.6 为主、Kimi 2.5 备选），
> 把学科覆盖从"微积分极限"扩展到"线性代数 / 微分方程 / 大学物理"，
> 并新增答案自动验证与中文 PDF 排版，使整条流水线端到端可运行、结果可核验。**

---

## 1. 背景与目标

Starter kit 在 Claude Code 上已验证：微积分极限领域 17/18 = **94.4%**，
但域外进阶题（积分、优化、组合、物理）自动求解率仅 **40%**，且推理完全依赖 Claude。

本项目的两个核心任务：

| 任务 | 具体内容 |
|------|----------|
| **1. 迁移引擎** | 把流水线的推理能力从 Claude 迁移到国产大模型，并保证无 API Key 时依然可用 |
| **2. 扩展学科** | 从微积分极限扩展到线性代数、微分方程、大学物理，用真实（非极限）作业验证 |

**完成级别定位：Level 3（Gold）**——用一份线性代数作业（非微积分极限）在国产模型方案下
生成正确 PDF；同时落地了 Level 4 的**部分**能力：

- ✅ 已落地：答案验证模块（`validate.py`）、解题步骤生成、多课程支持（4 个领域 YAML）、配置系统（`config.py`）
- ⏳ 未落地：模型对比报告（Qwen vs Kimi vs Claude，需真实 API Key）、图形自动生成（matplotlib）、GitHub Repo

---

## 2. 总体架构

```
Input (.md / .pdf / .docx / 图片)
   │
   ▼
Stage 1  文档摄入 ingest.py
   │      Markdown 直接读；PDF→pdfplumber；Word→python-docx；
   │      图片→Tesseract OCR / Qwen-VL（国产模型 Vision）
   ▼
Stage 2  题目解析 parse_problems.py + classify.py
   │      题号/子题/公式提取；T-box 多领域本体分类
   │      （classify.py 加载 domain_skills/ 下全部 4 个领域 YAML）
   ▼
Stage 3  混合求解 solve.py + solvers_extended.py + llm_solver.py
   │      ├─ SymPy 引擎（确定性）：极限/ε-δ/切线/矩阵/行列式/特征值/
   │      │   逆矩阵/线性方程组/向量/ODE/物理公式 → 答案精确可复现
   │      └─ 国产 LLM 引擎（推理）：证明题/概念题/多步推理
   │          Qwen 3.6 / Kimi 2.5（OpenAI 兼容接口）→ 无 Key 自动离线降级
   ▼
Stage 3.5 答案验证 validate.py（新增）
   │      特征值回代 det(A−λI)≈0；A·A⁻¹=I；方程组回代；可复现命令记录
   ▼
Stage 4  LaTeX 生成 render_latex.py
   │      作业模板 + 题目/解答交替 + \boxed 答案；--chinese 用 ctexart
   ▼
Stage 5  编译与验证 compile_pdf()
          自动发现 MiKTeX/TeX Live/tectonic；xelatex 优先；编译 3 遍
```

**继承的核心设计原则**（来自 starter kit，验证有效，故原样保留）：

> `Solve rate = domain knowledge coverage`——求解能力由领域知识（domain_skills/*.yaml）决定，
> 而不是硬编码正则。要解更多题 = 新增领域 YAML + 求解器模板，而不是堆代码。

---

## 3. 国产模型选型（选用哪个、为什么）

### 3.1 候选对比

| 模型 | 数学推理 | 中文理解 | 上下文 | 接口 | 成本 | 定位 |
|------|---------|---------|--------|------|------|------|
| **Qwen 3.6（通义千问）** | ★★★★★ | ★★★★★ | 128k | DashScope OpenAI 兼容 | 低，有免费额度 | **首选：计算/求解主力** |
| **Kimi 2.5（Moonshot）** | ★★★★ | ★★★★★ | 长（2.5 支持 128k+） | Moonshot OpenAI 兼容 | 低 | 备选：超长作业/复杂多步推理 |
| DeepSeek | ★★★★★ | ★★★★ | 64k | OpenAI 兼容 | 极低 | 备选，代码+数学强 |

### 3.2 选型结论与理由

**主选 Qwen 3.6，备选 Kimi 2.5，通过环境变量一键切换。** 理由：

1. **数学推理强**：本流水线中 LLM 负责"SymPy 搞不定的部分"——证明题、概念题、
   多步文字推理。Qwen 系列在 MATH / GSM8K 等数学基准上居国产模型第一梯队，中文题面理解无障碍。
2. **接口标准化**：DashScope 提供 OpenAI 兼容的 `/chat/completions`，与 Kimi（Moonshot）、
   DeepSeek 同构 → 一个 `PROVIDERS` 注册表 + 一个 `urllib` 调用函数即可支持全部厂商，
   无需引入 openai SDK（减少依赖、便于离线环境部署）。
3. **配套 Vision 能力**：Qwen-VL 可承担"扫描件/拍照作业"的公式识别（Stage 1 图片摄入），
   一个 API Key 同时解决文本推理与视觉摄入两个环节。
4. **成本可控**：计算题（作业主体）全部走 SymPy 本地计算，**零 API 成本**；
   只有证明/概念题才调用 LLM，单份作业通常 ≤ 3 次调用。

### 3.3 迁移的关键工程决策：离线降级

Claude 基线里"推理"是隐式的（Claude Code 本身就是推理引擎）。迁移后 LLM 变成**外部依赖**，
必然面对"无 Key / 断网 / 限流"。因此设计为三层兜底：

```
证明/概念题 → ① Qwen/Kimi API（在线）
            → ② 离线知识库模板 OFFLINE_TEMPLATES（确定性答案，来自教材/讲义）
            → ③ 明确标记"需要 LLM 求解器"，不假装解出（诚实输出）
```

这保证：**流水线永不中断、已解结果永远可复现、未解结果永远诚实标注**——
这也是评判标准中"输出可核验"的实现方式。

---

## 4. 目标课程与真实作业

| 项 | 内容 |
|----|------|
| **主目标课程** | 线性代数（非微积分极限，满足 Gold 要求） |
| **真实作业** | 《线性代数 作业三（矩阵与线性方程组）》10 题：矩阵加法/乘法、二阶与三阶行列式、逆矩阵、特征值、特征值+特征向量、转置、线性方程组、向量点积 |
| **扩展测试** | 《扩展领域测试》6 题：3 道 ODE（一阶线性 ×2、二阶常系数齐次）+ 3 道物理（牛顿第二定律、库仑定律、自由落体） |
| **推理路由测试** | 《推理类题目测试》3 道证明题（可导必连续 / √2 无理数 / 代数恒等式）——验证证明题正确路由到国产 LLM 引擎 |
| **基线回归** | Berkeley Math 1A Worksheet 3–4（18 题），验证迁移后未损失 starter kit 能力 |

> **关于"真实作业"的说明**：本次挑战为自主完成，无法获取某门在修课程的真实作业原件，
> 故作业原件为**贴近线性代数课程真实难度与题型分布的代表性作业**（10 题，覆盖该课程核心题型）。
> 它满足挑战"非微积分极限"的硬性约束，并已按真实作业标准逐题人工复核（见验证报告）。

---

## 5. 求解策略（SymPy 与 LLM 如何分工）

**核心原则：能用确定性计算就不用 LLM。** 判断标准：答案是否需要"推导性文字"。

| 题型 | 引擎 | 原因 |
|------|------|------|
| 极限 / 导数 / 积分 | SymPy `limit/diff/integrate` | 精确、可复现 |
| 矩阵运算、行列式、逆、秩 | SymPy `Matrix` | 精确分数运算 |
| 特征值 / 特征向量 | SymPy `eigenvals/eigenvects` | 符号解 |
| 线性方程组 | SymPy `linsolve` | 高斯消元 |
| ODE | SymPy `dsolve` | 符号通解 |
| 物理公式题 | SymPy 代入计算（公式内置） | 数值精确 |
| **证明题** | **国产 LLM**（离线降级：证明框架模板） | 需要演绎文字 |
| **概念题**（"what is meant by…"） | 模板优先 → 未命中走 **国产 LLM** | 需要解释性文字 |
| 画图题 | 标注"需图形工具"（诚实跳过） | 后续可用 matplotlib 扩展 |

**路由实现**：Stage 2 分类出领域类型（matrix/ode/physics/limit/proof/conceptual…），
Stage 3 的 `SOLVERS` 字典路由；T-box 未命中的题回退关键词分类，再未命中归入 conceptual → LLM。

---

## 6. 排版与输出策略

- **LaTeX 模板**：继承 starter kit 的 `render_latex.py`（题目 `\problem{}` + 解答 `\solution{}` 交替、最终答案 `\boxed{}` 高亮、fancyhdr 页眉页脚）。
- **中文支持**：`--chinese` 时改用 `ctexart` 文档类 + xelatex 编译（MiKTeX 安装 ctex 宏包），
  中文题面、中文页眉、数学公式（含矩阵 `pmatrix/bmatrix/matrix`）全部正确排版。
- **编译引擎发现**：`config.find_latex_engines()` 自动探测 MiKTeX（用户级/机器级）、TeX Live、tectonic、PATH；xelatex 优先（中文最佳），失败自动降级 pdflatex/lualatex。
- **交付 PDF**：主作业输出 `lsa_C4C_output.pdf`（中文排版，2 页，10 题全部带步骤与框选答案）。

---

## 7. 风险与边界情况处理

| 风险 | 处理方案 |
|------|----------|
| 无国产模型 API Key | 离线知识库模板降级，计算题不受影响（SymPy 本地） |
| LLM 返回格式不稳定 | prompt 强制【步骤】/【答案】标记 + 解析器容错（`parse_llm_response`） |
| 扫描型 PDF 公式识别差 | pdfplumber 只适合文本型 PDF；扫描件走 Qwen-VL；文档中明确标注该边界 |
| 分类误路由（已踩坑） | "det" 曾误匹配 "determine" → 收窄为 "det("；T-box 未命中回退关键词分类 |
| LaTeX 环境缺失 | 引擎自动发现 + 明确的安装提示 + Overleaf 替代方案 |
| 数学表达式解析失败 | 逐层 try/except，失败题诚实标注原因（不产出错误答案） |

---

## 8. 里程碑与产出对照

| 阶段 | 产出 |
|------|------|
| 理解基线 + 方案设计 | 本文档 |
| 迁移与扩展开发 | `lsa_C4C_homework-solver/`（12 个脚本 + 4 个领域 YAML） |
| 真实作业测试 | `lsa_C4C_作业原件.md` → `lsa_C4C_output.pdf`（10/10 正确） |
| 正确性验证 | `lsa_C4C_验证报告.md`（16 题对比 + 基线回归 + 自动验证 13/13） |
| 教学说明 | `lsa_C4C_教学说明.md` |
| AI 使用记录 | `lsa_C4C_AI日志.md` |
| 拿来主义说明 | `lsa_C4C_拿来说明.md` |
| 复盘 | `AAR.md` |
