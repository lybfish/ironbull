"""
执行节点可执行文件入口（供 PyInstaller/Nuitka 打包用）。
打包时以本文件为入口，会拉起 uvicorn 运行 app.main:app。
"""
import os
import sys


def main():
    port = int(os.environ.get("PORT", "9101"))
    host = os.environ.get("HOST", "0.0.0.0")
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        factory=False,
    )


if __name__ == "__main__":
    # 确保应用根（本文件所在目录，即 dist/execution-node）在 path 最前，以便 import app / libs
    run_dir = os.path.dirname(os.path.abspath(__file__))
    if run_dir not in sys.path:
        sys.path.insert(0, run_dir)
    os.chdir(run_dir)
    main()
