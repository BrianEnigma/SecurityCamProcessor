#!/bin/bash
SRC=$HOME/Recordings/recent/
DST=$HOME/Recordings/archive/

cd $SRC
# All but the most recent five
OLD=`ls -1d 20* | sort | ghead -n -5`
for D in $OLD ; do
    echo $D
    mkdir -p $DST/$D
    mv $SRC/$D/* $DST/$D/
    rm -rf $SRC/$D
done

