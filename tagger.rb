#!/usr/bin/env ruby

require 'yaml'
require 'json'
require 'aws-sdk'
require './scanner'
require './metadata'

SKIP_THRESHOLD = 120

class Tagger < Callback
    def initialize()
        super()
        @tags = Hash.new
        # Sample every three incoming frames. This is equivalent to every three seconds.
        @sample_period = 3
        # Time (in seconds since midnight) associated with the last thing we performed scanning on.
        # This is used to help throttle against conditions like rain or wind (with moving shadows)
        # that could drop hundreds of files in an hour. If "this" video is too close to the previous
        # video, we'll skip running Rekognizer on it.
        @previous_item_time = -9999
        # Number of samples to take for tagging. For instance when given 20 frames of video (20 seconds),
        # divide by this number. In that example, we'd ask for keywords for every 4th frame.
        @partitions = 5
        throw "bad config" if !load_settings()
    end
    
    def load_settings()
        settings = YAML.load(File.read('settings.yml'))
        @stopwords = settings['stopwords']
        @flagged_tags = settings['flagged_tags']
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
    
    def add_tag(name, confidence)
        name = name.downcase
        if @tags.has_key?(name)
            @tags[name] = [@tags[name], confidence.to_i].max
        else
            @tags[name] = confidence.to_i
        end
    end
    private :add_tag
        
    def process_frame(filename)
        rekognition = Aws::Rekognition::Client.new
        seconds = 0
        result = Array.new
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
            add_tag(l.name, l.confidence)
        }
        print("#{filename} : #{label_string}\n")
    end
    private :process_frame

    def needs_processing(input_file)
        output_file = input_file[0, input_file.rindex('.')] + ".json"
        return !File.exists?(output_file)
    end
    
    def callback(input_file, frames)
        @tags = Hash.new
        output_file = input_file[0, input_file.rindex('.')] + ".json"
        return if !File.exists?(input_file)
        return if File.exists?(output_file)
        print("#{input_file} => #{output_file}\n")
        
        flagged_tags = Hash.new
        important_tags = Hash.new
        ignored_tags = Hash.new

        times = Metadata.extract_times(input_file)
        current_item_time = times[:time_start]
        sorted_frames = frames.sort
        if sorted_frames.length <= 6
            check_frames = sorted_frames
        else
            check_frames = []
            span = (sorted_frames.length / @partitions).to_i
            check_frames << sorted_frames[5] # Always get second six because the video has 5s buffer from before motion triggering
            counter = span - 1
            while (counter < sorted_frames.length)
                check_frames << sorted_frames[counter]
                counter += span
            end
        end

        check_frames.each { |frame|
            process_frame(frame)
        }
        @tags.each_pair { |tag, percent|
            if @flagged_tags.include?(tag)
                flagged_tags[tag] = percent
            elsif @stopwords.include?(tag)
                ignored_tags[tag] = percent
            else
                important_tags[tag] = percent
            end
        }
        
        jsonHash = {
            'flagged_tags' => flagged_tags,
            'important_tags' => important_tags,
            'ignored_tags' => ignored_tags,
            'time_start' => times[:time_start],
            'time_end' => times[:time_end],
            'duration' => times[:duration],
            'since' => current_item_time - @previous_item_time
        }
        
        File.open(output_file, 'w') do |f|
            f.write(JSON.pretty_generate(jsonHash))
        end
        
        @previous_item_time = times[:time_end]
    end
end
