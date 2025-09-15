import re
from bs4 import BeautifulSoup

def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    m3u8_urls = []
    script_tags = soup.find_all("script")

    for s in script_tags:
        content = s.string or s.get_text() or ""
        if not content:
            continue

        # 优先解析 eval 混淆 JS
        if "eval(function(p,a,c,k,e,d)" in content:
            decoded_urls = decode_eval_js(content)
            if decoded_urls:
                m3u8_urls.append(decoded_urls)
                continue  # 找到后继续检查其他 script，可能有多个 URL

        # 如果不是 eval，直接找普通 m3u8
        m = re.search(r"https?://[^\s'\"]+\.m3u8", content)
        if m:
            m3u8_urls.append(m.group(0).strip())

    # 打印结果
    if m3u8_urls:
        for i, url in enumerate(m3u8_urls, 1):
            print(f"m3u8_url_{i}: {url}")
    else:
        print("未找到 m3u8 链接")

    return m3u8_urls

def decode_eval_js(js_code: str) -> str:
    """
    解包典型的 eval(function(p,a,c,k,e,d){...})(payload,a,c,k.split('|'),...)
    返回解包后找到的最后一个 .m3u8 URL（若没有则返回 None）。
    """
    # 匹配 eval 混淆 JS 的 payload, a, c, k
    m = re.search(
        r"eval\(function\(p,a,c,k,e,d\).*?\(\s*(['\"])(.+?)\1\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(['\"])(.+?)\5\.split\('\|'\)",
        js_code, re.S
    )
    if not m:
        return None

    payload = m.group(2)
    a = int(m.group(3))
    c = int(m.group(4))
    k = m.group(6).split("|")

    # 按 JS 规则替换 payload 中的数字为对应字符串
    for i in range(c-1, -1, -1):
        if i < len(k) and k[i]:
            pattern = r"\b{}\b".format(base36encode(i))
            payload = re.sub(pattern, k[i], payload)

    # 提取 .m3u8 链接
    urls = re.findall(r"https?://[^\s'\";]+\.m3u8", payload)
    return urls  # 返回所有 URLs，而不是最后一个

def base36encode(number: int) -> str:
    """把 10 进制数字转成 base36（js 中 c.toString(36) 的逆过程）"""
    if number < 0:
        raise ValueError("必须是非负整数")
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    res = ""
    while number:
        number, i = divmod(number, 36)
        res = digits[i] + res
    return res or "0"

# 测试用例
if __name__ == "__main__":
    html_content = """
    <script>
        window.dataLayer.push({
            event: 'recommendationVisit',
            recommendation: {
                scenario: window.scenario,
            },
        })

        document.addEventListener('DOMContentLoaded', () => {
            let source
            let isPreviewing = false

            eval(function(p,a,c,k,e,d){e=function(c){return c.toString(36)};if(!''.replace(/^/,String)){while(c--){d[c.toString(a)]=k[c]||c.toString(a)}k=[function(e){return d[e]}];e=function(){return'\\w+'};c=1};while(c--){if(k[c]){p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c])}}return p}('f=\'8://7.6/5-4-3-2-1/e.0\';d=\'8://7.6/5-4-3-2-1/c/9.0\';b=\'8://7.6/5-4-3-2-1/a/9.0\';',16,16,'m3u8|41a9c2dbc030|b70a|4f11|4b0a|12fe305e|com|surrit|https|video|1280x720|source1280|842x480|source842|playlist|source'.split('|'),0,{}))
            
            const video = document.querySelector('video.player')

            const initialPlayerEvent = 
    </script>
    """
    parse_page(html_content)