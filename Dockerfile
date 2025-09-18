FROM python:3.12-slim

# 设置中文环境
ENV LANG=zh_CN.UTF-8 \
    LC_ALL=zh_CN.UTF-8 \
    PYTHONUNBUFFERED=1

# 安装依赖
RUN apt-get update && apt-get install -y \
    bash wget tar ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 创建普通用户
RUN groupadd -g 1000 appuser && useradd -m -u 1000 -g appuser appuser

# 在 root 下创建工作目录并赋权
RUN mkdir -p /home/appuser/app /m3u8_Downloader /DRIVE && \
    chown -R appuser:appuser /home/appuser/app /m3u8_Downloader /DRIVE

USER appuser
WORKDIR /home/appuser/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 下载并解压 m3u8-Downloader-Go
RUN wget -qO- https://github.com/Greyh4t/m3u8-Downloader-Go/releases/download/v1.5.2/m3u8-Downloader-Go_linux_amd64.tgz \
    | tar -xz -C /m3u8_Downloader

# CMD ["bash", "/home/appuser/app/main.sh"]
CMD ["bash"]

