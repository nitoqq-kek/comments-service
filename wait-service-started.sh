#!/usr/bin/env sh

while ! nc -z $1 $2;
do
  echo waiting for $1:$2;
  sleep 1;
done;
echo Connected!;
