#!/usr/bin/env bash
######
## UPDATE for 2019: I completely changed my approach on how to obtain the emoji dump.
## The new approach results in a JSON file, so the processing is a bit diferent than
## with the previous version.  This version will also take care of aliased emoji.

# Use:
# Make this file executable, and feed it the results from the Slack emoji URL dump. Files will be downloaded to `codecademy`
# 	chmod +x download.sh
# 	./download.sh emoji.json




# Input File
INPUT="$1"

# Create codecademy directory where downloaded emoji will be stored
mkdir -p codecademy;


# Clean Up Source File:
# Break up the file into individual lines for processing (Comma and { to NewLine)
# Slack's emoji JSON brings an unwanted escape character "\". We need to remove it.
# We'll also remove unwanted quote marks `"` and curly braces "{"  "}"

RAW_LIST=$(cat "${INPUT}" | tr ",{" "\\n" | sed -E 's/[\\"{}]//g')

# Separate into Custom Emoji (Ignoring slack's default ones) and Aliases

# Filter for custom emoji (ie: Anything on emoji.slack-edge.com), and remove the ":" separator
EMOJI_LIST=$( echo "${RAW_LIST}" | grep "https://emoji.slack-edge.com" | sed 's/: https/ https/')

# Filter for the aliases, and remove the separator
ALIAS_LIST=$( echo "${RAW_LIST}" | grep ":alias:" | sed 's/:alias:/ /' )


# First download all the emoji
echo "${EMOJI_LIST}" |
while read -r line || [[ -n "$line" ]]; do
echo "Downloading ${line}"
	parts=($line)
	url=${parts[1]}
	# name=${parts[0]}
	# extension=${url##*.}
    name=${url##*/}

	# echo "Downloading ${name}.${extension}"
    echo "Downloading ${name}"
	curl -s -o "codecademy/${name}" "${url}"

done;

# Now duplicate all the aliases
echo "${ALIAS_LIST}" |
while read -r line || [[ -n "$line" ]]; do
	parts=($line)
	alias=${parts[0]}
	source=${parts[1]}


	target=$(echo "${EMOJI_LIST}" | grep "${source} ")
	extension=${target##*.}


	echo "Looking for source of ${alias} in ${source} -> ${target}"
	echo "copying codecademy/${source}.${extension} to codecademy/${alias}.${extension}"
	cp "codecademy/${source}.${extension}" "codecademy/${alias}.${extension}"

done;