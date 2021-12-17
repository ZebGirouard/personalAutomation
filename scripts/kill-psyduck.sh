#!/bin/sh

echo 'Killing Content Service (psyduck)'

input_path="$OUTPUTS/psyduckProcesses"

"$SCRIPTS/kill-processes.sh" $input_path
