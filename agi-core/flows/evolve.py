"""
evolve.py — L2 自动优化层（v2: 调用 learn_evolve.py 进化引擎）
向后兼容：直接运行此文件会委托给 learn_evolve.py

Usage:
    cd ~/agi && python3 -m flows.evolve
    cd ~/agi && python3 -m flows.evolve --dry-run
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """委托给 learn_evolve.py。"""
    evolve_script = Path(__file__).parent / "learn_evolve.py"
    if not evolve_script.exists():
        print("[evolve] learn_evolve.py 不存在，跳过")
        return

    # 透传命令行参数
    args = [sys.executable, str(evolve_script)] + sys.argv[1:]
    result = subprocess.run(args)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
