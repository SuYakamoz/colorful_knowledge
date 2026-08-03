#!/bin/bash
# ============================================================
# 多彩知识宝盒 - 服务器端一键部署
# 功能:配置 .env → 测试推送一次 → 设置每天 08:00 定时推送(企业微信卡片)
# 用法:把本脚本与 push_daily.py、config.py、knowledge_base.py、.env.example 放同一目录,
#       执行:bash deploy.sh
# ============================================================
set -e
cd "$(dirname "$0")"

echo "==== 1/4 检查环境 ===="
if ! python3 -c "import urllib.request" 2>/dev/null; then
    echo "缺少 Python3,请先: sudo apt install -y python3"; exit 1
fi
echo "Python3 OK(推送脚本只用标准库,无需 pip 安装任何包)"

echo "==== 2/4 检查 .env ===="
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

echo "==== 3/4 测试推送一次(微信应收到卡片)===="
python3 push_daily.py

echo "==== 4/4 设置时区与定时任务 ===="
sudo timedatectl set-timezone Asia/Shanghai 2>/dev/null && echo "时区已设为北京时间" || echo "提示:无法自动设时区,请确认服务器时区为北京时间(否则定时按服务器本地时间)"
SCRIPT_DIR="$PWD"
(crontab -l 2>/dev/null | grep -v "colorful-knowledge"; echo "0 8 * * * cd $SCRIPT_DIR && /usr/bin/python3 $SCRIPT_DIR/push_daily.py >> $SCRIPT_DIR/push.log 2>&1 # colorful-knowledge") | crontab -
echo "定时任务已配置:每天 08:00 自动推送"

echo ""
echo "==== 部署完成 ===="
echo "· 手动推送:      cd $SCRIPT_DIR && python3 push_daily.py"
echo "· 查看定时任务:  crontab -l"
echo "· 查看推送日志:  tail -f $SCRIPT_DIR/push.log"