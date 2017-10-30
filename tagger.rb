#!/usr/bin/env ruby

require 'yaml'
require 'aws-sdk'
require './scanner'

class Tagger < Callback
    def initialize()
        super()
        @tags = Hash.new
        # Sample every three incoming frames. This is equivalent to every three seconds.
        @sample_period = 3
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
        
        frame_counter = 0
        sorted_frames = frames.sort
        sorted_frames.each { |frame|
            if (frame_counter % @sample_period == 0)
                #puts("Checking file #{frame}")
                process_frame(frame)
            else
                #puts("Skipping file #{frame}")
            end
            frame_counter += 1
        }
        flagged_tags = Hash.new
        important_tags = Hash.new
        ignored_tags = Hash.new
        @tags.each_pair { |tag, percent|
            if @flagged_tags.include?(tag)
                flagged_tags[tag] = percent
            elsif @stopwords.include?(tag)
                ignored_tags[tag] = percent
            else
                important_tags[tag] = percent
            end
        }
        f = File.new(output_file, 'w')
        f << "{\n"
        f << "\t\"flagged_tags\": [\n"
        first = true
        flagged_tags.each_pair { |tag, percent|
            f << "\t\t"
            if first
                first = false
            else
                f << ","
            end
            f << "{\"#{tag}\": #{percent}}\n"
        }
        f << "\t],\n"
        f << "\t\"important_tags\": [\n"
        first = true
        important_tags.each_pair { |tag, percent|
            f << "\t\t"
            if first
                first = false
            else
                f << ","
            end
            f << "{\"#{tag}\": #{percent}}\n"
        }
        f << "\t],\n"
        f << "\t\"ignored_tags\": [\n"
        first = true
        ignored_tags.each_pair { |tag, percent|
            f << "\t\t"
            if first
                first = false
            else
                f << ","
            end
            f << "{\"#{tag}\": #{percent}}\n"
        }
        f << "\t]\n}\n"
        f.close()
    end
end
