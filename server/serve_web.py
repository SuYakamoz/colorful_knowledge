# -*- coding: utf-8 -*-
"""多彩知识宝盒 - 白名单静态服务(安全版详情页服务器)。

只允许访问网页所需的几个文件(index.html / data / assets/logo.png),
其余一切(如 .env、config.py、push_daily.py)一律 403,防止密钥泄露。

用法(服务器上,项目根目录执行):
  nohup python3 server/serve_web.py 8001 > /dev/null 2>&1 &
"""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根

# 白名单:URL 路径 → 项目根下的文件(只放网页真正需要的东西)
ALLOWED = {
    "/": "index.html",
    "/index.html": "index.html",
    "/data/common_sense.jsonl": "data/common_sense.jsonl",
    "/assets/logo.png": "assets/logo.png",
}


class WhitelistHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]  # 去掉企业微信附加参数
        if path in ALLOWED:
            self.path = "/" + ALLOWED[path]
            return super().do_GET()
        # 手动构造 403(避免 send_error 在 keep-alive 下的兼容问题)
        body = "Forbidden: 该文件不允许访问".encode("utf-8")
        self.send_response(403)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    print(f"白名单服务已启动:http://0.0.0.0:{port}(仅网页所需文件可访问,密钥已屏蔽)")
    HTTPServer(("0.0.0.0", port), WhitelistHandler).serve_forever()