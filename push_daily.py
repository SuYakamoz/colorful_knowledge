# -*- coding: utf-8 -*-
"""常识每日推送主脚本(纯逻辑;所有配置见 config.py)。

用法:
  python push_daily.py --dry-run          # 只打印消息,不发(本地调试用)
  python push_daily.py --dry-run --ai     # 用 AI 生成内容,只打印
  python push_daily.py                    # 真实推送(需 Server酱 SendKey)
  python push_daily.py --no-ai            # 强制只用静态知识库(不用 AI)
  python push_daily.py --no-save          # 不落盘保存(只推送)

流程:默认优先用 AI 按 config.AI_SYSTEM_PROMPT 的角色生成常识;
      AI 失败(无 key / 网络 / 解析失败)时自动回退静态知识库;
      生成结果按 config 配置落盘保存到 data/common_sense.jsonl。
"""

import argparse
import json
import os
import random
import sys
import urllib.parse
import urllib.request
from datetime import date

from config import (
    AI_API_KEY,
    AI_BASE_URL,
    AI_MODEL,
    AI_SYSTEM_PROMPT,
    AI_TEMPERATURE,
    AI_USER_PROMPT,
    DAILY_COUNT,
    DATA_FILE,
    DATA_LATEST_FILE,
    PUSH_CHANNEL,
    SAVE_ENABLED,
    SERVERCHAN_API,
    SERVERCHAN_SENDKEY,
    WECOM_AGENT_ID,
    WECOM_CARD_TYPE,
    WECOM_CARD_URL,
    WECOM_CORP_ID,
    WECOM_SECRET,
    WECOM_TOUSER,
)
from knowledge_base import CATEGORY_ICONS, KNOWLEDGE_BASE
from lunar import get_today_lunar


def pick_daily_items(count: int = DAILY_COUNT) -> list[tuple[str, str]]:
    """回退方案:从静态知识库随机选 count 个类别,每类抽 1 条。"""
    categories = random.sample(list(KNOWLEDGE_BASE.keys()), k=min(count, len(KNOWLEDGE_BASE)))
    return [(cat, random.choice(KNOWLEDGE_BASE[cat])) for cat in categories]


def generate_by_ai(count: int = DAILY_COUNT) -> list[tuple[str, str]]:
    """调用 AI(OpenAI 兼容)生成常识,返回 [(类别, 内容), ...];失败抛异常由调用方处理。"""
    if not AI_API_KEY:
        raise RuntimeError("未配置 AI API Key(见 config.py / .env 的 DEEPSEEK_API_KEY)")

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT.format(count=count)},
            {"role": "user", "content": AI_USER_PROMPT.format(count=count)},
        ],
        "temperature": AI_TEMPERATURE,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{AI_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    content = body["choices"][0]["message"]["content"]
    # 兼容 response_format 返回 JSON 对象或纯文本 JSON
    data = content if isinstance(content, list) else json.loads(content)
    items = []
    for item in data:
        cat = str(item.get("category", "常识")).strip()
        text = str(item.get("content", "")).strip()
        if text:
            items.append((cat, text))
    if not items:
        raise RuntimeError("AI 返回内容为空或格式不正确")
    return items


def icon_for(category: str) -> str:
    """根据类别名匹配图标;支持 AI 返回的简写(如「生活」匹配「生活常识」)。"""
    for key, icon in CATEGORY_ICONS.items():
        if category == key or category in key or key in category:
            return icon
    return "📌"


def build_lunar_line() -> str:
    """今日农历信息行(日期 + 干支 + 节气/节日)。"""
    info = get_today_lunar()
    parts = [info["lunar"], info["ganzhi"]]
    if info["term"]:
        parts.append(f"☀️{info['term']}")
    if info["festival"]:
        parts.append(f"🎉{info['festival']}")
    return "📅 " + " · ".join(parts)


def build_message(items: list[tuple[str, str]]) -> tuple[str, str]:
    """把选中的常识拼成 (标题, 内容)。"""
    title = "📚 今日常识 3 条"
    lines = []
    for cat, text in items:
        lines.append(f"{icon_for(cat)}【{cat}】{text}")
    return title, "\n".join(lines)


def save_items(items: list[tuple[str, str]], source: str) -> bool:
    """把本次常识落盘:①按天幂等写积累文件;②总是更新"最新一次"文件(详情页显示今日卡片)。"""
    today = date.today().isoformat()

    # ① 积累文件(按日期幂等,保证数据干净:每天最多 3 条)
    try:
        os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
        existing_dates = set()
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            existing_dates.add(json.loads(line).get("date"))
                        except json.JSONDecodeError:
                            continue
        if today in existing_dates:
            print(f"⏭️ 今天({today})已有记录,跳过落盘(幂等)")
        else:
            with open(DATA_FILE, "a", encoding="utf-8") as f:
                for cat, text in items:
                    record = {"date": today, "source": source, "category": cat, "content": text}
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"💾 已落盘 {len(items)} 条 → {DATA_FILE}")
    except OSError as e:
        print(f"⚠️ 落盘失败(不影响推送):{e}")

    # ② 最新一次推送(每次覆盖,不受幂等限制 → 详情页与卡片内容一致)
    try:
        os.makedirs(os.path.dirname(DATA_LATEST_FILE) or ".", exist_ok=True)
        latest = {"date": today, "source": source, "lunar": get_today_lunar(),
                  "items": [{"category": cat, "content": text} for cat, text in items]}
        with open(DATA_LATEST_FILE, "w", encoding="utf-8") as f:
            json.dump(latest, f, ensure_ascii=False, indent=2)
        print(f"💾 已更新最新推送 → {DATA_LATEST_FILE}")
    except OSError as e:
        print(f"⚠️ 更新 latest 失败(不影响推送):{e}")
    return True


def send_serverchan(sendkey: str, title: str, content: str) -> bool:
    """调用 Server酱 API 推送消息,成功返回 True。"""
    url = SERVERCHAN_API.format(sendkey=sendkey)
    data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
        print("Server酱响应:", body[:300])
        return '"code":0' in body


# ============ 企业微信通道(官方 API,真卡片,不经过第三方平台) ============

def get_wecom_token(corpid: str, secret: str) -> str:
    """获取企业微信 access_token。"""
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={secret}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if body.get("errcode") != 0:
        raise RuntimeError(f"获取 access_token 失败:{body}")
    return body["access_token"]


def send_wecom_message(token: str, agentid: str, payload: dict) -> bool:
    """发送企业微信应用消息,成功返回 True。"""
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    payload["agentid"] = int(agentid)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    print("企业微信响应:", body)
    return body.get("errcode") == 0


def truncate_bytes(s: str, limit: int) -> str:
    """按 UTF-8 字节数截断(企业微信限制按字节算,中文 1 字≈3 字节),避免截断半个中文。"""
    b = s.encode("utf-8")
    if len(b) <= limit:
        return s
    return b[:limit].decode("utf-8", errors="ignore")


def send_wecom(title: str, items: list[tuple[str, str]]) -> bool:
    """企业微信通道入口:按 WECOM_CARD_TYPE 发 textcard 卡片或 markdown 卡片。"""
    if not (WECOM_CORP_ID and WECOM_AGENT_ID and WECOM_SECRET):
        raise RuntimeError("未配置企业微信(WECOM_CORP_ID / WECOM_AGENT_ID / WECOM_SECRET,见 .env.example)")
    token = get_wecom_token(WECOM_CORP_ID, WECOM_SECRET)
    lines = [f"{icon_for(cat)}【{cat}】{text}" for cat, text in items]
    if WECOM_CARD_TYPE == "markdown":
        # markdown 卡片上限 2048 字节,3 条常识足够;截断保护
        md_content = f"## {title}\n" + "\n".join(f"> {line}" for line in lines)
        md_content = truncate_bytes(md_content, 2048)
        return send_wecom_message(token, WECOM_AGENT_ID,
                                  {"touser": WECOM_TOUSER, "msgtype": "markdown",
                                   "markdown": {"content": md_content}})
    # textcard 卡片:description 上限 512 字节,按字节截断(避免中文截断)
    desc = truncate_bytes("\n".join(lines), 512)
    return send_wecom_message(token, WECOM_AGENT_ID,
                              {"touser": WECOM_TOUSER, "msgtype": "textcard",
                               "textcard": {"title": title, "description": desc,
                                            "url": WECOM_CARD_URL, "btntxt": "查看详情"}})


def main() -> None:
    parser = argparse.ArgumentParser(description="常识每日推送")
    parser.add_argument("--dry-run", action="store_true", help="只打印消息,不真正推送")
    parser.add_argument("--ai", action="store_true", help="强制使用 AI 生成(失败则报错退出)")
    parser.add_argument("--no-ai", action="store_true", help="禁用 AI,只用静态知识库")
    parser.add_argument("--no-save", action="store_true", help="不落盘保存数据")
    args = parser.parse_args()

    use_ai = (not args.no_ai) and (args.ai or bool(AI_API_KEY))

    if use_ai:
        try:
            items = generate_by_ai()
            source = "ai"
        except Exception as e:
            if args.ai:  # 用户强制 AI,失败就退出
                print(f"AI 生成失败:{e}", file=sys.stderr)
                sys.exit(1)
            print(f"⚠️ AI 生成失败({e}),回退到静态知识库")
            items = pick_daily_items()
            source = "fallback"
    else:
        items = pick_daily_items()
        source = "fallback"

    title, content = build_message(items)

    print("=" * 40)
    print(f"来源:{'🤖 AI 生成' if source == 'ai' else '📚 静态知识库'}")
    print("标题:", title)
    print("-" * 40)
    print(content)
    print("=" * 40)

    if SAVE_ENABLED and not args.no_save:
        save_items(items, source)

    if args.dry_run:
        print("[dry-run] 未发送,以上为将推送的内容")
        return

    if PUSH_CHANNEL == "wecom":
        try:
            ok = send_wecom(title, items)
        except Exception as e:
            print(f"企业微信推送失败:{e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0 if ok else 1)

    # 默认 Server酱
    if not SERVERCHAN_SENDKEY:
        print("错误:未配置 Server酱 SendKey(见 config.py / .env 的 SERVERCHAN_SENDKEY)", file=sys.stderr)
        sys.exit(1)

    ok = send_serverchan(SERVERCHAN_SENDKEY, title, content)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()