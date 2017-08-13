#!/usr/bin/env ruby

require './scanner'

class GifMaker < Callback
    def initialize()
        super()
        throw "ffmpeg is required" if !is_ffmpeg_present()
        throw "ImageMagic convert is required" if !is_convert_present()
    end
    
    def is_ffmpeg_present()
        result = `which ffmpeg`
        return false if nil == result || result.empty?
        return true
    end
    private :is_ffmpeg_present

    def is_convert_present()
        result = `which convert`
        return false if nil == result || result.empty?
        return true
    end
    private :is_convert_present
    
    def timecode_string(seconds)
        hours = (seconds / (60 * 60)).to_i
        seconds = seconds % (60 * 60)
        minutes = (seconds / 60).to_i
        seconds = seconds % 60
        return sprintf("%02u:%02u:%02u.000", hours, minutes, seconds)
    end
    private :timecode_string

    def extract_frames(video_filename, extract_period, tmp_location)
        seconds = 0
        counter = 0
        while true
            timecode = timecode_string(seconds)
            filename = sprintf("%s/img%05d.jpg", tmp_location, counter)
            cmd = "ffmpeg -loglevel 16 -ss #{timecode} -i \"#{video_filename}\" -frames:v 1 \"#{filename}\""
            print("#{timecode}\r")
            rc = Kernel.system(cmd)
            break if (true != rc)
            break if (!File.exists?(filename))
            seconds += extract_period
            counter += 1
        end
    end
    private :extract_frames
    
    def load_frames(folder)
        Dir.new(folder).each { |filename|
            if (0 == filename.index('img') && filename.end_with?('.jpg'))
                @frames_original << File.expand_path(folder + '/' + filename);
            end
        }
    end
    private :load_frames
    
    def convert_frames()
        @frames_original.each { |filename|
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

    def callback(input_file)
        output_file = input_file[0, input_file.rindex('.')] + ".gif"
        return if !File.exists?(input_file)
        return if File.exists?(output_file)
        
        temp_folder = "/tmp/tagger/"
        `rm -rf #{temp_folder}`
        Dir.mkdir(temp_folder)

        print("#{input_file} => #{output_file}\n")
        @frames_original = Array.new
        @frames_resized = Array.new
        extract_frames(input_file, 1, temp_folder)
        load_frames(temp_folder)
        convert_frames()
        build_gif(output_file)
    end
end
