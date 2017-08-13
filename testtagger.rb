#!/usr/bin/env ruby

require './tagger'

if ARGV.length != 1
    print "Put input file on command line"
    exit(1)
end

tagger = Tagger.new
tagger.callback(ARGV[0])

