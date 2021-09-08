#!/bin/sh

echo 'Killing Monolith'

# Kill all node processes spun up independently from yarn start
kill $(ps -e | grep "node ./script" | awk '{print $1}')
kill $(ps -e | grep "webpack-dev-server.js" | awk '{print $1}')

input_path="$OUTPUTS/monolithProcesses"

"$SCRIPTS/kill-processes.sh" $input_path
