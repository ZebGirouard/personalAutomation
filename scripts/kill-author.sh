#!/bin/sh

echo 'Killing Author'

input_path="$OUTPUTS/authorProcesses"

"$SCRIPTS/kill-processes.sh" $input_path
