state：
- download 已下载(已下载的可能没中文字幕，还是要获取m3u8)
- wait 等待下载 （下载时选择_下载时只看这一个指标）
- no_res 无资源（下载时跳过），获取 m3u8 时不跳过，获取m3u8 后，改为 wait （在 info——up 中完成）
- skip 获取 m3u8 下载 都跳过
- out_number 获取 m3u8 下载 都跳过



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




