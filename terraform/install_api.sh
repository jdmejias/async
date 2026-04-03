#!/bin/bash
# Amazon Linux 2023 - Instalar y ejecutar API
sudo dnf update -y
sudo dnf install -y git python3 python3-pip

APP_DIR="/home/ec2-user/async"
REPO_URL="${repo_url}"
RABBITMQ_IP="${rabbitmq_ip}"
POSTGRES_IP="${postgres_ip}"

if [ ! -d "$APP_DIR" ]; then
	git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR" || exit 1

cat > .env.aws <<EOF
DATABASE_URL=postgresql://appuser:password@$POSTGRES_IP:5432/appdb
RABBIT_URL=amqp://guest:guest@$RABBITMQ_IP:5672/
EXCHANGE=tasks.exchange
QUEUE=tasks.queue
EOF

pip3 install -r requirements.txt

pkill -f "uvicorn api:app" >/dev/null 2>&1 || true
nohup env $(cat .env.aws | xargs) python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 \
	> /home/ec2-user/api.log 2>&1 &

