#!/bin/bash

echo 'Starting Monolith'

"$SCRIPTS/kill-monolith.sh"

output_path="$OUTPUTS/monolithProcesses"
cd "$HOME/Coding/work/Codecademy"
bundle install
yarn install
make services
bundle exec rails server &
pid=$!
echo $pid >$output_path

yarn --production=false&
pid=$!
echo $pid >>$output_path

node ./script/check-duplicate-packages.js&
pid=$!
echo $pid >>$output_path

node ./script/react/dev-server&
pid=$!
echo $pid >>$output_path

# ONE DAY ILL GET THIS TO WORK
# MESSYCOMMANDS=$(yarn run 2>/dev/null | sed -n '/- start$/{n;p;}' | sed 's/ \&\& /\&/g' | xargs)

# IFS='&' read -r -a monoCommands <<< "$MESSYCOMMANDS"
# for element in "${monoCommands[@]}"
# do
#     echo "${element}&"
#     eval "${element}&"
#     pid=$!
#     echo $pid >>$output_path
# done
