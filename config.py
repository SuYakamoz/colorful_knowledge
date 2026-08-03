# -*- coding: utf-8 -*-
"""集中配置文件:所有可调项都在这,改这里即可,不用翻代码。

支持本地 .env 文件(与本文件同目录,格式 KEY=值,每行一个):
  DEEPSEEK_API_KEY=你的key
  SERVERCHAN_SENDKEY=你的sendkey
本地运行时自动读取;GitHub Actions 上改用仓库 Secret(同名),互不影响。
"""

import os

# ============================================================
# 加载逻辑(一般不用改):.env 加载 + 环境变量读取
# ============================================================

def load_dotenv() -> None:
    """极简 .env 加载器:读取项目根目录 .env,注入 os.environ(不覆盖已存在的变量)。"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # 支持行内注释:值里 # 之后的内容忽略(如 KEY=xxx # 注释)
            if "#" in value:
                value = value.split("#", 1)[0].strip()
            if key and key not in os.environ:
                os.environ[key] = value


def get_secret(env_name: str, default: str = "") -> str:
    """读取环境变量(含 .env),空值回退 default。"""
    return (os.environ.get(env_name) or default).strip()


load_dotenv()  # 模块导入时自动加载 .env

# ============================================================
# ① 推送设置(改这里)
# ============================================================
DAILY_COUNT = 3                      # 每天推送几条常识(推荐 3~5)

# ============================================================
# ② AI 生成设置(改这里)
# ============================================================
# 想换模型:改 DEEPSEEK_MODEL / DEEPSEEK_BASE_URL(.env 或 GitHub Secret 同名变量优先)
# 例:通义千问  DEEPSEEK_MODEL="qwen-plus"         DEEPSEEK_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
#     智谱GLM  DEEPSEEK_MODEL="glm-4"              DEEPSEEK_BASE_URL="https://open.bigmodel.cn/api/paas/v4"
AI_MODEL = get_secret("DEEPSEEK_MODEL", "deepseek-chat")           # 模型名(默认 DeepSeek)
AI_BASE_URL = get_secret("DEEPSEEK_BASE_URL", "https://api.deepseek.com")   # 接口地址(不要带末尾斜杠)
AI_TEMPERATURE = 0.9                 # 生成随机性:0~1,越大越发散

# API Key 从环境变量 / .env 读取(环境变量名,别直接写 key 在这里!)
AI_API_KEY_ENV = "DEEPSEEK_API_KEY"

# AI 角色设定:按你喜好改这段话即可(领域池、风格、字数要求)
AI_SYSTEM_PROMPT = """你是一位博学的「每日常识编辑」。请每天为用户输出 {count} 条不同领域的常识,
领域必须各不相同,从以下 16 个领域池中挑选(尽量轮换,不要连续几天重复同一组合):
金融理财、职场发展、生活实用、健康养生、科学知识、历史人文、法律常识、
科技数码、心理社交、安全应急、商业经济、教育成长、地理旅行、运动健身、文化艺术、冷知识。
要求:
1. 每条常识要通俗易懂、有趣、有实际价值,60~100 字;
2. 输出严格为 JSON 数组,格式:[{{"category": "领域名", "content": "常识内容"}}, ...];
3. 不要输出 JSON 以外的任何文字。"""

AI_USER_PROMPT = "请生成今天的 {count} 条常识。"

# ============================================================
# ③ 数据积累设置(改这里)
# ============================================================
SAVE_ENABLED = True                  # 是否把每天的常识落盘保存(做网站的数据源)
DATA_FILE = "data/common_sense.jsonl"   # 保存路径(相对本项目根目录)

# ============================================================
# ④ 推送通道设置(改这里)
# ============================================================
# 推送通道选择:"serverchan"(Server酱微信推送)或 "wecom"(企业微信自建应用,官方 API 真卡片)
PUSH_CHANNEL = get_secret("PUSH_CHANNEL", "serverchan")

# ---- Server酱通道(需 SERVERCHAN_SENDKEY)----
SERVERCHAN_API = "https://sctapi.ftqq.com/{sendkey}.send"   # Server酱接口
SERVERCHAN_SENDKEY_ENV = "SERVERCHAN_SENDKEY"               # SendKey 的环境变量名

# ---- 企业微信通道(官方 API,真卡片,不经过第三方平台)----
# 注册:qy.weixin.qq.com 免费注册 → 应用管理 → 创建自建应用 → 拿 CorpID / AgentId / Secret
WECOM_CORP_ID = get_secret("WECOM_CORP_ID")                 # 企业 ID
WECOM_AGENT_ID = get_secret("WECOM_AGENT_ID")               # 自建应用 AgentId
WECOM_SECRET = get_secret("WECOM_SECRET")                   # 自建应用 Secret
WECOM_TOUSER = get_secret("WECOM_TOUSER", "@all")           # 接收人(默认全员;单人填你的企业微信 userid)
WECOM_CARD_TYPE = get_secret("WECOM_CARD_TYPE", "textcard") # 卡片类型:"textcard"(文本卡片)或 "markdown"
WECOM_CARD_URL = get_secret("WECOM_CARD_URL", "https://github.com/SuYakamoz/colorful_knowledge")  # textcard 点击跳转链接

# ============================================================
# 生效值(一般不用改)
# ============================================================
AI_API_KEY = get_secret(AI_API_KEY_ENV)                      # 实际生效的 AI key
SERVERCHAN_SENDKEY = get_secret(SERVERCHAN_SENDKEY_ENV)      # 实际生效的 SendKey