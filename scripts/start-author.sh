#!/bin/sh

echo 'Starting Author'

cd ~/Coding/work/author
bundle install
yarn install
yarn start:postgres
yarn start:rails &
cd client
yarn install
yarn start &