# ------------------ 构建 m3u8-Downloader-Go ------------------
FROM golang:1.22-alpine AS m3u8-builder
WORKDIR /build
RUN sed -i 's#https\?://dl-cdn.alpinelinux.org/alpine#https://mirrors.tuna.tsinghua.edu.cn/alpine#g' /etc/apk/repositories && \
    apk update && apk add --no-cache git
RUN git clone https://github.com/Greyh4t/m3u8-Downloader-Go.git src && \
    cd src && git checkout tags/v1.5.2 && \
    go build -o /build/m3u8-Downloader-Go

# ------------------ 下载 N_m3u8DL-RE ------------------
FROM alpine:latest AS n-builder
WORKDIR /tmp
RUN apk add --no-cache curl tar
RUN curl -L -o N_m3u8DL.tar.gz https://github.com/nilaoda/N_m3u8DL-RE/releases/download/v0.3.0-beta/N_m3u8DL-RE_v0.3.0-beta_linux-x64_20241203.tar.gz && \
    tar -xzf N_m3u8DL.tar.gz

# ------------------ 最终镜像 ------------------
FROM alpine:latest AS final
WORKDIR /app

# 安装必要基础环境(gcompat icu-libs 为 N_m3u8DL 所需)
RUN sed -i 's#https\?://dl-cdn.alpinelinux.org/alpine#https://mirrors.tuna.tsinghua.edu.cn/alpine#g' /etc/apk/repositories && \
    apk update && apk add --no-cache bash python3 py3-pip ffmpeg \ 
    gcompat icu-libs \
    libstdc++

# 复制文件，不运行任何命令
COPY requirements.txt ./
COPY --from=m3u8-builder /build/m3u8-Downloader-Go /m3u8_Downloader/m3u8-Downloader-Go
COPY --from=n-builder /tmp/N_m3u8DL-RE /m3u8_Downloader/
RUN pip3 install --no-cache-dir --break-system-packages -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 赋予执行权限
RUN chmod +x /m3u8_Downloader/*

# 默认进入 bash
ENTRYPOINT [""]

