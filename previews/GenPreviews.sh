#!/bin/bash

source config.sh

# Kill any previous instance that might be around. Systemd doesn't seem to correctly timeout.
ps ax | grep ffmpeg | grep thumbnail | sed 's/^ *//' | cut -d ' ' -f1 | xargs kill

# Capture thumbnails to temp folder
for ((i = 0 ; i < ${#CAMERAS[@]} ; i++)) ; do
	LINE=(${CAMERAS[i]})
	IP=${LINE[0]}
	NAME=${LINE[1]}
	USER=${LINE[2]}
	PASS=${LINE[3]}
	ffmpeg -hide_banner \
		-i rtsp://$USER:$PASS@$IP:554/h264Preview_01_sub \
		-vf "select='eq(pict_type,PICT_TYPE_I)'" \
		-vsync vfr \
		-frames 1 \
		-f image2 \
		-y /Users/admin/Security/live/thumbnail-$NAME.jpg
	#ffmpeg -hide_banner -loglevel fatal \
done

# Copy to web folder
cp /Users/admin/Security/live/thumbnail* /Users/admin/Security/live/

exit 0

