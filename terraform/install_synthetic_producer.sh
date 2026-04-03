#!/bin/bash
# Amazon Linux 2023 - Instalar y ejecutar Synthetic Producer
sudo dnf update -y
sudo dnf install -y python3 python3-pip git
pip3 install boto3

APP_DIR="/home/ec2-user/async"
REPO_URL="${repo_url}"

if [ ! -d "$APP_DIR" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR" || exit 1

API_IP=$(python3 - <<'PY'
from get_parameter import get_ssm_parameter
print(get_ssm_parameter("/message-queue/dev/api/public_ip", "localhost"))
PY
)

pip3 install -r requirements.txt

pkill -f "python3 synthetic_producer.py" >/dev/null 2>&1 || true
nohup env API_BASE_URL="http://$${API_IP}:8000" PRODUCER_INTERVAL_SECONDS="10" \
  python3 synthetic_producer.py > /home/ec2-user/synthetic_producer.log 2>&1 &
