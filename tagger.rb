#!/usr/bin/env ruby

require 'yaml'
require 'aws-sdk'
require './scanner'

class Tagger < Callback
    def initialize()
        super()
        @tags = Array.new
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
        }
        print("#{filename} : #{label_string}\n")
        #result << [object.key, seconds, label_string, labels]
        @tags << labels.collect { |entry| entry.name.downcase }
        @tags.flatten!
        @tags.uniq!
    end
    private :process_frame

    def needs_processing(input_file)
        output_file = input_file[0, input_file.rindex('.')] + ".json"
        return !File.exists?(output_file)
    end

    def callback(input_file, frames)
        output_file = input_file[0, input_file.rindex('.')] + ".json"
        return if !File.exists?(input_file)
        return if File.exists?(output_file)
        print("#{input_file} => #{output_file}\n")
        
        frames.each { |frame|
            process_frame(frame)
        }
        flagged_tags = Array.new
        important_tags = Array.new
        ignored_tags = Array.new
        @tags.each { |tag|
            if @flagged_tags.include?(tag)
                flagged_tags << tag
            elsif @stopwords.include?(tag)
                ignored_tags << tag
            else
                important_tags << tag
            end
        }
        f = File.new(output_file, 'w')
        f << "{\n"
        f << "\t\"flagged_tags\": [\n"
        first = true
        flagged_tags.each { |tag|
            f << "\t\t"
            if first
                first = false
            else
                f << ","
            end
            f << "\"#{tag}\"\n"
        }
        f << "\t],\n"
        f << "\t\"important_tags\": [\n"
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
