#!/usr/bin/env bash

# ================== 定义菜单 ==================
declare -A MENU

MENU[1]="进入虚拟环境|
cd /Users/super/Documents/DockerData/Movie_SP && \
source venv/bin/activate
# python3 tools/Data_Base_Edit/yaml_to_db.py && \
# deactivate
"


# 替换文件中所有的 2000.1.1 为 Download_Time




MENU[2]="写入演员配置到数据库|
cd /Users/super/Documents/DockerData/Movie_SP && \
source venv/bin/activate && \
Download_Time=\$(grep '^# Download:' cfg/source.yaml | awk -F': ' '{print \$2}') && \
sed -i '' \"s/2000\.1\.1/\${Download_Time}/g\" cfg/source.yaml && \
python3 tools/Data_Base_Edit/yaml_to_db.py && \
sed -i '' \"/^# Download:/!s/\${Download_Time}/2000.1.1/g\" cfg/source.yaml && \
deactivate
"


MENU[3]="更新演员作品列表到数据库|
cd /Users/super/Documents/DockerData/Movie_SP && \
source venv/bin/activate && \
python3 tools/jav_num_up.py && \
deactivate
"

MENU[4]="[!重复执行!]从视频网站，更新作品信息
(refresh_mode:更新最近90日内除了 state = skip & out_number 外所有的)|
cd /Users/super/Documents/DockerData/Movie_SP
source venv/bin/activate
while true; do
    python3 tools/jav_info_up.py refresh_mode
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        deactivate
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done
"

MENU[5]="[!重复执行!]从视频网站，更新作品信息
(download_mode:跳过state = no_res & download)|
cd /Users/super/Documents/DockerData/Movie_SP
source venv/bin/activate
while true; do
    python3 tools/jav_info_up.py download_mode
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        deactivate
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done
"

MENU[6]="下载视频|
cd /Users/super/Documents/DockerData/Movie_SP && \
source venv/bin/activate && \
python3 tools/jav_download.py && \
deactivate
"

MENU[7]="[!重复执行!]下载视频|
cd /Users/super/Documents/DockerData/Movie_SP
source venv/bin/activate
while true; do
    # python3 tools/jav_download.py
    /usr/local/bin/docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm Movie_SP python3 tools/jav_download.py

    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        deactivate
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done
"

MENU[8]="更新 Jable 中文视频到数据库，并下载|
cd /Users/super/Documents/DockerData/Movie_SP
source venv/bin/activate

while true; do
    python3 tools/get_id_from_url_jable.py
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done

while true; do
    python3 tools/jav_info_up.py Jable_cnSUB
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done

while true; do
    python3 tools/jav_download.py Jable_cnSUB
    if [ \$? -eq 0 ]; then
        echo \"执行成功，退出循环\"
        break
    else
        echo \"执行失败，重新尝试...\"
        sleep 5
    fi
done

deactivate
"

MENU[9]="更新 Jable 中文视频 (前10页) 到数据库|
cd /Users/super/Documents/DockerData/Movie_SP && \
source venv/bin/activate && \
python3 tools/get_id_from_url_jable.py 1 10 && \
deactivate
"

MENU[10]="上传 github|
awk '{if (\$1==\"IsNeedFetchProxy:\") print \"IsNeedFetchProxy: \\\"0\\\"\"; else print}' /Users/super/Documents/DockerData/Movie_SP/cfg/config.yaml > /tmp/config.yaml.tmp && mv /tmp/config.yaml.tmp /Users/super/Documents/DockerData/Movie_SP/cfg/config.yaml
git add . && git commit -m 'commit' && git push -u origin main
awk '{if (\$1==\"IsNeedFetchProxy:\") print \"IsNeedFetchProxy: \\\"1\\\"\"; else print}' /Users/super/Documents/DockerData/Movie_SP/cfg/config.yaml > /tmp/config.yaml.tmp && mv /tmp/config.yaml.tmp /Users/super/Documents/DockerData/Movie_SP/cfg/config.yaml
"

MENU[11]="构建docker 并上传 dockerhub|
docker build -t movie_sp_env:latest . && \
docker tag movie_sp_env:latest superpassby/movie_sp:latest
# docker push superpassby/movie_sp:latest
"

# ================== 打印菜单 ==================
echo "请选择要执行的操作："
for key in $(echo "${!MENU[@]}" | tr ' ' '\n' | sort -n); do
    desc="${MENU[$key]%%|*}"  # 取 | 前面作为描述，保留换行
    echo -e "$key) $desc"
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
        CMD="${MENU[$CHOICE]#*|}"  # 取 | 后面全部内容作为命令，保留多行
        echo "执行命令："
        echo "$CMD"
        echo ""
        eval "$CMD"
        echo ""
    else
        echo "无效的选择: $CHOICE"
    fi
done




