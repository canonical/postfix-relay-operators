#!/bin/bash

inotifywait -mr /etc/postfix --exclude /etc/postfix/main.cf --exclude /etc/postfix/master.cf -e close_write -e create -e delete -e move --format '%w %e %T' --timefmt '%H%M%S' | while read file event tm; do
    current=$(date +'%H%M%S')
    delta=`expr $current - $tm`
    if [ $delta -lt 2 -a $delta -gt -2 ] ; then
        sleep 1  # sleep 1 set to let file operations end
        postmap $file
    fi
done
