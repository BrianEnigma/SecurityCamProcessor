# ...


## Dependencies

- ffmpeg
    - `brew install ffmpeg`
- ImageMagick (specifically, the "convert" command)
    - `brew install imagemagick`
- gifsicle
    - `brew install gifsicle`
- aws-sdk gem
    - `sudo gem install aws-sdk`

# Get a list of tags found to be important

```
cat *.json | jq '.important_tags[]' | sort -u |  sed 's/"//g'
```

Useful for finding additional tags to filter.

# TODO

- Add percentages to json
- Create a generic test harness tool that takes the plugin name as a parameter

