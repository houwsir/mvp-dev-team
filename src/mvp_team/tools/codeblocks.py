"""从模型输出中解析「带路径的代码块」，并安全落盘。

约定：工程师角色输出的每个文件都写成如下形式——

    ```file:backend/app/main.py
    <文件内容>
    ```

解析器只认第一行 info string 里带 `file:` 或 `file=` 的代码块，
普通代码块（例如示意片段、shell 示例）会被忽略，不会误写进产物目录。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from mvp_team.state import FileArtifact

# ```file:path/to/file.ext \n ... ```  或  ```python file=path/to/file.ext \n ... ```
_FENCE_RE = re.compile(
    r"^[ \t]*```[ \t]*(?P<info>[^\n`]*)\n(?P<body>.*?)(?:\n[ \t]*```[ \t]*$|\Z)",
    re.MULTILINE | re.DOTALL,
)

_PATH_IN_INFO_RE = re.compile(r"(?:file\s*[:=]\s*)(?P<path>[^\s;]+)")


@dataclass
class ParsedFile:
    path: str
    content: str
    lang: str = ""


def parse_file_blocks(text: str, role: str = "") -> list[ParsedFile]:
    """抽出所有 `file:` 代码块。顺序保持模型输出顺序。"""
    files: list[ParsedFile] = []
    for match in _FENCE_RE.finditer(text or ""):
        info = (match.group("info") or "").strip()
        path_match = _PATH_IN_INFO_RE.search(info)
        if not path_match:
            continue
        path = path_match.group("path").strip().strip("`'\"")
        if not path:
            continue
        lang = info[: path_match.start()].strip() or ""
        body = match.group("body")
        # 去掉模型偶尔多加的结尾换行噪点，同时保留内部缩进
        files.append(ParsedFile(path=path, content=body.rstrip("\n") + "\n", lang=lang))
    return files


def _safe_join(root: Path, rel_path: str) -> Path:
    """把相对路径安全地拼到 root 下，阻止 `../` 逃逸与绝对路径写入。"""
    cleaned = rel_path.strip().lstrip("/")
    candidate = (root / cleaned).resolve()
    root_resolved = root.resolve()
    if root_resolved != candidate and root_resolved not in candidate.parents:
        raise ValueError(f"非法产物路径（越出输出目录）：{rel_path}")
    return candidate


def materialize(
    files: list[ParsedFile],
    output_dir: Path,
    role: str,
    project: str,
) -> tuple[list[FileArtifact], list[str]]:
    """将解析出的文件写入磁盘，返回 (artifact 列表, 警告列表)。"""
    artifacts: list[FileArtifact] = []
    warnings: list[str] = []
    for item in files:
        try:
            target = _safe_join(output_dir, item.path)
        except ValueError as exc:  # pragma: no cover - 防御性分支
            warnings.append(str(exc))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item.content, encoding="utf-8")
        artifacts.append(
            FileArtifact(
                path=item.path,
                role=role,
                project=project,
                bytes=len(item.content.encode("utf-8")),
                lines=item.content.count("\n"),
            )
        )
    return artifacts, warnings
