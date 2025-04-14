#!/bin/bash

export GDRIVE_FOLDER_ID="1axp3gAWo6VeAFq16oj1B5Nm06us2FBdR"
export GOOGLE_APPLICATION_CREDENTIALS="./credentials/gcp-oauth.keys.json"
export MCP_GDRIVE_CREDENTIALS="./credentials/.gdrive-server-credentials.json"

node index_mod.js "$@" auth
