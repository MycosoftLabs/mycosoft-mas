#!/bin/sh
# wait-for-it.sh

set -e

host=$(echo "$1" | cut -d: -f1)
port=$(echo "$1" | cut -d: -f2)
shift
cmd="$@"

until nc -z "$host" "$port"; do
  >&2 echo "Service on $host:$port is unavailable - sleeping"
  sleep 1
done

>&2 echo "Service on $host:$port is up - executing command"
exec $cmd 