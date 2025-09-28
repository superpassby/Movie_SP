# 计划任务，jable 中文视频下载
if docker ps --format '{{.Names}}' | grep -iq 'Jable_cnSUB'; then
    echo "存在包含 Jable_cnSUB 的容器，退出"
else
    echo "不存在包含 Jable_cnSUB 的容器，启动下载"
    /usr/local/bin/docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm Jable_cnSUB
fi



python3 -m venv venv

source venv/bin/activate



/usr/local/bin/docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm Movie_SP python3



# 删除所有 nfo jpg
find /Volumes/NVME_2T/000-Movie_SP /Volumes/SATA_SSD_2T/000-Movie_SP \
  -type f \( -name "*.nfo" -o -name "*.jpg" \) \
  -delete


state：
- download 已下载(已下载的可能没中文字幕，还是要获取m3u8)
- wait 等待下载 （下载时选择_下载时只看这一个指标）
- no_res 无资源（下载时跳过），获取 m3u8 时不跳过，获取m3u8 后，改为 wait （在 info——up 中完成）
- skip 获取 m3u8 下载 都跳过
- out_number 获取 m3u8 下载 都跳过


@To do 
1、根据合集 添加番号
2、写入 数据库的 通用函数 输入要写入 的 表 列的数据 返回 等待时间 启用文件锁，自动增加列
3、下载的公共函数 输入 下载链接 保存位置，文件名 返回 下载 文件锁，记录下载文件名 可多开下载

libicu-dev
```
# 确保拉取最新代码
git checkout main
git pull origin main

# 上传代码
git add .
git commit -m "commit"
git push -u origin main
```

强制推送 
git push -f origin main


# 在 Dockerfile 所在目录执行：
构建docker镜像
cd /Users/super/Documents/DockerData/Movie_SP
docker build -t movie_sp_env:latest .

上传docker镜像：
docker tag movie_sp_env:latest superpassby/movie_sp:latest
docker push superpassby/movie_sp:latest



docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm Movie_SP





docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm movie_sp python3 tools/Data_Base_Edit/yaml_to_db.py

docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm movie_sp python3 tools/jav_num_up.py

docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm movie_sp python3 tools/get_id_from_url_jable.py


docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm movie_sp python3 tools/jav_download.py Jable_cnSUB


docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm movie_sp python3 tools/jav_download.py 藤森里穗

docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm movie_sp python3 tools/jav_download.py 白峰美羽



docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm movie_sp ./main.sh



docker compose -f /Users/super/Documents/DockerData/Movie_SP/docker-compose.yaml run --rm movie_sp ./main.sh



