# 📚 常识每日推送(微信)

每天定时往你的微信推送 **3 条不同类别**的常识(生活 / 科学 / 历史 / 健康 / 冷知识随机三样)。

```
🤖 DeepSeek 每天按「常识编辑」角色生成 3 条(失败自动回退知识库)
   ↓ 每天 08:00 GitHub Actions 自动触发
Python 脚本整理成一条消息
   ↓ Server酱 API
你的微信收到「📚 今日常识 3 条」
```

## 文件结构

| 文件 | 作用 |
|------|------|
| `config.py` | **⚙️ 所有配置集中在这里**(改这里,不用翻代码) |
| `knowledge_base.py` | **兜底**知识库(7 类 × 12 条;AI 不可用时用,可自行扩充) |
| `push_daily.py` | 主脚本(纯逻辑,配置都从 config.py 读) |
| `.github/workflows/daily_push.yml` | GitHub Actions 定时工作流(每天 08:00) |
| `data/common_sense.jsonl` | **每天积累的常识数据**(自动生成,以后做网站的数据源) |
| `.env`(自己创建) | 本地密钥配置(已 gitignore,不会误传 GitHub) |

## 🚀 上手三步(都需要你本人操作,约 10 分钟)

### 第 1 步:注册 Server酱,拿到 SendKey

1. 打开 https://sct.ftqq.com ,用 GitHub 账号登录(没有就注册一个);
2. 登录后点击「SendKey」菜单,复制你的 SendKey(一串字符);
3. 按页面提示**微信扫码关注「方糖」服务号**——这是接收推送的入口。

> 免费额度:每天 5 条,完全够用。

### 第 2 步:建 GitHub 仓库并上传本项目

1. 打开 https://github.com/new ,仓库名随便(如 `common-sense-push`),选 Public 或 Private 都行,创建;
2. 把本文件夹里的这些文件上传进仓库(网页上点 Add file → Upload files,或 git 推送):
   - `config.py`
   - `knowledge_base.py`
   - `push_daily.py`
   - `.gitignore`
   - `.github/workflows/daily_push.yml`(注意保留 `.github/workflows` 目录结构)
   - ⚠️ **不要**上传 `.env`(本地密钥文件,已被 .gitignore 忽略)
3. 到仓库页面 **Settings → Secrets and variables → Actions → New repository secret**,依次添加 Secret:
   - `SERVERCHAN_SENDKEY` = 第 1 步复制的 SendKey(必配);
   - `DEEPSEEK_API_KEY` = 你的 DeepSeek API Key(必配,platform.deepseek.com 申请);
   - `DEEPSEEK_MODEL` = 模型名,**可选**(不配默认 `deepseek-chat`);
   - `DEEPSEEK_BASE_URL` = 接口地址,**可选**(不配默认 `https://api.deepseek.com`)。
   - 各自保存。

### 第 3 步:手动测试,然后等定时

1. 打开仓库的 **Actions** 页签;
2. 左侧选 **Daily Common Sense Push** → 右侧 **Run workflow** → 绿色按钮;
3. 等 1-2 分钟,跑完看绿色 ✅,你的微信就会收到第一条常识;
4. 确认收到后就不用管了——之后**每天北京时间 08:00** 自动推送。

> ⏰ 说明:GitHub Actions 的定时用的是 UTC 时间,`0 0 * * *` = 北京 08:00。偶尔可能有几分钟延迟,属正常。

## 🛠 本地调试(可选)

在装有 Python 3.10+ 的电脑上:

```bash
python push_daily.py --dry-run     # 只打印消息,不发送
set SERVERCHAN_SENDKEY=你的SendKey # Windows
python push_daily.py               # 真实发送到微信
```

## ✏️ 自定义

| 想改什么 | 改哪里 |
|---------|--------|
| 推送时间 | `.github/workflows/daily_push.yml` 里的 `cron`(UTC 时间) |
| 每天几条(默认 3) | `push_daily.py` 里 `DAILY_COUNT = 3` |
| 常识内容 | 直接在 `knowledge_base.py` 的列表里加/改句子 |
| 加新类别 | 在 `KNOWLEDGE_BASE` 加一个列表 + 在 `CATEGORY_ICONS` 加图标即可 |

## 🤖 AI 生成模式(默认开启)

- **工作原理**:每天 GitHub Actions 触发时,`push_daily.py` 先调用 DeepSeek,按 `AI_SYSTEM_PROMPT` 里设定的「博学常识编辑」角色,现场生成 3 条不同领域的常识(JSON 格式);
- **自动兜底**:AI 失败(网络/没 key/解析错误)时,自动回退到 `knowledge_base.py` 随机抽 3 条,保证每天都有推送、不会断更;
- **改角色/要求**:编辑 `push_daily.py` 里的 `AI_SYSTEM_PROMPT` 字符串即可(比如改成"用幽默风格"、"必须包含一个数据点"等);
- **本地试 AI 效果**:`python push_daily.py --dry-run --ai`(需在环境变量配好 `DEEPSEEK_API_KEY`);
- **想完全不用 AI**:`python push_daily.py --no-ai`。

> 💰 费用:每天一次 DeepSeek 调用,约几百 token,DeepSeek 充值几块钱能用很久。

> 📌 **注意区分**:你桌面 `Agent` 教学项目里也有一个 `.env`(那是 LangChain 教学用的,含 `DEEPSEEK_MODEL_URL` 等变量);本推送项目用的是**自己文件夹里**的 `.env`(键名是 `DEEPSEEK_API_KEY`/`SERVERCHAN_SENDKEY`),两者互不影响,别改错文件。

## 🔄 自定义 AI 模型(换任意 OpenAI 兼容模型)

脚本完全通过环境变量控制模型,不换代码就能换模型:

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `DEEPSEEK_API_KEY` | 无(必填) | API 密钥 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名,如 `qwen-plus`(通义)/ `glm-4`(智谱)/ `gpt-4o-mini`(OpenAI) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | 接口地址,换厂商时改成对应 base_url(注意不要带 `/v1` 或带不带取决于厂商) |

在 GitHub 上改对应 Secret 即可;本地运行则设同名环境变量。

## 📊 数据积累(为以后做网站)

- 每天生成(或回退)的常识会**自动追加**到仓库 `data/common_sense.jsonl`,并由 workflow 自动提交回仓库;
- 每行一条 JSON,格式(方便以后导入数据库 / 做网站):

```json
{"date": "2026-08-03", "source": "ai", "category": "科学", "content": "光速约为每秒 30 万公里……"}
```

- 字段说明:`date` 日期(按天幂等,同一天不会重复存)、`source` 来源(`ai`=AI 生成 / `fallback`=知识库回退)、`category` 类别、`content` 内容;
- 想关闭落盘:运行加 `--no-save`(或在 workflow 的 run 那行改为 `python push_daily.py --no-save`);
- 积累一段时间后,把 `data/common_sense.jsonl` 导入数据库/生成静态站,就是你的常识网站数据源。

## ⚙️ 配置文件 config.py(最重要)

**所有可调项都集中在 `config.py`,改完不用动其他文件**:

| 配置项 | 默认值 | 改成什么 |
|--------|--------|---------|
| `DAILY_COUNT` | `3` | 每天几条常识(3~5) |
| `AI_MODEL` | `deepseek-chat` | 想换模型改这里(如 `qwen-plus`/`glm-4`/`gpt-4o-mini`) |
| `AI_BASE_URL` | `https://api.deepseek.com` | 换厂商时改对应接口地址 |
| `AI_TEMPERATURE` | `0.9` | 生成随机性(0~1) |
| `AI_SYSTEM_PROMPT` | 16 类领域池 | **AI 角色设定**:领域池、风格、字数要求都在这里 |
| `SAVE_ENABLED` | `True` | 是否落盘保存数据 |
| `DATA_FILE` | `data/common_sense.jsonl` | 数据保存路径 |
| `SERVERCHAN_API` | Server酱接口 | 换推送通道时改 |

**密钥**不写在 config.py 里,放 `.env`(本地)或 GitHub Secret(云端):
- **本地**:把项目里的 `.env.example` **复制一份改名为 `.env`**,填入你的密钥即可(文件里每项都有申请说明);
  - `DEEPSEEK_API_KEY` = DeepSeek key(platform.deepseek.com 申请);
  - `SERVERCHAN_SENDKEY` = Server酱 SendKey(sct.ftqq.com 注册,微信扫码关注后获取);
- **云端**:不用复制 `.env`,直接在 GitHub 仓库配同名 Secret(`SERVERCHAN_SENDKEY`、`DEEPSEEK_API_KEY` 必配,`DEEPSEEK_MODEL`、`DEEPSEEK_BASE_URL` 可选),自动优先生效。

## ⚠️ 注意

- SendKey 是密钥,**不要**提交到仓库代码里,只在 GitHub Secret 里配置;
- 项目只在 GitHub Actions 云端运行,本地电脑不需要开机;
- 知识库初始 60 条,每天 3 条可抽约 20 天不重样(随机);想长期用建议逐步扩充到几百条。