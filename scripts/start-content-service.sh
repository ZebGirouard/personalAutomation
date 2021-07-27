#!/bin/sh

echo 'Starting Content Service Legacy'

cd ~/Coding/work/content_service
bundle install
docker-compose up &
if $1 == 'test'
then
    ./test/run.sh
else
    bundle exec rackup
fi
