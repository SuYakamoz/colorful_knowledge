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
    SAVE_ENABLED,
    SERVERCHAN_API,
    SERVERCHAN_SENDKEY,
)
from knowledge_base import CATEGORY_ICONS, KNOWLEDGE_BASE


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


def build_message(items: list[tuple[str, str]]) -> tuple[str, str]:
    """把选中的常识拼成 (标题, 内容)。"""
    title = "📚 今日常识 3 条"
    lines = []
    for cat, text in items:
        lines.append(f"{icon_for(cat)}【{cat}】{text}")
    return title, "\n\n".join(lines)


def save_items(items: list[tuple[str, str]], source: str) -> bool:
    """把本次常识追加保存到 DATA_FILE(按日期幂等),成功返回 True。

    每行一个 JSON 对象:{"date": "...", "source": "ai|fallback", "category": ..., "content": ...}
    方便以后导入数据库 / 做网站。
    """
    try:
        os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
        today = date.today().isoformat()
        # 读取已有行,当天已存过则跳过(幂等,避免重复)
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
            return True
        with open(DATA_FILE, "a", encoding="utf-8") as f:
            for cat, text in items:
                record = {"date": today, "source": source, "category": cat, "content": text}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"💾 已落盘 {len(items)} 条 → {DATA_FILE}")
        return True
    except OSError as e:
        print(f"⚠️ 落盘失败(不影响推送):{e}")
        return False


def send_serverchan(sendkey: str, title: str, content: str) -> bool:
    """调用 Server酱 API 推送消息,成功返回 True。"""
    url = SERVERCHAN_API.format(sendkey=sendkey)
    data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
        print("Server酱响应:", body[:300])
        return '"code":0' in body


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

    if not SERVERCHAN_SENDKEY:
        print("错误:未配置 Server酱 SendKey(见 config.py / .env 的 SERVERCHAN_SENDKEY)", file=sys.stderr)
        sys.exit(1)

    ok = send_serverchan(SERVERCHAN_SENDKEY, title, content)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()