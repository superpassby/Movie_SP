import yaml
import subprocess
from pathlib import Path

PROJECT_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "cfg").exists())

CONFIG_FILE = PROJECT_ROOT / "cfg" / "config.yaml"
SOURCE_FILE = PROJECT_ROOT / "cfg" / "source.yaml"
ACTRESS_DIR = PROJECT_ROOT / "data"
CURL = PROJECT_ROOT / "tools" / "curl_chrome116"


# 确保目录存在（相当于 mkdir -p）
ACTRESS_DIR.mkdir(parents=True, exist_ok=True)

# 直接加载 YAML 文件
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

with open(SOURCE_FILE, "r", encoding="utf-8") as f:
    source = yaml.safe_load(f)

# print("config:", config)
# print("source:", source)

def run_curl(url: str) -> str:
    # 基本命令
    # cmd = [str(CURL)]
    # 跟随重定向
    cmd = [str(CURL), "-L"]

    # 判断是否需要代理
    if config.get("IsNeedCurlProxy") == "y":
        cmd += ["-x", config["Proxy_Catch"]]

    # URL 一定放最后
    cmd.append(url)

    print(f"[DEBUG] 执行: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"[DEBUG] curl 执行失败: {result.stderr}")
            return ""
        return result.stdout
    except Exception as e:
        print(f"[DEBUG] curl 异常: {e}")
        return ""

# 使用示例
# html = run_curl("https://jable.tv/models/kojima-minami/")
# print(html)



