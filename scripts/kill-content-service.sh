#!/bin/sh

echo 'Killing Content Service Legacy'

input_path="$OUTPUTS/csLegacyProcesses"

"$SCRIPTS/kill-processes.sh" $input_path
