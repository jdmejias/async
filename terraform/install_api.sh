#!/bin/bash
# Amazon Linux 2023 - Instalar y ejecutar API
sudo dnf update -y
sudo dnf install -y git python3 python3-pip
pip3 install boto3

APP_DIR="/home/ec2-user/async"
REPO_URL="${repo_url}"

if [ ! -d "$APP_DIR" ]; then
	git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR" || exit 1

RABBIT_IP=$(python3 - <<'PY'
from get_parameter import get_ssm_parameter
print(get_ssm_parameter("/message-queue/dev/rabbitmq/public_ip", "localhost"))
PY
)

POSTGRES_IP=$(python3 - <<'PY'
from get_parameter import get_ssm_parameter
print(get_ssm_parameter("/message-queue/dev/postgres/public_ip", "localhost"))
PY
)

cat > .env.aws <<EOF
DATABASE_URL=postgresql://appuser:password@$${POSTGRES_IP}:5432/appdb
RABBIT_URL=amqp://guest:guest@$${RABBIT_IP}:5672/
EXCHANGE=tasks.exchange
QUEUE=tasks.queue
EOF

pip3 install -r requirements.txt

pkill -f "uvicorn api:app" >/dev/null 2>&1 || true
nohup env $(cat .env.aws | xargs) python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 \
	> /home/ec2-user/api.log 2>&1 &

