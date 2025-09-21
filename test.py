#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import datetime
import subprocess
import requests
from collections import deque
import yaml
import datetime

# ------------------ 动态添加项目根目录 ------------------

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "db" / "data.db"
CFG_PATH = PROJECT_ROOT / "cfg" / "config.yaml"
SOURCE_PATH = PROJECT_ROOT / "cfg" / "source.yaml"

# ------------------ 导入数据源脚本 ------------------
from tools.jav_data_fetch import data_AvBase  # 默认用 AvBase（enable=1 且第一个）
from tools.Data_Base_Edit.db_edit import db_edit
from tools.jav_data_fetch import data_AvBase
from switch_clash import switch_clash_group # 导入 switch_clash_group 函数

best_node, best_delay, test_url = switch_clash_group("自定义代理", " | NB", "jable")
print(f"切换到 {best_node}，平均延迟: {best_delay:.2f}ms，测速链接: {test_url}")
      