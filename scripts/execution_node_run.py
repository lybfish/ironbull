"""
执行节点可执行文件入口（供 PyInstaller/Nuitka 打包用）。
直接 import app 对象并传给 uvicorn（避免 PyInstaller 的 string import 问题）。
"""
import os
import sys


def main():
    # 确保应用根在 path 最前
    run_dir = os.path.dirname(os.path.abspath(__file__))
    if run_dir not in sys.path:
        sys.path.insert(0, run_dir)
    os.chdir(run_dir)

    port = int(os.environ.get("PORT", "9101"))
    host = os.environ.get("HOST", "0.0.0.0")

    # 直接导入 app 对象（PyInstaller 可追踪）
    from app.main import app  # noqa: E402

    import uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()
