#!/bin/sh
set -eu

case "${1:-server}" in
    server) config=fba_server ;;
    worker) config=fba_celery_worker ;;
    beat) config=fba_celery_beat ;;
    *)
        echo "Unknown backend role: $1 (expected server, worker or beat)" >&2
        exit 1
        ;;
esac

# Each container loads only its own process configuration from the shared image.
cp "/fba/deploy/backend/supervisor/${config}.conf" /etc/supervisor/conf.d/backend.conf

if [ "$config" = fba_server ]; then
    exec sh /fba/deploy/backend/docker-entrypoint.sh
fi

exec supervisord -c /etc/supervisor/supervisord.conf
