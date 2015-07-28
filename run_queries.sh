#!/bin/sh
run_query() {
    DATE=$(date +%s)
    /usr/bin/time -a -o timedata.json --format '{"time":'$DATE', "elapsed": %e}' curl -s localhost:9200/cds-*/_search -d'{
    "query": {
        "match": {
            "id_user": 0
        }
    },
    "aggregations": {
        "by_bibrec": {
            "terms": {
                "field": "id_bibrec"
            }
        }
    }
}' > /dev/null
}
while true
do
    run_query
    tail -n 1 timedata.json
    sleep 0.1
done

