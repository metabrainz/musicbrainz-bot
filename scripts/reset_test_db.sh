#!/bin/bash

container_name="musicbrainz-docker-musicbrainz-1"

command="script/create_test_db.sh"

docker exec "$container_name" "$command"
