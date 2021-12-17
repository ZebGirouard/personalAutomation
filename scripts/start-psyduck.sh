#!/bin/sh

echo 'Starting Content Service (psyduck)'

"$SCRIPTS/kill-psyduck.sh"

output_path="$OUTPUTS/psyduckProcesses"
cd "$HOME/Coding/work/psyduck"
make dev-build&
pid=$!
echo $pid >$output_path
make dev-up&
pid=$!
echo $pid >>$output_path