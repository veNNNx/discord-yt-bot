# Discord YT music bot
Project was deployed via portainer.

# Deployment
## Prerequirements

* Create bot with proper access rights.
* Create `YouTube Data API v3` token in `Google Developers Console`.
* Fill tokens into `config.py`

## Setup docker image on server
* Drop all files or clone repository on server (create config.py and add tokens)
* Change permissions `chmod +x install_requirements.sh`
* Change permissions `chmod +x  src/modules/utils/scripts/restart.sh`
* Setup proper volume on server for static folder with in-memory playlists
* Create Docker Image using content of `Dockerfile` and files from repository.
* Create Custom Template in portainer using `portainer_template.txt`.
* Deploy the stack.

# TBD
## Skip to selected song in queue
