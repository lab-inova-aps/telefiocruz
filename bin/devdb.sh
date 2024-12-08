#!/bin/sh
ssh -p 22022 root@avafiocruz.com.br "cd /opt/telefiocruz/ && pg_dump -U postgres -d telefiocruz -f telefiocruz.sql && gzip telefiocruz.sql"
scp -P 22022 root@avafiocruz.com.br:/opt/telefiocruz/telefiocruz.sql.gz /tmp/telefiocruz.sql.gz
docker compose cp /tmp/telefiocruz.sql.gz postgres:/tmp
docker compose exec postgres psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'telefiocruz';"
docker compose exec postgres gunzip /tmp/telefiocruz.sql.gz
docker compose exec postgres dropdb -U postgres telefiocruz
docker compose exec postgres createdb -U postgres telefiocruz
docker compose exec postgres psql -U postgres -d telefiocruz -f /tmp/telefiocruz.sql
docker compose exec app python manage.py devdb 
