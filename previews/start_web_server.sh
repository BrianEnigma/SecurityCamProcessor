#!/bin/bash

FOLDER=$HOME/Security/live/

cp index.html $FOLDER

#docker run --name security-nginx -v "$FOLDER:/usr/share/nginx/html:ro" -d --restart unless-stopped -p 8080:80 nginx
docker run --rm --name security-nginx -v "$FOLDER:/usr/share/nginx/html:ro" -d -p 8080:80 nginx

exit 0

