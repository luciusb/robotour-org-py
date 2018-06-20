#!/bin/sh

ssh ondra@live.robotour.cz <<EOF
cd ~/live.robotour.cz
git pull
touch tmp/restart.txt
EOF
