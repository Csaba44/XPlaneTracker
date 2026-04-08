########################
# BASE
########################
FROM php:8.4-fpm-alpine AS base

RUN addgroup -g 1000 app \
 && adduser -G app -g app -s /bin/sh -D app

RUN apk add --no-cache \
    git unzip libzip-dev oniguruma-dev \
 && docker-php-ext-install pdo_mysql zip

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www


########################
# DEV
########################
FROM base AS dev

USER app
CMD ["php-fpm"]


########################
# PROD
########################
FROM base AS prod

COPY . /var/www

RUN mkdir -p storage bootstrap/cache \
 && chown -R app:app /var/www

RUN composer install \
    --no-dev \
    --optimize-autoloader \
    --no-interaction \
    --no-progress

USER app

CMD ["php-fpm"]
