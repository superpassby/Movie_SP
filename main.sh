#!/bin/bash

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

# ------------------ 定义选项及命令（支持多行） ------------------
declare -A MENU

MENU[1]="运行docker|
docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm movie_sp /home/appuser/app/main.sh
"

MENU[2]="写入演员配置到数据库|
python3 $PROJECT_ROOT/tools/Data_Base_Edit/yaml_to_db.py
"

MENU[3]="更新演员作品列表到数据库|
python3 $PROJECT_ROOT/tools/jav_num_up.py
"

MENU[4]="从视频网站，更新作品信息|
python3 $PROJECT_ROOT/tools/jav_info_up.py
"

MENU[5]="[!重复执行!]从视频网站，更新作品信息|
while true; do
    python3 $PROJECT_ROOT/tools/jav_info_up.py
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done
"

MENU[6]="下载视频|
python3 $PROJECT_ROOT/tools/jav_download.py
"

MENU[7]="[!重复执行!]下载视频|
while true; do
    python3 $PROJECT_ROOT/tools/jav_download.py
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done
"

MENU[8]="更新 Javle 中文视频到数据库|
python3 $PROJECT_ROOT/tools/get_id_from_url_jable.py
"
MENU[9]="更新 Javle 中文视频 (前10页) 到数据库|
python3 $PROJECT_ROOT/tools/get_id_from_url_jable.py 1 10
"

MENU[10]="上传 github |
git add $PROJECT_ROOT/.
git commit -m "commit"
git push -u origin main
"



# ------------------ 打印菜单（按数字顺序） ------------------
echo "请选择要执行的操作："
for key in $(echo "${!MENU[@]}" | tr ' ' '\n' | sort -n); do
    desc=$(echo "${MENU[$key]}" | head -n1 | tr -d '\r' | sed 's/|$//')
    echo "$key、$desc"
done


# ------------------ 获取选择 ------------------
if [ $# -eq 0 ]; then
    read -p "输入选项数字（可多个，用空格分隔）: " -a CHOICES
else
    CHOICES=("$@")
fi

# ------------------ 执行命令 ------------------
for CHOICE in "${CHOICES[@]}"; do
    if [[ -n "${MENU[$CHOICE]}" ]]; then
        # 取出菜单的命令部分（去掉第一行描述）
        CMD=$(echo "${MENU[$CHOICE]}" | tail -n +2)
        echo "执行命令："
        echo "$CMD"
        echo ""  # 空行分隔
        eval "$CMD"
        echo ""  # 命令执行后空行分隔
    else
        echo "无效的选择: $CHOICE"
    fi
done
