# MusicBrainz Bot

This bot it indended to allow editing MusicBrainz automatically.
If you want to edit the main MusicBrainz database, rather than your own
local server, make sure to follow
[the bot Code of Conduct](https://musicbrainz.org/doc/Code_of_Conduct/Bots)
and make the scripts you are running available (for example on your fork
of this repository).


# Setup:
### Setup MusicBrainz-Docker test server:
1. Follow [musicbrainz-docker test setup guide](https://github.com/metabrainz/musicbrainz-docker/tree/master#test-setup) to setup a test server. Make sure to [also publish the database port](https://github.com/metabrainz/musicbrainz-docker/blob/master/README.md#publish-ports-of-all-services).
   
    ```bash
    git clone https://github.com/metabrainz/musicbrainz-docker.git
    cd musicbrainz-docker
    
    admin/configure add musicbrainz-standalone
    admin/configure add publishing-db-port
    
    sudo docker-compose build
    sudo docker-compose run --rm musicbrainz createdb.sh -sample -fetch
    sudo docker-compose up -d
    ```

2. In your `musicbrainz-docker` directory, run `sudo docker-compose ps` to check that all the containers are running. Copy the container id of the musicbrainz container.

3. Rename the `musicbrainz` container using `sudo docker rename <container_id> musicbrainz`.

4. Now enter the `musicbrainz` container using `sudo docker exec -it musicbrainz bash`.

   1. Now you are inside the container. Edit the DBDefs.pm file using `vim lib/DBDefs.pm`. Refer extras/DBDefs.pm for the changes to be made.
   2. Exit the container using `exit`

5. Restart the docker-container using `sudo docker-compose restart`

### Setup the MusicBrainz-Bot:
1. Clone the repository
2. Create a new virtual environment using `python3 -m venv env`
3. Install requirements using `pip install -r requirements.txt`

### Run Tests:
1. Run `pytest -s` to run all the tests.