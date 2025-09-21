#!/bin/bash
set -euo pipefail

# ------------------ 获取项目根目录 ------------------
SCRIPT_PATH=$(readlink -f "$0")
PROJECT_ROOT=$(dirname "$SCRIPT_PATH")
while [ ! -d "$PROJECT_ROOT/cfg" ]; do
    PROJECT_ROOT=$(dirname "$PROJECT_ROOT")
    if [ "$PROJECT_ROOT" = "/" ]; then
        echo "未找到项目根目录（缺少 cfg 文件夹）"
        exit 1
    fi
done



CONFIG_FILE="$PROJECT_ROOT/cfg/config.yaml"

# 读取 Jellyfin 配置
JELLYFIN_URL=$(grep -E '^\s*Jellyfin:' "$CONFIG_FILE" | sed 's/.*: "\(.*\)"/\1/')
API_KEY=$(grep -E '^\s*Jellyfin_API:' "$CONFIG_FILE" | sed 's/.*: "\(.*\)"/\1/')

SAVE_SUB=$(grep -E '^\s*SavePath_Sub:' "$CONFIG_FILE" | sed 's/.*: "\(.*\)"/\1/')
DRIVE_PATH=$(grep -E '^\s*DRIVE_Path:' "$CONFIG_FILE" | sed 's/.*: "\(.*\)"/\1/')

SAVE_PATH_REAL="${DRIVE_PATH}${SAVE_SUB#/DRIVE/}"

MRGX="每日更新"
HJ="合集"
MRGX_TMP="${SAVE_PATH_REAL}每日更新_待删除"

mkdir -p "$MRGX_TMP"


# 获取媒体库 ID
for var in MRGX HJ; do
    library_name="${!var}"
    library_id=$(curl -s "${JELLYFIN_URL}/Library/VirtualFolders" \
        -H "X-Emby-Token: ${API_KEY}" \
        | jq -r --arg name "$library_name" '.[] | select(.Name==$name) | .ItemId')
    eval "$var='$library_id'"
    echo "库 $library_name 的 ID: ${!var}"
done

# 获取用户 ID
USER_ID=$(curl -s "${JELLYFIN_URL}/Users" \
    -H "X-Emby-Token: ${API_KEY}" \
    | jq -r '.[0].Id')
echo "用户 ID: $USER_ID"



echo $MRGX_TMP


move_watched_unfavorite() {
    echo "执行删除操作：移动已观看且未收藏的媒体到 $MRGX_TMP"

    folders_to_delete=$(curl -s -G "${JELLYFIN_URL}/Users/${USER_ID}/Items" \
        -H "X-Emby-Token: ${API_KEY}" \
        --data-urlencode "Recursive=true" \
        --data-urlencode "ParentId=${MRGX}" \
        --data-urlencode "fields=Path,UserData" \
    | jq -r '.Items[] | select(.UserData.Played == true and .UserData.IsFavorite == false) | .Path')

    for path in $folders_to_delete; do
        # target_dir 直接使用路径，避免 dirname 出错
        # target_dir="$path"
        target_dir=$(dirname "$path")

        # 保护措施：不要移动媒体库根目录
        if [ "$target_dir" = "$SAVE_PATH_REAL" ]; then
            echo "⚠️ 跳过媒体库根目录: $target_dir"
            continue
        fi

        folder_name=$(basename "$target_dir")
        dest="$MRGX_TMP/$folder_name"

        # 如果目标已存在，加时间戳
        if [ -e "$dest" ]; then
            timestamp=$(date +%s)
            dest="${MRGX_TMP}/${folder_name}_$timestamp"
        fi

        echo "移动文件夹: $target_dir -> $dest"
        # mv "$target_dir" "$dest"
    done

    echo "删除操作完成！"
}




refresh_library() {
    echo "正在刷新 Jellyfin 媒体库..."
    curl -s -X POST "${JELLYFIN_URL}/Library/Refresh" \
        -H "X-Emby-Token: ${API_KEY}" \
        --data-urlencode "Id=${MRGX}" > /dev/null
    echo "Jellyfin 媒体库刷新完成！"
}


# 主入口：支持参数或交互
ACTION="${1:-}"

if [ -z "$ACTION" ]; then
    echo "请选择操作:"
    echo "1) 删除已观看且未收藏的媒体"
    echo "2) 移动已收藏的媒体"
    read -rp "请输入 1 或 2: " ACTION
fi

case "$ACTION" in
    1) move_watched_unfavorite ;;
    2) move_favorites ;;
    *) echo "无效选项: $ACTION"; exit 1 ;;
esac

refresh_library

