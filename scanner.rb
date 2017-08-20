#!/usr/bin/env ruby

class Callback
    def initialize()
    end
    def callback(input_file, frames)
    end
    def needs_processing(input_file)
    end
end

class Scanner
    def initialize(directory, input_extension, callback_list)
        @directory = File.expand_path(directory)
        @input_extension = input_extension
        @callback_list = Array.new
        @callback_list.push(callback_list)
        @callback_list.flatten!
        throw "ffmpeg is required" if !is_ffmpeg_present()
    end

    def is_ffmpeg_present()
        result = `which ffmpeg`
        return false if nil == result || result.empty?
        return true
    end
    private :is_ffmpeg_present

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
        print("Extracting frames from #{video_filename}\n")
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
    
    def load_frames(folder, frames)
        Dir.new(folder).each { |filename|
            if (0 == filename.index('img') && filename.end_with?('.jpg'))
                frames << File.expand_path(folder + '/' + filename);
            end
        }
    end
    private :load_frames
    
    def scan()
        scan_dir(@directory)
    end

    def scan_dir(directory_name)
        Dir.open(directory_name) { |dir|
            dir.each { |item|
                next if item.empty? || '.' == item[0]
                full_path = File.expand_path(directory_name + "/" + item)
                
                if File.directory?(full_path)
                    scan_dir(full_path) 
                    next
                end
                next if !full_path.end_with?(@input_extension)
                
                any_need_processing = false
                @callback_list.each { |obj|
                    any_need_processing = any_need_processing | obj.needs_processing(full_path)
                }
                
                if any_need_processing
                    temp_folder = "/tmp/tagger/"
                    `rm -rf #{temp_folder}`
                    Dir.mkdir(temp_folder)
                    frames = Array.new
                    extract_frames(full_path, 1, temp_folder)
                    load_frames(temp_folder, frames)
                    @callback_list.each { |obj|
                        obj.callback(full_path, frames)
                    }
                end
            }
        }
    end
    private :scan_dir
end

