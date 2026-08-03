#!/bin/bash
# ============================================================
# 多彩知识宝盒 - 服务器端一键部署(对接 GitHub 自动同步)
# 功能:接入 GitHub 仓库 → 配置 .env → 测试推送 → 每天 08:00 定时推送
# 之后改代码:本地改 → git push 到 GitHub → 服务器每天自动拉取新版
# 用法:执行 bash deploy.sh(重复运行安全,可用来手动同步代码)
# ============================================================
set -e
cd "$(dirname "$0")"

echo "==== 1/5 接入 GitHub 仓库 ===="
if [ ! -d .git ]; then
    echo "本目录还不是 git 仓库,开始接入 GitHub..."
    git init -q
    git remote add origin https://github.com/SuYakamoz/colorful-_knowledge.git
    git fetch -q origin
    git checkout -q -t origin/main 2>/dev/null || git checkout -q -b main origin/main
    echo "已接入 GitHub(仓库文件已同步;本地 .env 不会被覆盖)"
else
    echo "已是 git 仓库,拉取最新代码..."
    git pull -q origin main || echo "(拉取失败,继续用本地版本)"
fi
# 数据文件本地化:data/ 由服务器每天写入,不同步回仓库,避免 pull 冲突
git update-index --skip-worktree data/common_sense.jsonl 2>/dev/null || true

echo "==== 2/5 检查环境 ===="
if ! python3 -c "import urllib.request" 2>/dev/null; then
    echo "缺少 Python3,请先: sudo apt install -y python3"; exit 1
fi
echo "Python3 OK(推送脚本只用标准库,无需 pip 安装任何包)"

echo "==== 3/5 检查 .env ===="
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "已生成 .env,请先编辑填入密钥后再运行一次本脚本:"
    echo "  sudo nano .env"
    echo "必填:DEEPSEEK_API_KEY=你的DeepSeek key"
    echo "      PUSH_CHANNEL=wecom"
    echo "      WECOM_CORP_ID=ww176205ca199bdbb8"
    echo "      WECOM_AGENT_ID=1000002"
    echo "      WECOM_SECRET=你的Secret"
    echo "可选:SERVERCHAN_SENDKEY(想保留 Server酱 通道时填)"
    exit 1
fi
echo ".env 已存在"

echo "==== 4/5 测试推送一次(微信应收到卡片)===="
python3 push_daily.py

echo "==== 5/5 设置时区与定时任务 ===="
sudo timedatectl set-timezone Asia/Shanghai 2>/dev/null && echo "时区已设为北京时间" || echo "提示:无法自动设时区,请确认服务器时区为北京时间(否则定时按服务器本地时间)"
SCRIPT_DIR="$PWD"
(crontab -l 2>/dev/null | grep -v "colorful-knowledge"; echo "0 8 * * * cd $SCRIPT_DIR && git pull -q origin main && /usr/bin/python3 $SCRIPT_DIR/push_daily.py >> $SCRIPT_DIR/push.log 2>&1 # colorful-knowledge") | crontab -
echo "定时任务已配置:每天 08:00 先自动拉 GitHub 最新代码,再推送"

echo ""
echo "==== 部署完成 ===="
echo "· 手动同步+推送:  cd $SCRIPT_DIR && bash deploy.sh"
echo "· 查看定时任务:    crontab -l"
echo "· 查看推送日志:    tail -f $SCRIPT_DIR/push.log"