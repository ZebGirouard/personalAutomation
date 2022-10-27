#!/bin/sh

echo 'Starting Author'

"$SCRIPTS/kill-author.sh"

output_path="$OUTPUTS/authorProcesses"
cd "$HOME/Coding/work/author/client"
yarn install
yarn start &
pid=$!
echo $pid >>$output_path