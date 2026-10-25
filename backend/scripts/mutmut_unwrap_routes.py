"""建立可對 API 路由做變異測試的 backend 副本

mutmut 會跳過有裝飾器的函式（@staticmethod、@classmethod 除外），
FastAPI 的路由函式都有 @router.get(...) 之類的裝飾器，因此 api/ 模組不會產生任何變異體。

本腳本把 backend 複製到指定目錄，將指定模組的

    @router.post("/block/{user_id}", status_code=201)
    async def block_user(...): ...

改寫成語意相同的

    async def block_user(...): ...


    block_user = (router.post("/block/{user_id}", status_code=201))(block_user)

套用順序與裝飾器相同（由下往上），每個路由的註冊位置不變，所以路由比對順序一致。
副本的 [tool.mutmut] only_mutate 會設為這些模組。

用法（在 backend/ 執行）：

    python scripts/mutmut_unwrap_routes.py /tmp/mm-api app/api/safety.py app/api/messages.py
    cd /tmp/mm-api && mutmut run --max-children 4
"""

import ast
import re
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
IGNORE = shutil.ignore_patterns(
    "mutants", "__pycache__", ".pytest_cache", ".ruff_cache", "htmlcov", "uploads*", ".venv", "venv"
)


def unwrap(source: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    edits: list[tuple[int, int, list[str]]] = []  # (起始行, 結束行, 取代內容)，0-based、不含結束行

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) or not node.decorator_list:
            continue
        decorators = [ast.get_source_segment(source, d) for d in node.decorator_list]
        applied = node.name
        for decorator in reversed(decorators):
            applied = f"({decorator})({applied})"
        edits.append((node.end_lineno, node.end_lineno, [f"\n\n{node.name} = {applied}\n"]))
        edits.append((node.decorator_list[0].lineno - 1, node.lineno - 1, []))

    for start, end, replacement in sorted(edits, reverse=True):
        lines[start:end] = replacement

    result = "".join(lines)
    ast.parse(result)  # 改寫結果必須仍是合法的 Python
    return result


def main(dest: str, modules: list[str]) -> None:
    dest_dir = Path(dest).resolve()
    if dest_dir.exists():
        sys.exit(f"目標目錄已存在：{dest_dir}")
    shutil.copytree(BACKEND, dest_dir, ignore=IGNORE)

    for module in modules:
        path = dest_dir / module
        path.write_text(unwrap(path.read_text(encoding="utf-8")), encoding="utf-8")

    pyproject = dest_dir / "pyproject.toml"
    only_mutate = "".join(f'\n    "{module}",' for module in modules)
    pyproject.write_text(
        re.sub(
            r"only_mutate = \[.*?\]",
            f"only_mutate = [{only_mutate}\n]",
            pyproject.read_text(encoding="utf-8"),
            flags=re.S,
        ),
        encoding="utf-8",
    )
    print(f"已建立 {dest_dir}，改寫 {len(modules)} 個模組")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
