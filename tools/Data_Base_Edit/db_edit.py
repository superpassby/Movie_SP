# tools/Data_Base_Edit/db_edit.py
import sqlite3
from pathlib import Path

# ------------------ 数据库路径 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "db").exists())
DB_PATH = PROJECT_ROOT / "db" / "data.db"

class DBEdit:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def fetch_all(self, sql, params=None):
        """执行查询，返回所有结果"""
        params = params or ()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return rows

    def fetch_one(self, sql, params=None):
        """执行查询，返回单条结果"""
        params = params or ()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
        return row

    def execute(self, sql, params=None):
        """执行 INSERT/UPDATE/DELETE 或其他修改操作"""
        params = params or ()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount  # 返回影响行数

    def execute_many(self, sql, seq_of_params):
        """批量执行修改操作"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, seq_of_params)
            conn.commit()
            return cursor.rowcount

# 实例化单例，方便其他文件直接导入使用
db_edit = DBEdit()
