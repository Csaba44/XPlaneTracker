#!/bin/sh
set -e

cd /var/www

if [ -z "$APP_KEY" ]; then
  echo "APP_KEY missing, refusing to start"
  exit 1
fi

echo "Running migrations (forced, prod)..."
php artisan migrate --force

echo "Starting php-fpm..."
exec php-fpm
