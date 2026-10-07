#!/usr/bin/env python3
"""
配置系统（Level 4）：学生信息、课程信息、模型选择、LaTeX 引擎、模板偏好。

配置文件 config.yaml 放在技能根目录（可选）。未提供时使用默认值。
优先级：命令行参数 > 环境变量 > config.yaml > 默认值。

示例 config.yaml:
    student: 张三
    course: 线性代数
    title: 作业解答
    llm_provider: qwen          # qwen | kimi | deepseek
    latex_engine: xelatex        # xelatex | pdflatex
    use_chinese: true            # 中文排版（xelatex + ctex）
"""

import os
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

SKILL_ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "student": "lsa",
    "course": "Mathematics",
    "title": "Homework Solutions",
    "llm_provider": "qwen",
    "latex_engine": "xelatex",
    "use_chinese": False,
}


def _load_yaml():
    cfg_path = SKILL_ROOT / "config.yaml"
    if cfg_path.exists() and yaml is not None:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    return {}


def get_config() -> dict:
    """合并默认值 + config.yaml + 环境变量，返回完整配置。"""
    cfg = dict(DEFAULTS)
    cfg.update(_load_yaml())

    env_map = {
        "student": "C4C_STUDENT",
        "course": "C4C_COURSE",
        "title": "C4C_TITLE",
        "llm_provider": "C4C_LLM_PROVIDER",
        "latex_engine": "C4C_LATEX_ENGINE",
    }
    for key, env in env_map.items():
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    if os.environ.get("C4C_USE_CHINESE"):
        cfg["use_chinese"] = os.environ["C4C_USE_CHINESE"].lower() in ("1", "true", "yes")
    return cfg


def find_latex_engines() -> dict:
    """在常见安装路径中查找 LaTeX 引擎（MiKTeX / TeX Live / tectonic）。"""
    candidates = []
    # MiKTeX（用户级）
    miktex_bin = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64"
    candidates.append(miktex_bin)
    # MiKTeX（机器级）
    candidates.append(Path("C:/Program Files/MiKTeX/miktex/bin/x64"))
    # TeX Live
    candidates.append(Path("C:/texlive"))
    for name in ["xelatex", "pdflatex", "lualatex"]:
        for base in candidates:
            p = base / f"{name}.exe"
            if p.exists():
                yield (name, str(p))
    # PATH 中的引擎
    import shutil
    for name in ["pdflatex", "xelatex", "lualatex", "tectonic"]:
        found = shutil.which(name)
        if found:
            yield (name, found)


if __name__ == "__main__":
    import json
    print(json.dumps(get_config(), ensure_ascii=False, indent=2))
    print("LaTeX engines:", list(find_latex_engines()))
