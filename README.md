# MusicBrainz Bot

This bot it indended to allow editing MusicBrainz automatically.
If you want to edit the main MusicBrainz database, rather than your own
local server, make sure to follow
[the bot Code of Conduct](https://musicbrainz.org/doc/Code_of_Conduct/Bots)
and make the scripts you are running available (for example on your fork
of this repository).


# Setup
### Setup MusicBrainz-Docker test server:
1. Follow [musicbrainz-docker test setup guide](https://github.com/metabrainz/musicbrainz-docker/tree/master#test-setup) to setup a test server. Make sure to [also publish the database port](https://github.com/metabrainz/musicbrainz-docker/blob/master/README.md#publish-ports-of-all-services).
   
    ```bash
    git clone https://github.com/metabrainz/musicbrainz-docker.git
    cd musicbrainz-docker
    
    admin/configure add musicbrainz-standalone
    admin/configure add publishing-db-port
    
    sudo docker compose build
    sudo docker compose run --rm musicbrainz createdb.sh -sample -fetch
    sudo docker compose up -d
    ```

2. Now enter the `musicbrainz` container using `sudo docker exec -it musicbrainz-docker-musicbrainz-1 bash`.

   1. Now you are inside the container. Edit the DBDefs.pm file using `vim lib/DBDefs.pm`.
   2. Make the following changes:
      1. Under the "# The Database" section, set the **TEST** `host` to `db` and `port` to `5432`.
      2. Under the "# Server Settings" section, <br> replace `# sub DB_STAGING_TESTING_FEATURES { my $self = shift; $self->DB_STAGING_SERVER }` <br> with `sub DB_STAGING_TESTING_FEATURES { 1 }` (Make sure to uncomment the line.)
      3. Under the "# Other Settings" section, <br> replace `# sub USE_SET_DATABASE_HEADER { 0 }` <br> with `sub USE_SET_DATABASE_HEADER { 1 }` (make sure to uncomment the line.)
   3. Save changes using `:wq` in vim command mode.

   4. Exit the container using `exit`

3. Restart the docker-container using `sudo docker compose restart`

### Setup the MusicBrainz-Bot:
1. Clone the repository using `git clone https://github.com/metabrainz/musicbrainz-bot.git`
2. Change directory to the repository using `cd musicbrainz-bot`
3. Create a new virtual environment using `python3 -m venv env`
4. Activate the environment using `source env/bin/activate`
5. Install requirements using `pip install -r requirements.txt`

### Run Tests:
1. Run `pytest -s` to run all the tests.