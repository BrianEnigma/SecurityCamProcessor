#!/usr/bin/env ruby

require './scanner'

class GifMaker < Callback
    def initialize()
        super()
        throw "ImageMagic convert is required" if !is_convert_present()
    end
    
    def is_convert_present()
        result = `which convert`
        return false if nil == result || result.empty?
        return true
    end
    private :is_convert_present
    
    def convert_frames(frames)
        frames.each { |filename|
            outfile = filename[0, filename.rindex('.')] + ".gif"
            @frames_resized << outfile
            cmd = "convert -resize 300x300 '" + filename + "' '" + outfile + "'"
            system(cmd)
        }
    end
    private :convert_frames
    
    def build_gif(output_file)
        cmd = "gifsicle --merge --delay 3 --loopcount=0 --optimize --colors 256"
        @frames_resized.sort.each { |file|
            cmd += " '" + file + "'"
        }
        cmd += " > '" + output_file + "'"
        system(cmd)
    end
    private :build_gif

    def needs_processing(input_file)
        output_file = input_file[0, input_file.rindex('.')] + ".gif"
        return !File.exists?(output_file)
    end
    
    def callback(input_file, frames)
        output_file = input_file[0, input_file.rindex('.')] + ".gif"
        return if !File.exists?(input_file)
        return if File.exists?(output_file)
        
        print("#{input_file} => #{output_file}\n")
        @frames_resized = Array.new
        convert_frames(frames)
        build_gif(output_file)
    end
end
