"""从模型自由文本中稳健地抽取 JSON。

现实情况：即使要求「只输出 JSON」，模型也常常裹上 ```json 围栏、添加解释、
或使用中文引号。这里做四层兜底：

1. 直接解析全文；
2. 抽取 ```json 围栏内容；
3. 用括号配平扫描出第一个完整 JSON 对象/数组；
4. 修复常见瑕疵（中文引号、尾随逗号、BOM）后重试。
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(?P<body>.*?)```", re.DOTALL)


def _repair(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # 去掉对象/数组里最后一个元素后的逗号
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text.strip()


def _scan_balanced(text: str) -> str | None:
    """括号配平扫描：找到第一个完整的 {...} 或 [...]，跳过字符串内的括号。"""
    start = None
    for i, ch in enumerate(text):
        if ch in "{[":
            start = i
            break
    if start is None:
        return None

    opener = text[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_json(text: str) -> Any | None:
    """尽最大努力从文本中取出一个 JSON 值，失败返回 None。"""
    if not text:
        return None

    candidates: list[str] = [text.strip()]
    candidates.extend(m.group("body") for m in _FENCE_RE.finditer(text))
    scanned = _scan_balanced(text)
    if scanned:
        candidates.append(scanned)

    for raw in candidates:
        for attempt in (raw, _repair(raw)):
            try:
                return json.loads(attempt)
            except (json.JSONDecodeError, TypeError):
                continue
    return None
