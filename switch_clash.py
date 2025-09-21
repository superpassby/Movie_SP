import requests
import time
import json
import os

API = "http://10.10.10.88:9090"
SECRET = "123456"
HEADERS = {"Authorization": f"Bearer {SECRET}"}

# 定义切换记录文件
SWITCH_LOG_FILE = 'switch_log.json'

# 获取当前时间戳（秒）
def current_timestamp():
    return int(time.time())

# 读取切换日志
def read_switch_log():
    if os.path.exists(SWITCH_LOG_FILE):
        with open(SWITCH_LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# 写入切换日志
def write_switch_log(log):
    with open(SWITCH_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=4)

# 获取所有代理节点
def get_all_proxies():
    r = requests.get(f"{API}/proxies", headers=HEADERS)
    r.raise_for_status()
    return r.json()["proxies"]

# 解析用户输入的排除和包含关键字
def parse_keywords(user_input: str):
    if "|" in user_input:
        exclude_raw, include_raw = user_input.split("|", 1)
    else:
        exclude_raw, include_raw = user_input, ""
    
    exclude = [x.strip() for x in exclude_raw.split(",") if x.strip()]
    include = [x.strip() for x in include_raw.split(",") if x.strip()]
    return exclude, include

# 过滤节点：排除包含指定关键字的节点，包含必须包含指定关键字的节点
def filter_nodes(node_names, proxies, exclude, include):
    result = []
    for name in node_names:
        if any(ex in name for ex in exclude):
            continue
        if include and not all(inc in name for inc in include):
            continue
        if name not in proxies:
            continue
        result.append(proxies[name])
    return result

# 获取节点的平均延迟
def avg_delay(proxy, test_url):
    extra = proxy.get("extra", {})
    if test_url not in extra:
        return None
    history = extra[test_url].get("history", [])
    if not history:
        return None
    delays = [h["delay"] for h in history if h.get("delay", 0) > 0]
    if not delays:
        return None
    return sum(delays) / len(delays)

# 切换策略组
def switch_group(group_name, node_name):
    r = requests.put(
        f"{API}/proxies/{group_name}",
        headers=HEADERS,
        json={"name": node_name},
    )
    r.raise_for_status()

# 检查节点是否在5分钟内已经切换过
def is_node_recently_switched(node_name, log):
    now = current_timestamp()
    # 如果节点在5分钟内切换过
    if node_name in log:
        last_switch_time = log[node_name]
        if now - last_switch_time < 300:  # 300秒即5分钟
            return True
    return False

# 核心函数：根据用户输入切换代理节点
def switch_clash_group(preselect_group, filter_input, preselect_url):
    # 获取所有代理节点
    proxies = get_all_proxies()

    # 读取切换日志
    switch_log = read_switch_log()

    # 获取策略组
    groups = {k: v for k, v in proxies.items() if v.get("type") == "Selector"}

    # 解析过滤条件
    exclude, include = parse_keywords(filter_input)

    # 获取指定策略组的节点
    group_info = groups.get(preselect_group)
    if not group_info:
        raise ValueError(f"未找到策略组 {preselect_group}")

    candidates = filter_nodes(group_info.get("all", []), proxies, exclude, include)
    if not candidates:
        raise ValueError("没有符合条件的节点")

    # 收集所有测速 URL
    urls = set()
    for p in proxies.values():
        extra = p.get("extra", {})
        urls.update(extra.keys())
    urls = sorted(urls)

    if not urls:
        raise ValueError("没有找到可用的测速链接")

    # 选择测速链接
    candidates_url = [u for u in urls if preselect_url in u]
    if not candidates_url:
        raise ValueError("未找到测速链接")
    test_url = candidates_url[0]

    # 查找未切换过的节点
    available_candidates = []
    for p in candidates:
        if is_node_recently_switched(p["name"], switch_log):
            continue
        available_candidates.append(p)

    # 如果所有节点都已经切换过且超过5分钟，则重新开始
    if not available_candidates:
        print("所有符合条件的节点已经在5分钟内切换过，重新开始。")
        switch_log = {}  # 清空日志
        write_switch_log(switch_log)
        available_candidates = candidates  # 重新使用所有符合条件的节点

    # 选择延迟最低的节点
    best_node, best_delay = None, None
    for p in available_candidates:
        delay = avg_delay(p, test_url)
        if delay is None:
            continue
        if best_delay is None or delay < best_delay:
            best_node, best_delay = p["name"], delay

    if not best_node:
        raise ValueError("没有找到可用的节点")

    # 切换策略组
    switch_group(preselect_group, best_node)
    print(f"策略组 {preselect_group} 已切换到 {best_node}\n平均延迟: {best_delay:.2f}ms, 测速链接: {test_url}")

    # 更新切换日志
    switch_log[best_node] = current_timestamp()
    write_switch_log(switch_log)

    return best_node, best_delay, test_url

# 如果需要外部调用该函数，按以下方式调用：
if __name__ == "__main__":
    # 示例调用，使用外部传参
    switch_clash_group("rou", "BM,jp | NB,香港", "rou")
