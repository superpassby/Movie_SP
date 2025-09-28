# ------------------ 构建阶段 ------------------
FROM python:3.11-slim AS builder

WORKDIR /tmp

# 使用清华源，安装必要工具，下载 N_m3u8DL-RE 和 m3u8-Downloader-Go
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt update && \
    apt install -y --no-install-recommends curl tar && \
    curl -L -o N_m3u8DL.tar.gz https://github.com/nilaoda/N_m3u8DL-RE/releases/download/v0.3.0-beta/N_m3u8DL-RE_v0.3.0-beta_linux-x64_20241203.tar.gz && \
    tar -xzf N_m3u8DL.tar.gz && \
    curl -L -o m3u8-Downloader-Go.tgz https://github.com/Greyh4t/m3u8-Downloader-Go/releases/download/v1.5.2/m3u8-Downloader-Go_linux_amd64.tgz && \
    tar -xzf m3u8-Downloader-Go.tgz

# ------------------ 最终镜像 ------------------
FROM python:3.11-slim AS final

WORKDIR /app

COPY --from=builder /tmp/N_m3u8DL-RE /usr/local/bin/
COPY --from=builder /tmp/m3u8-Downloader-Go /usr/local/bin/

# 安装系统依赖，创建非 root 用户和必要目录，并赋予权限
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt update && \
    apt install -y --no-install-recommends bash ffmpeg python3-pip libicu-dev sudo \
    libnss3 libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 libxcomposite1 libxdamage1 && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -s /bin/bash appuser && \
    mkdir -p /app && chmod -R 777 /app && \
    chmod +x /usr/local/bin/N_m3u8DL-RE /usr/local/bin/m3u8-Downloader-Go && \ 
    # 给 appuser 添加 sudo 权限
    usermod -aG sudo appuser && \
    # 配置 sudo 无密码
    echo "appuser ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/appuser

# 切换到非 root 用户
USER appuser

ENV PATH="/home/appuser/.local/bin:${PATH}"

COPY requirements.txt ./

# 安装 Python 包并赋予可执行权限
RUN python3 -m pip install --no-cache-dir --upgrade pip -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple && \
    pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple && \
    pip install --no-cache-dir -r requirements.txt && \
    python3 -m playwright install chromium

# 默认进入 bash
# ENTRYPOINT ["/bin/bash"]
ENTRYPOINT [""]
