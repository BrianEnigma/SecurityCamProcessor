#!/usr/bin/env ruby

require 'yaml'
require 'aws-sdk'
require './scanner'

class Tagger < Callback
    def initialize()
        super()
        @tags = Array.new
        throw "ffmpeg is required" if !is_ffmpeg_present()
        throw "bad config" if !load_settings()
    end
    
    def is_ffmpeg_present()
        result = `which ffmpeg`
        return false if nil == result || result.empty?
        return true
    end
    private :is_ffmpeg_present

    def load_settings()
        settings = YAML.load(File.read('settings.yml'))
        @stopwords = settings['stopwords']
        if settings['access_key_id'].empty? || settings['secret_access_key'].empty?
            print("AWS credentials not found in settings.yml\n")
            return false
        end
        if settings['region'].empty?
            print("AWS region not found in settings.yml\n")
            return false
        end
        Aws.config.update(
            {
                region: settings['region'], 
                credentials: Aws::Credentials.new(settings['access_key_id'],settings['secret_access_key'])
            }
        )
        return true
    end
    private :load_settings
    
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
    
    def process_frames(tmp_location)
        Dir.new(tmp_location).each { |filename|
            #p filename
            if (0 == filename.index('img') && filename.end_with?('.jpg'))
                process_frame(File.expand_path(tmp_location + "/" + filename))
            end
        }
    end
    private :process_frames
    
    def process_frame(filename)
        rekognition = Aws::Rekognition::Client.new
        seconds = 0
        result = Array.new
        #contents = Base64.encode64(File.open(filename, 'rb').read(5000000))
        contents = File.open(filename, 'rb').read(5000000)
        #p contents[0, 70]
        labels = rekognition.detect_labels({
                image: {
                    bytes: contents
                },max_labels:20, min_confidence: 70
            }).labels
        label_string = ''
        labels.map { |l| 
            label_string += "'#{l.name}:#{l.confidence.to_i}%' "
        }
        print("#{filename} : #{label_string}\n")
        #result << [object.key, seconds, label_string, labels]
        @tags << labels.collect { |entry| entry.name.downcase }
        @tags.flatten!
        @tags.uniq!
    end
    private :process_frame

    def callback(input_file)
        output_file = input_file[0, input_file.rindex('.')] + ".json"
        return if !File.exists?(input_file)
        return if File.exists?(output_file)
        print("#{input_file} => #{output_file}\n")
        
        temp_folder = "/tmp/tagger/"
        `rm -rf #{temp_folder}`
        Dir.mkdir(temp_folder)
        
        extract_frames(input_file, 1, temp_folder)
        process_frames(temp_folder)
        important_tags = Array.new
        ignored_tags = Array.new
        @tags.each { |tag|
            if @stopwords.include?(tag)
                ignored_tags << tag
            else
                important_tags << tag
            end
        }
        f = File.new(output_file, 'w')
        f << "{\n\t\"important_tags\": [\n"
        first = true
        important_tags.each { |tag|
            f << "\t\t"
            if first
                first = false
            else
                f << ","
            end
            f << "\"#{tag}\"\n"
        }
        f << "\t],\n"
        f << "\t\"ignored_tags\": [\n"
        first = true
        ignored_tags.each { |tag|
            f << "\t\t"
            if first
                first = false
            else
                f << ","
            end
            f << "\"#{tag}\"\n"
        }
        f << "\t]\n}\n"
        f.close()
    end
end
