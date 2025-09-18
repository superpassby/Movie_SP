state：
- download 已下载(已下载的可能没中文字幕，还是要获取m3u8)
- wait 等待下载 （下载时选择_下载时只看这一个指标）
- no_res 无资源（下载时跳过），获取 m3u8 时不跳过，获取m3u8 后，改为 wait （在 info——up 中完成）
- skip 获取 m3u8 下载 都跳过
- out_number 获取 m3u8 下载 都跳过


### 控制类文件 ###
### 对所有的活动进行控制，所有的设置都在这里
## source.yaml
# 控制 演员 相关的 信息
- 演员名称 （可有多个,第一个为中文名称，也是写入数据库等名称，后面的，是不同的 source_catch_*.py 抓取用的名称、或其他参数
- Actress: 藤浦惠 | [藤浦めぐ][305][javbus] | [藤浦めぐ][jable] | [胡桃さくら][1][2][javbus]

- 是否只获取第一页信息,首次一般用 n 抓取 全部页码信息，
- Only_Scan_First_Page: y

- 是否开启下载
- Enable_Download: y

- 控制下载作品的时间
  Filter: 2022.01.14 - 2022.03.15
  Filter: 2022.01.14 -
  Filter: - 2022.03.15
  Filter: befor 7 month
  Filter: after 7 month
  Filter: all


### config.yaml
# 控制程序执行的内容
# 视频存储位置
- SavePath_Sub: /mnt/mac/SATA_SSD_2T/000-NASSAV/000-Sub/
- SavePath_noSub: /mnt/mac/SATA_SSD_2T/000-NASSAV/000-noSub/
- SavePath_Javle_Sub: /mnt/mac/SATA_SSD_2T/000-NASSAV/000-JableSub/
- SavePath_rou.video: /mnt/mac/SATA_SSD_2T/000-NASSAV/000-Rou/

# 抓取网站用的代理
- Proxy_Catch: http://10.10.10.88:7890
# 下载用的代理
- Proxy_Download: http://10.10.10.88:7890
# 是否启用代理
- IsNeedCurlProxy: y
- IsNeedDownloadProxy: y
# 使用的下载器 (只能一个，默认 N_m3u8DL-RE )
- N_m3u8DL-RE: y
- yutoo: y
# 数据源（仅针对AV）,及调用顺序
- Jable: 1
- MissAV: 2
- NetFlav: 0

### 执行类文件 ###
### 执行具体工作



## catch.py
根据输入url，抓取网站



## source_catch.py 可有多个： source_catch_javbus.py
# 对 javbus 等资源站的抓取，实现功能:
1、获取 演员 信息：
- 姓名
- 胸围
- 腰围
- 臀围

2、获取作品信息：
- 番号
- 发行日期 (统一格式 2022.03.15)

3、后期功能：获取生成 .nfo 的其他相关信息

4、生成日志文件，
演员：藤浦惠
第1页：抓取成功｜第2页：抓取成功 ｜ 第3页：抓取失败 ｜ 重复第3页：抓取成功






## video_catch.py 可有多个：video_catch_jable.py video_catch_missav.py video_catch_rou_video.py
# 对 jable 等视频网站 的抓取，实现功能：
# 主要功能是 在下载时，提供下载链接，以及确认
根据番号，获取对应视频的：
- m3u8 
- 关键词
- 女优名称
- 头像图片链接
- 路径（针对av网站，看关键词中是否有中文字幕等关键词、routv）
- 名称 rou_video
- 头像图片链接



## download.py
# 下载文件，实现功能
- 根据 m3u8 、 是否有中文字幕 下载文件
- 确定下载文件是否成功，返回相应参数 
下载失败 
state：1 
合并失败 2
下载成功 3









## write_db.py
# 将 source_catch.py video_catch.py download.py 返回的内容，按照特定格式写入数据库文件，并排序


## main.py
# 整个功能组织的实现
运行后、输出提示、根据输入执行对应功能 ，也可以 main.py 1 ｜ 2 ｜ 3 ｜ re （重复执行知道成功退出）
1、番号信息抓取、


2、视频信息抓取





## nfo.py
从不同处获得的 actress_name 都转成中文的


### 对 jable.tv 中文视频的定期下载









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


# 安装依赖
python3 -m pip install --break-system-packages -r requirements.txt


# 更新 yaml 
python3 fetch_javbus.py

python3 up_video_messages.py 小野夕子.yaml new

# 更新所有演员 跳过已有 m3u8_url 的
python3 up_video_messages.py new

 更新所有演员 不跳过已有 m3u8_url 的
python3 up_video_messages.py all



while true; do
    python3 up_video_messages.py 胡桃さくら.yaml new
    if [ $? -eq 0 ]; then
        echo "执行成功，退出循环"
        break
    else
        echo "执行失败，重新尝试..."
        sed -i 's/source: null/skip: true/' actress/胡桃さくら.yaml
        sleep 5  # 可以加延时，避免过快重复
    fi
done


# 检查下载器
python3 rule/MissAV.py fcdss-103


# 清理进程
python3 ./tools/cleanup_n_m3u8.py


while true; do
    python3 download.py
    if [ $? -eq 0 ]; then
        echo "执行成功，退出循环"
        break
    else
        echo "执行失败，重新尝试..."
        sleep 5  # 可以加延时，避免过快重复
    fi
done



注意所有对数据库的读取和写入，都要用 显式 处理，不能依赖表里行的顺序或位置。