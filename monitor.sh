#!/bin/sh
print_data() {
    DATE=$(date +%s)
    UPTIME=$(uptime)
    FREEMEM=$(free | head -n 2 | tail -n 1)
    FREEREAL=$(free | head -n 3 | tail -n 1)
    FREESWAP=$(free | head -n 4 | tail -n 1)
    LOAD1=$(echo $UPTIME | sed 's/^.*\(.\...\), \(.\...\), \(.\...\)$/\1/')
    LOAD5=$(echo $UPTIME | sed 's/^.*\(.\...\), \(.\...\), \(.\...\)$/\2/')
    LOAD10=$(echo $UPTIME | sed 's/^.*\(.\...\), \(.\...\), \(.\...\)$/\3/')
    MEMUSED=$(echo $FREEMEM | sed 's/  */ /g' | cut -d' ' -f3)
    MEMREALUSED=$(echo $FREERAL | sed 's/  */ /g' | cut -d' ' -f3)
    SWAPUSED=$(echo $FREESWAP | sed 's/  */ /g' | cut -d' ' -f3)
    echo -n '{"time": '
    echo -n $DATE
    echo -n ', "load1": '
    echo -n $LOAD1
    echo -n ', "load5": '
    echo -n $LOAD5
    echo -n ', "load10": '
    echo -n $LOAD10
    echo -n ', "memused": '
    echo -n $MEMUSED
    echo -n ', "memrealused": '
    echo -n $MEMREALUSED
    echo -n ', "swapused": '
    echo -n $SWAPUSED
    echo -n '}'
    echo
}
while true
do
    print_data
    sleep 1
done
