#!/bin/bash
# Make sure to give this script execution permission (chmod +x reset_test_db.sh)

# Check if the script is run as root (sudo)
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo."
  exit 1
fi

# Define the container name
container_name="musicbrainz-docker-musicbrainz-1"

# Define the command to be executed
command="script/create_test_db.sh"

# Run the docker exec command
docker exec "$container_name" "$command"
