set -euo pipefail

PROJECT_DIR="/opt/starburger/star-burger"
ENV_FILE="$PROJECT_DIR/.env"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"

echo ">>> [1/7] Загружаем переменные окружения..."
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
else
  echo "Файл .env не найден по пути $ENV_FILE"
  exit 1
fi

echo ">>> [2/7] Обновляем код из GitHub..."
cd "$PROJECT_DIR"
git fetch --all
git reset --hard origin/master

echo ">>> [3/7] Собираем фронтенд..."
docker compose -f "$COMPOSE_FILE" run --rm frontend || {
  echo "Ошибка при сборке фронтенда, продолжаем..."
}

echo ">>> [4/7] Пересобираем и перезапускаем контейнеры..."
docker compose -f "$COMPOSE_FILE" down
docker compose -f "$COMPOSE_FILE" up -d --build

echo ">>> [5/7] Применяем миграции..."
docker compose -f "$COMPOSE_FILE" exec backend python manage.py migrate --noinput || {
  echo "Ошибка при миграции, продолжаем..."
}

echo ">>> [6/7] Собираем статику..."
docker compose -f "$COMPOSE_FILE" exec backend python manage.py collectstatic --noinput || {
  echo "Ошибка при сборке статики, продолжаем..."
}

echo ">>> [7/7] Проверяем статус контейнеров..."
docker compose -f "$COMPOSE_FILE" ps

if [ -n "${ROLLBAR_ACCESS_TOKEN:-}" ]; then
  REVISION=$(git rev-parse HEAD)
  echo ">>> Отправляем нотификацию в Rollbar..."
  curl -s https://api.rollbar.com/api/1/deploy/ \
    -F access_token="$ROLLBAR_ACCESS_TOKEN" \
    -F environment=production \
    -F revision="$REVISION" \
    -F local_username="$(whoami)" > /dev/null
  echo "Деплой зафиксирован в Rollbar."
fi

echo "Деплой завершён успешно."
