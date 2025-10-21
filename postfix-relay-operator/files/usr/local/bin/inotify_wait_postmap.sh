#!/bin/bash

lock=/tmp/inofity.lock
inotifywait -mr /etc/postfix --exclude /etc/postfix/main.cf --exclude /etc/postfix/master.cf -e close_write -e create -e delete -e move --format '%w%f %e' | while read -r file event; do
    : >> $lock #create a file if it doesn't exist
    {
    flock 3 # lock file by filedescriptor
    sleep 5
    # variable will be set by Juju
    # shellcheck disable=SC2154
    /var/lib/juju/agents/"$juju_unit_agent_name"/charm/hooks/config-changed
    } 3<$lock
done
