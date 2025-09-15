import sys
import re
from bs4 import BeautifulSoup
from pathlib import Path

# ------------------ 动态添加项目根目录 ------------------
# 1. 获取当前脚本文件路径
CURRENT_FILE = Path(__file__).resolve()

# 2. 找到项目根目录（假设项目根目录下有 cfg 目录）
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

# 3. 将项目根目录加入 Python 模块搜索路径
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# ------------------ 导入项目模块 ------------------
from tools.catch import run_curl, config, source

# print("config:", config)
# print("source:", source)


# ------------------ 正式函数 ------------------

def data_parse_page(html):








# # ------------------ 测试 ------------------
def main():



    # data_parse_page(html)

   
    print("config:", config)



if __name__ == "__main__":
    main()