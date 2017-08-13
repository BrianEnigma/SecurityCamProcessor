#!/usr/bin/env ruby

require './gifmaker'

if ARGV.length != 1
    print "Put input file on command line"
    exit(1)
end

gifmaker = GifMaker.new
gifmaker.callback(ARGV[0])
