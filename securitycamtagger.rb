#!/usr/bin/env ruby

require './scanner'
require './tagger'
require './gifmaker'

running=`pgrep -f securitycamtagger`
if !running.empty?
    print "This script is already running.\n"
    exit 0
end

if ARGV.empty?
    print "Put folder to recursively scan on the command line.\n"
    exit 1
end

tagger = Tagger.new()
gifmaker = GifMaker.new()
scanner = Scanner.new(ARGV[0], ".mp4", [tagger, gifmaker])
scanner.scan()
