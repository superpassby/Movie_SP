import re
from pathlib import Path

def get_nfo_paths():
    dirs = [
        "/Volumes/SATA_SSD_2T/000-Movie_SP/000-JAV/",
        "/Volumes/NVME_2T/000-Movie_SP/000-JAV/"
    ]
    path_nfo = []
    for d in dirs:
        base = Path(d)
        if base.exists():
            for f in base.rglob("*.nfo"):
                path_nfo.append(str(f))
    return path_nfo

def check_nfo_files(path_nfo_list):
    not_match = []
    not_avbase = []

    for path in path_nfo_list:
        p = Path(path)
        video_id = p.parent.name  # 上一级目录名

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"读取失败 {p}: {e}")
            continue

        # 提取 <title> 和 <metatubeid>
        title_match = re.search(r"<title>(.*?)</title>", content, re.S | re.I)
        metatubeid_match = re.search(r"<metatubeid>(.*?)</metatubeid>", content, re.S | re.I)

        title = title_match.group(1).strip() if title_match else ""
        metatubeid = metatubeid_match.group(1).strip() if metatubeid_match else ""



        # 检查逻辑
        if video_id.upper() not in metatubeid.upper():
            not_match.append((p, metatubeid))   # 保存 Path 和 metatubeid
        elif "AVBASE" not in metatubeid:
            not_avbase.append(str(p))

    # 打印 not_match
    print("\n=== not_match (metatubeid 不含 video_id) ===")
    delete_targets = []
    for p, mid in not_match:
        print(f"{p} | metatubeid: {mid}")
        parent = p.parent
        candidates = list(parent.glob("*.nfo")) + list(parent.glob("*.jpg"))
        if candidates:
            print("  将删除以下文件：")
            for c in candidates:
                print(f"    {c}")
            delete_targets.extend(candidates)
    print(f"共 {len(not_match)} 个\n")

    # 确认删除
    if delete_targets:
        confirm = input("确认要删除以上文件吗？(y/n): ").strip().lower()
        if confirm == "y":
            for c in delete_targets:
                try:
                    c.unlink()
                    print(f"已删除 {c}")
                except Exception as e:
                    print(f"删除失败 {c}: {e}")
        else:
            print("取消删除。")

    return not_match, not_avbase



if __name__ == "__main__":
    nfo_files = get_nfo_paths()
    print(f"共找到 {len(nfo_files)} 个 nfo 文件")
    not_match, not_avbase = check_nfo_files(nfo_files)