# C4C 拿来主义说明

> 作者：lsa ｜ 日期：2026-10-07
> 原则：**先理解 Claude 版怎么做的，再迁移；能拿的拿来，拿不动造，造完说清楚差异。**

---

## 1. 从 Starter Kit 拿了什么（直接复用）

| 拿来的资产 | 说明 | 为什么拿 |
|------------|------|----------|
| **五阶段流水线架构** | ingest → parse → solve → render → compile（`pipeline.py` 骨架） | 已在 Claude 上验证端到端可跑，架构合理 |
| **核心解析器** | `parse_problems.py`（题号/子题/公式提取）、`ingest.py`（Markdown + 分段） | 题号格式覆盖中英文，测试充分 |
| **T-box 本体机制** | `classify.py` + `retrieve.py` + `calculus_limits.yaml` | "领域知识驱动求解能力"是 starter kit 的核心洞察，必须继承 |
| **微积分极限求解器** | `solve.py` 中 limit / epsilon_delta / tangent / conceptual 全部函数（约 1300 行） | 这是 94.4% 基线的本体，一行未动地保留 |
| **LaTeX 渲染骨架** | `render_latex.py` 的题目/解答交替、`\boxed` 答案、转义与清理函数 | 排版质量经过 Berkeley 真实试卷验证 |
| **知识源（oracles/）** | Stewart 教材摘编、学习指南、讲义、教学指南 5 份 | 概念题模板的知识来源 |
| **测试资产** | Berkeley Worksheet 3–4、中文工作单/答案 PDF、示例作业 | 直接当作迁移后的回归测试集 |
| **依赖自举** | `bootstrap.py` 自动装缺失依赖 | 降低使用门槛 |

## 2. 用了哪些外部库

| 库 | 用途 | 来源 |
|----|------|------|
| **SymPy** | 全部符号计算：极限/导数/积分/矩阵/特征值/linsolve/dsolve | starter kit 指定，官方文档 |
| **PyYAML** | 加载领域本体 YAML | starter kit 指定 |
| **pdfplumber** | 文本型 PDF 摄入（本次新增启用） | 挑战文档"文档摄入方案对比"推荐 |
| **python-docx** | Word 摄入（段落+表格） | 同上 |
| **MiKTeX / XeLaTeX + ctex** | PDF 编译与中文排版 | 挑战文档"LaTeX 编译方案"推荐 |
| 标准库 `urllib` | 国产 LLM 的 OpenAI 兼容 HTTP 调用 | 自选（避免引入 openai SDK，离线可部署） |

## 3. 改了什么 / 新造了什么（逐文件）

| 文件 | 改动类型 | 具体内容 |
|------|----------|----------|
| `scripts/llm_solver.py` | **新建** | 国产模型引擎：Qwen/Kimi/DeepSeek Provider 注册表、OpenAI 兼容调用（标准库）、结构化输出解析、离线知识库降级 |
| `scripts/solvers_extended.py` | **新建** | 线性代数（矩阵解析 finditer + 加/乘/转置/秩/行列式/逆/特征值/方程组/向量）、ODE（LaTeX 导数记号→Derivative 的占位符解析 + dsolve）、物理（牛顿/库仑/自由落体） |
| `scripts/validate.py` | **新建** | Stage 3.5 答案验证：特征值回代 det(A−λI)≈0、A·A⁻¹=I、可复现命令记录 |
| `scripts/config.py` | **新建** | 配置系统（config.yaml + 环境变量 + 默认值）与 LaTeX 引擎自动发现 |
| `domain_skills/linear_algebra.yaml` | **新建** | 线代本体：7 概念 / 7 求解方法 / 8 条分类规则 |
| `domain_skills/differential_equations.yaml` | **新建** | ODE 本体 |
| `domain_skills/physics_mechanics.yaml` | **新建** | 物理本体 |
| `scripts/solve.py` | **改造** | `solve_matrix/solve_ode` 占位 stub → 接入扩展实现；`solve_proof` → 国产 LLM 路由；`solve_conceptual` 模板未命中 → LLM 兜底；SOLVERS 注册 `physics` |
| `scripts/parse_problems.py` | **改造** | 新增 `physics` 分类关键词与优先级；新增中文概念/证明关键词（解释/什么是/含义/说明/举例/为什么…）；T-box 未命中回退关键词分类 |
| `scripts/classify.py` | **改造** | 从"只加载 calculus_limits.yaml"改为**加载 domain_skills/ 全部领域 YAML**（多领域统一优先级排序）；新增 14 条 类型映射 |
| `scripts/ingest.py` | **改造** | `read_pdf_text/read_docx/read_image_ocr` 三个 NotImplementedError stub → 真实实现（pdfplumber / python-docx / Tesseract+Qwen-VL） |
| `scripts/render_latex.py` | **改造** | `use_chinese` 参数（ctexart 文档类）；`compile_pdf` 重写为引擎自动发现 + xelatex 优先 |
| `scripts/pipeline.py` | **改造** | 新增 `--chinese`、Stage 3.5 验证阶段、参数透传 |
| `SKILL.md` / `README.md` / `requirements.txt` | **重写** | 反映迁移后架构、扩展能力与测试结果 |

## 4. Claude 版本 vs 国产模型版本差异

| 维度 | Claude 基线（starter kit） | 本版本（国产模型方案） |
|------|---------------------------|------------------------|
| 推理引擎 | Claude Code 隐式内嵌（无代码边界、无成本控制） | **显式 LLM 引擎层**（`llm_solver.py`）：Provider 抽象 + 结构化 prompt + 输出解析 |
| 离线可用性 | 推理依赖 Claude，无法离线复现 | **三层兜底**：在线 API → 离线知识库模板 → 诚实标注未解；计算题始终本地 SymPy |
| 可切换性 | 单一引擎 | 环境变量一键切换 Qwen / Kimi / DeepSeek |
| 学科覆盖 | 微积分极限（域外 40%） | + **线性代数 / 微分方程 / 大学物理**（3 个新领域 YAML + 求解器） |
| 输入格式 | 仅 Markdown | + **PDF（pdfplumber）/ Word（python-docx）/ 图片（Tesseract / Qwen-VL）** |
| 正确性保障 | 无验证模块，靠人工 | **Stage 3.5 自动验证**（特征值回代、A·A⁻¹=I）+ 验证报告人工逐题复核 |
| 中文排版 | 中文 PDF 为预制成品（非流水线生成） | 流水线内 `--chinese`（ctexart + xelatex）动态生成中文 PDF |
| 引擎兼容 | 假定 pdflatex/xelatex 在 PATH | 自动发现 MiKTeX（用户级/机器级）/TeX Live/tectonic/PATH |
| 核心域正确率 | 94.4%（17/18） | **94.4%（零退化）** |
| 真实作业（非极限） | 未覆盖 | **线性代数 10/10 = 100%，ODE+物理 6/6 = 100%** |

## 5. 拿来主义的取舍记录

- **没有重写解析器**：starter kit 的题号/公式解析覆盖面已经够用，重写只会引入新 bug——只加了 physics 关键词。
- **没有照搬 stub**：`solve_matrix/solve_ode` 两个"学生扩展点"占位函数按挑战要求补全为真实现，但**保持函数签名与返回结构不变**，路由层零改动。
- **没有引入 openai SDK**：三个国产厂商全是 OpenAI 兼容协议，40 行标准库代码即可覆盖，换来"零额外依赖、离线可部署"。
- **保留了 starter kit 全部测试资产**：把它们升级为迁移后的回归测试集——这正是发现 2 处分类回归的关键。
