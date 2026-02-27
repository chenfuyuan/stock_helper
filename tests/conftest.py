"""全局测试配置和公共 fixtures。

此文件用于配置测试环境，确保测试可以正确导入 src 模块。
"""

import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
# 这样可以在测试中使用 "src.xxx" 的方式导入模块
root_dir = Path(__file__).resolve().parent.parent
src_path = root_dir / "src"

# 避免重复添加
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
