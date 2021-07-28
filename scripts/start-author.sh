#!/bin/sh

echo 'Starting Author'

"$SCRIPTS/kill-author.sh"

output_path="$OUTPUTS/authorProcesses"
cd "$HOME/Coding/work/author"
bundle install
yarn install
yarn start:postgres
yarn start:rails &
pid=$!
echo $pid >$output_path
cd client
yarn install
yarn start &
pid=$!
echo $pid >>$output_path