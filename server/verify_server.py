# -*- coding: utf-8 -*-
"""企业微信「接收消息服务器 URL」验证服务(极简)。

作用:让企业微信后台「接收消息」的 URL 验证通过(URL 校验 / 明文模式),之后才能配置「企业可信IP」。
我们不需要真正接收消息,这个服务只负责:①验证 URL 所有权(GET 校验);②其余请求返回 success。

启动(在服务器上):
  1) pip install cryptography
  2) 企业微信后台 应用详情→接收消息→ 生成 Token 和 EncodingAESKey,复制
  3) 启动:TOKEN=你的Token AES_KEY=你的EncodingAESKey python3 verify_server.py
  4) 后台「接收消息服务器URL」填:http://<服务器公网IP>:8000/wecom → 保存(自动触发验证)
  5) 验证通过后:配「企业可信IP」= 服务器公网IP(或 0.0.0.0/0)
"""

import base64
import hashlib
import os
import struct
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

TOKEN = os.environ.get("TOKEN", "")
AES_KEY = os.environ.get("AES_KEY", "")  # 43 位 EncodingAESKey
PORT = int(os.environ.get("PORT", "8000"))


def verify_signature(token, timestamp, nonce, echostr, msg_signature) -> bool:
    """sha1 签名校验:sort([token, timestamp, nonce, echostr]) 拼接后 sha1。"""
    s = "".join(sorted([token, timestamp, nonce, echostr]))
    return hashlib.sha1(s.encode("utf-8")).hexdigest() == msg_signature


def decrypt_echostr(echostr: str, aes_key: str) -> str:
    """AES-CBC 解密 echostr,返回明文消息。"""
    key = base64.b64decode(aes_key + "=")  # 43 位 + "=" = 44 → 32 字节
    iv = key[:16]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    plain = decryptor.update(base64.b64decode(echostr)) + decryptor.finalize()
    # 去 PKCS7 填充
    pad_len = plain[-1]
    plain = plain[:-pad_len]
    # 结构:random(16) + msg_len(4 大端) + msg + receiveid
    msg_len = struct.unpack(">I", plain[16:20])[0]
    return plain[20:20 + msg_len].decode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 企业微信 URL 验证:GET 带 msg_signature/timestamp/nonce/echostr
        q = self.path.split("?", 1)
        if len(q) < 2:
            self._ok("success")
            return
        params = dict(
            (k, urllib.parse.unquote_plus(v))
            for k, v in (p.split("=", 1) for p in q[1].split("&") if "=" in p)
        )
        msg_signature = params.get("msg_signature", "")
        timestamp = params.get("timestamp", "")
        nonce = params.get("nonce", "")
        echostr = params.get("echostr", "")  # 已做 URL 解码,恢复原始 base64 字符
        print(f"[verify] echostr 前 30 字符:{echostr[:30]}")
        if not (TOKEN and AES_KEY):
            self._ok("error: 未配置 TOKEN/AES_KEY")
            return
        if not verify_signature(TOKEN, timestamp, nonce, echostr, msg_signature):
            print(f"[verify] 签名校验失败 timestamp={timestamp} nonce={nonce}")
            self._ok("error: 签名校验失败")
            return
        try:
            text = decrypt_echostr(echostr, AES_KEY)
            print(f"[verify] 解密成功,返回明文长度 {len(text)}")
            self._ok(text)  # 返回明文即验证通过
        except Exception as e:
            print(f"[verify] 解密失败:{e}")
            self._ok(f"error: {e}")

    def do_POST(self):
        # 消息回调(我们不需要,固定回 success)
        self._ok("success")

    def _ok(self, text):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


if __name__ == "__main__":
    if not (TOKEN and AES_KEY):
        print("请先设置环境变量 TOKEN 和 AES_KEY(企业微信后台 接收消息 里生成)")
        raise SystemExit(1)
    print(f"验证服务已启动:http://0.0.0.0:{PORT}/wecom")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()