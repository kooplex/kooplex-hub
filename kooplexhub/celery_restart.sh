#kill 
#nohup python3 -m celery -A kooplexhub beat --scheduler django_celery_beat.schedulers:DatabaseScheduler &
#nohup python3 -m celery -A kooplexhub worker &

kill $(ps axu | awk '/python3 -m celery -A kooplexhub worker/ && !/awk/ {print $2}')
kill $(ps axu | awk '/celery -A kooplexhub beat/ && !/awk/ {print $2}')

