#!/bin/sh
print_data() {
    DATE=$(date +%s)
    UPTIME=$(uptime)
    LOAD1=$(echo $UPTIME | sed 's/^.*\(.\...\), \(.\...\), \(.\...\)$/\1/')
    LOAD5=$(echo $UPTIME | sed 's/^.*\(.\...\), \(.\...\), \(.\...\)$/\2/')
    LOAD10=$(echo $UPTIME | sed 's/^.*\(.\...\), \(.\...\), \(.\...\)$/\3/')
    echo -n '{"time": '
    echo -n $DATE
    echo -n ', "load1": '
    echo -n $LOAD1
    echo -n ', "load5": '
    echo -n $LOAD5
    echo -n ', "load10": '
    echo -n $LOAD10
    echo -n '}'
    echo
}
while true
do
    print_data
    sleep 1
done
