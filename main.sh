#!/usr/bin/env bash

# ================== 获取项目根目录 ==================
SCRIPT_PATH=$(readlink -f "$0")
PROJECT_ROOT=$(dirname "$SCRIPT_PATH")

while [ ! -d "$PROJECT_ROOT/cfg" ]; do
    PROJECT_ROOT=$(dirname "$PROJECT_ROOT")
    if [ "$PROJECT_ROOT" = "/" ]; then
        echo "未找到项目根目录（缺少 cfg 文件夹）"
        exit 1
    fi
done

# ================== 判断是否在 Docker 容器内 ==================
if [ -f "/.dockerenv" ]; then
    DOCKER_RUN=""  # 容器内直接执行
else
    DOCKER_RUN="/usr/local/bin/docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm Movie_SP"
    PROJECT_ROOT=/app  # 容器内挂载路径
fi

# ================== 定义菜单 ==================
declare -A MENU

# 每个命令用相对仓库路径，Docker 挂载路径 /app
MENU[1]="自定义命令|
$DOCKER_RUN python3 $PROJECT_ROOT/tools/jav_data_fetch/data_AvBase.py 新有菜
"

MENU[2]="写入演员配置到数据库|
$DOCKER_RUN python3 $PROJECT_ROOT/tools/Data_Base_Edit/yaml_to_db.py
"

MENU[3]="更新演员作品列表到数据库|
$DOCKER_RUN python3 $PROJECT_ROOT/tools/jav_num_up.py
"

MENU[4]="从视频网站，更新作品信息|
$DOCKER_RUN python3 $PROJECT_ROOT/tools/jav_info_up.py
"

MENU[5]="[!重复执行!]从视频网站，更新作品信息|
$DOCKER_RUN python3 $PROJECT_ROOT/tools/jav_info_up.py
"

MENU[6]="下载视频|
$DOCKER_RUN python3 $PROJECT_ROOT/tools/jav_download.py
"

MENU[7]="[!重复执行!]下载视频|
while true; do
    $DOCKER_RUN python3 $PROJECT_ROOT/tools/jav_download.py
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done
"

MENU[8]="更新 Jable 中文视频到数据库，并下载|
while true; do
    $DOCKER_RUN python3 $PROJECT_ROOT/tools/get_id_from_url_jable.py
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done

while true; do
    $DOCKER_RUN python3 $PROJECT_ROOT/tools/jav_info_up.py Jable_cnSUB
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done

while true; do
    $DOCKER_RUN python3 $PROJECT_ROOT/tools/jav_download.py Jable_cnSUB
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done
"

MENU[9]="更新 Jable 中文视频 (前10页) 到数据库|
$DOCKER_RUN python3 $PROJECT_ROOT/tools/get_id_from_url_jable.py 1 10
"

MENU[10]="上传 github|
awk '{if (\$1==\"IsNeedFetchProxy:\") print \"IsNeedFetchProxy: \\\"0\\\"\"; else print}' /Users/super/Documents/DockerData/Movie_SP/cfg/config.yaml > /tmp/config.yaml.tmp && mv /tmp/config.yaml.tmp /Users/super/Documents/DockerData/Movie_SP/cfg/config.yaml
git add . && git commit -m 'commit' && git push -u origin main
awk '{if (\$1==\"IsNeedFetchProxy:\") print \"IsNeedFetchProxy: \\\"1\\\"\"; else print}' /Users/super/Documents/DockerData/Movie_SP/cfg/config.yaml > /tmp/config.yaml.tmp && mv /tmp/config.yaml.tmp /Users/super/Documents/DockerData/Movie_SP/cfg/config.yaml
"


MENU[11]="构建docker 并上传 dockerhub|
docker build -t movie_sp_env:latest . && \
docker tag movie_sp_env:latest superpassby/movie_sp:latest && \
docker push superpassby/movie_sp:latest
"

# ================== 打印菜单 ==================
echo "请选择要执行的操作："
for key in $(echo "${!MENU[@]}" | tr ' ' '\n' | sort -n); do
    desc=$(echo "${MENU[$key]}" | head -n1 | cut -d'|' -f1)
    echo "$key) $desc"
done

# ================== 获取选择 ==================
if [ $# -eq 0 ]; then
    read -p "输入选项数字（可多个，用空格分隔）: " -a CHOICES
else
    CHOICES=("$@")
fi

# ================== 执行命令 ==================
for CHOICE in "${CHOICES[@]}"; do
    if [[ -n "${MENU[$CHOICE]}" ]]; then
        CMD=$(echo "${MENU[$CHOICE]}" | cut -d'|' -f2-)
        echo "执行命令："
        echo "$CMD"
        echo ""
        eval "$CMD"
        echo ""
    else
        echo "无效的选择: $CHOICE"
    fi
done
