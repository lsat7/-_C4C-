#!/usr/bin/env python3
"""
Stage 1: Document Ingestion
读取作业文件（Markdown / PDF / Word / 图片），输出结构化文本。

Starter kit 仅实现 Markdown 读取。
PDF / Word / OCR 留给学生扩展（见 C4C.md Level 2）。

用法:
    python ingest.py input_file output.json
    python ingest.py homework.md problems.json
"""

import json
import re
import sys
from pathlib import Path


# ─────────────────────────────────────────────
# 核心函数：读取不同格式
# ─────────────────────────────────────────────

def read_markdown(filepath: str) -> str:
    """读取 Markdown 文件，返回原始文本。"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def read_pdf_text(filepath: str) -> str:
    """
    读取文本型 PDF（扩展实现）。
    需要: pip install pdfplumber
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "PDF 摄入需要 pdfplumber。\n提示: pip install pdfplumber"
        )
    pages_text = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            pages_text.append(t)
    return "\n\n".join(pages_text)


def read_docx(filepath: str) -> str:
    """
    读取 Word 文档（扩展实现）。
    需要: pip install python-docx
    """
    try:
        import docx
    except ImportError:
        raise ImportError(
            "Word 摄入需要 python-docx。\n提示: pip install python-docx"
        )
    document = docx.Document(filepath)
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    # 表格内容也一并提取
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            paragraphs.append(" | ".join(cells))
    return "\n".join(paragraphs)


def read_image_ocr(filepath: str) -> str:
    """
    OCR 读取图片/扫描件（扩展实现——本地 Tesseract + 国产模型 Vision 两种方案）。

    1) 本地 OCR（免费，需安装 Tesseract）:
         pip install pytesseract Pillow
    2) 国产模型 Vision（Qwen-VL，公式识别更强，需 API Key）:
         设置 DASHSCOPE_API_KEY 后走通义千问 VL 识别。
    """
    # 方案 2 优先：国产模型 Vision（公式识别质量高）
    api_key = None
    try:
        import os
        api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")
    except Exception:
        pass
    if api_key:
        text = _ocr_via_qwen_vl(filepath, api_key)
        if text:
            return text
    # 方案 1 兜底：本地 Tesseract
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise ImportError(
            "OCR 摄入需要 pytesseract 与 Pillow。\n"
            "提示: pip install pytesseract Pillow\n"
            "或设置 DASHSCOPE_API_KEY 使用国产模型 Vision。"
        )
    return pytesseract.image_to_string(Image.open(filepath), lang="chi_sim+eng")


def _ocr_via_qwen_vl(filepath: str, api_key: str) -> str:
    """用通义千问 VL（qwen-vl）识别图片中的题目。失败返回空串。"""
    import base64
    import json as _json
    import urllib.request
    try:
        with open(filepath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        payload = {
            "model": "qwen-vl-plus",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": "请把图片中的数学题目逐字转写为 Markdown，数学公式用 LaTeX（$...$）表示。"},
                ],
            }],
        }
        req = urllib.request.Request(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            data=_json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception:
        return ""


# ─────────────────────────────────────────────
# 格式检测与路由
# ─────────────────────────────────────────────

FORMAT_HANDLERS = {
    ".md":   read_markdown,
    ".txt":  read_markdown,       # 纯文本同 Markdown 处理
    ".pdf":  read_pdf_text,
    ".docx": read_docx,
    ".png":  read_image_ocr,
    ".jpg":  read_image_ocr,
    ".jpeg": read_image_ocr,
}


def detect_format(filepath: str) -> str:
    """根据扩展名检测文件格式。"""
    ext = Path(filepath).suffix.lower()
    if ext not in FORMAT_HANDLERS:
        raise ValueError(f"不支持的文件格式: {ext}\n支持: {list(FORMAT_HANDLERS.keys())}")
    return ext


def ingest(filepath: str) -> dict:
    """
    主入口：读取任意格式的作业文件，返回结构化结果。

    返回:
        {
            "source_file": "homework.md",
            "format": ".md",
            "raw_text": "...",
            "sections": [
                {"title": "Section Title", "content": "..."},
                ...
            ]
        }
    """
    filepath = str(filepath)
    ext = detect_format(filepath)
    handler = FORMAT_HANDLERS[ext]

    raw_text = handler(filepath)

    # 基础分段：按 Markdown 标题或空行分段
    sections = split_into_sections(raw_text)

    return {
        "source_file": Path(filepath).name,
        "format": ext,
        "raw_text": raw_text,
        "sections": sections,
    }


def split_into_sections(text: str) -> list:
    """
    将文本按 Markdown 标题分段。
    如果没有标题，整个文本作为一个 section。
    """
    sections = []
    current_title = "Untitled"
    current_lines = []

    for line in text.split("\n"):
        # 检测 Markdown 标题
        heading_match = re.match(r"^(#{1,4})\s+(.+)", line)
        if heading_match:
            # 保存前一个 section
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append({
                        "title": current_title,
                        "content": content,
                    })
            current_title = heading_match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # 保存最后一个 section
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({
                "title": current_title,
                "content": content,
            })

    return sections


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print("用法: python ingest.py <输入文件> <输出.json>")
        print("示例: python ingest.py homework.md problems.json")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    if not Path(input_path).exists():
        print(f"错误: 文件不存在 — {input_path}")
        sys.exit(1)

    print(f"[Stage 1] 文档摄入: {input_path}")
    result = ingest(input_path)

    # 确保输出目录存在
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  格式: {result['format']}")
    print(f"  分段: {len(result['sections'])} sections")
    print(f"  输出: {output_path}")


if __name__ == "__main__":
    main()
