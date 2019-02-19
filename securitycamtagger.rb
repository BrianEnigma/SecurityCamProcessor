#!/usr/bin/env ruby

require './scanner'
require './tagger'
require './gifmaker'
require './summarizer'
require './mover'

running=`pgrep -f securitycamtagger`
if !running.empty?
    print "This script is already running.\n"
    exit 0
end

if ARGV.length != 2
    print "Usage: securitycamtagger.rb {input directory} {output directory}\n"
    exit 1
end

input_folder = ARGV[0]
output_folder = ARGV[1]

mover = Mover.new(input_folder, output_folder, 2)
mover.move()

tagger = Tagger.new()
gifmaker = GifMaker.new()
summarizer = Summarizer.new()
scanner = Scanner.new(output_folder, ".mp4", [tagger, gifmaker], [summarizer])
scanner.scan()
