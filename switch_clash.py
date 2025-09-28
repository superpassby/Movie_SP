import requests
import time
import json
import os

API = "http://10.10.10.88:9090"
SECRET = "123456"
HEADERS = {"Authorization": f"Bearer {SECRET}"}

SWITCH_LOG_FILE = 'switch_log.json'
MIN_SWITCH_INTERVAL = 30  # 秒

def current_timestamp():
    return int(time.time())

def read_switch_log():
    if os.path.exists(SWITCH_LOG_FILE):
        try:
            with open(SWITCH_LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def write_switch_log(log):
    with open(SWITCH_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=4, ensure_ascii=False)

def get_all_proxies():
    r = requests.get(f"{API}/proxies", headers=HEADERS)
    r.raise_for_status()
    return r.json()["proxies"]

def parse_keywords(user_input: str):
    """
    支持两种逻辑：
    1. 用逗号分隔，如 "jp,日本" → 必须同时包含所有关键词
    2. 用空格分隔，如 "jp 日本" → 包含任意一个关键词
    """
    if "|" in user_input:
        exclude_raw, include_raw = user_input.split("|", 1)
    else:
        exclude_raw, include_raw = user_input, ""

    def parse_part(raw):
        raw = raw.strip()
        if not raw:
            return [], "all"
        if "," in raw:
            return [x.strip() for x in raw.split(",") if x.strip()], "all"
        else:
            return [x.strip() for x in raw.split() if x.strip()], "any"

    exclude, exclude_mode = parse_part(exclude_raw)
    include, include_mode = parse_part(include_raw)

    return (exclude, exclude_mode), (include, include_mode)

def filter_nodes(node_names, proxies, exclude_tuple, include_tuple):
    exclude, exclude_mode = exclude_tuple
    include, include_mode = include_tuple

    result = []
    for name in node_names:
        # 排除逻辑
        if exclude:
            if exclude_mode == "all" and all(ex in name for ex in exclude):
                continue
            if exclude_mode == "any" and any(ex in name for ex in exclude):
                continue

        # 包含逻辑
        if include:
            if include_mode == "all" and not all(inc in name for inc in include):
                continue
            if include_mode == "any" and not any(inc in name for inc in include):
                continue

        if name not in proxies:
            continue

        result.append(proxies[name])

    return result

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

def switch_group(group_name, node_name):
    r = requests.put(
        f"{API}/proxies/{group_name}",
        headers=HEADERS,
        json={"name": node_name},
    )
    r.raise_for_status()

def switch_clash_group(preselect_group, filter_input, preselect_url):
    proxies = get_all_proxies()
    switch_log = read_switch_log() or {}
    groups = {k: v for k, v in proxies.items() if v.get("type") == "Selector"}
    group_info = groups.get(preselect_group)
    if not group_info:
        print(f"[INFO] 未找到策略组 {preselect_group}")
        return None, None, preselect_url

    # 解析过滤条件
    exclude_tuple, include_tuple = parse_keywords(filter_input)
    candidates = filter_nodes(group_info.get("all", []), proxies, exclude_tuple, include_tuple)

    if not candidates:
        print(f"[INFO] 策略组 {preselect_group} 没有符合条件的节点，保持当前节点不切换")
        return None, None, preselect_url

    # 获取测速 URL
    urls = set()
    for p in proxies.values():
        extra = p.get("extra", {})
        urls.update(extra.keys())
    urls = sorted(urls)
    candidates_url = [u for u in urls if preselect_url in u]
    test_url = candidates_url[0] if candidates_url else None

    # 过滤延迟
    valid_candidates = []
    for p in candidates:
        delay = avg_delay(p, test_url) if test_url else None
        if delay is not None:
            valid_candidates.append((p["name"], delay))

    if not valid_candidates:
        print(f"[INFO] 策略组 {preselect_group} 没有可用的节点（无延迟数据），保持当前节点不切换")
        return None, None, test_url

    # 已使用节点
    group_log = switch_log.get(preselect_group, {})
    last_switch_time = group_log.get("_last_switch_time", 0)
    used_nodes = set(group_log.get("_used_nodes", []))
    now = current_timestamp()

    # 同一策略组在 MIN_SWITCH_INTERVAL 内不切换
    if now - last_switch_time < MIN_SWITCH_INTERVAL:
        print(f"[INFO] 策略组 {preselect_group} 切换过于频繁，需等待 {MIN_SWITCH_INTERVAL}s")
        return None, None, test_url

    # 过滤已用节点
    available_candidates = [(n, d) for n, d in valid_candidates if n not in used_nodes]
    if not available_candidates:
        used_nodes = set()
        available_candidates = valid_candidates

    # 选择延迟最低的节点
    best_node, best_delay = min(available_candidates, key=lambda x: x[1])

    # 切换节点
    switch_group(preselect_group, best_node)
    print(f"[INFO] 策略组 {preselect_group} 已切换到 {best_node}, 平均延迟: {best_delay:.2f}ms, 测速链接: {test_url}")

    # 更新日志
    used_nodes.add(best_node)
    group_log["_last_switch_time"] = now
    group_log["_used_nodes"] = list(used_nodes)
    switch_log[preselect_group] = group_log
    write_switch_log(switch_log)

    return best_node, best_delay, test_url

# # 测试切换函数
# if __name__ == "__main__":
#     test_group = "自定义代理"
#     test_filter = "| jp 日本"
#     test_url_key = "jable"
#     switch_clash_group(test_group, test_filter, test_url_key)

# 测试切换函数
if __name__ == "__main__":
    test_group = "自定义代理"
    test_filter = "|"
    test_url_key = "jable"
    switch_clash_group(test_group, test_filter, test_url_key)
