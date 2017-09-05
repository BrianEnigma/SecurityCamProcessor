#!/usr/bin/env ruby

require './scanner'
require './tagger'
require './gifmaker'
require './summarizer'

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
summarizer = Summarizer.new()
scanner = Scanner.new(ARGV[0], ".mp4", [tagger, gifmaker], [summarizer])
scanner.scan()
