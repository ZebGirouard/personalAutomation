#!/bin/bash

echo 'Starting Content Service Legacy'

output_path="$OUTPUTS/csLegacyProcesses"
cd "$HOME/Coding/work/content_service"
bundle install
docker-compose up &
pid=$!
echo $pid >$output_path
if [ "$1" = "test" ]; then
    ./test/run.sh &
else
    bundle exec rackup &
fi

pid=$!
echo $pid >>$output_path