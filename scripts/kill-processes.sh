processes_file_path=$1

processes_to_kill=""

while IFS= read -r line
do
 processes_to_kill+=" $line"
done < "$processes_file_path"

echo "Killing $processes_to_kill"

kill $processes_to_kill