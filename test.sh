#!/bin/bash

python Main.py &

sleep 10

PID=$!

if ps -p $PID> /dev/null ; then
	echo "found"
	kill $PID
	exit 0 
else
	echo "none found"
	kill $PID
	exit 1
fi
