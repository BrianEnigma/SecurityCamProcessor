#!/usr/bin/env ruby

require './scanner'

class Summarizer < DirectoryCallback
    def initialize()
        super()
    end

    def read_json_list(directory_name)
        result = Array.new
        directory_name = File.expand_path(directory_name)
        Dir.open(directory_name) { |dir|
            dir.each { |item|
                full_path = File.expand_path(directory_name + "/" + item)
                next if item.empty? || '.' == item[0]
                next if File.directory?(full_path)
                next if !full_path.end_with?(".json")
                result << full_path
            }
        }
        result.sort!
        return result
    end
    private :read_json_list    
    
    def needs_processing(input_file)
        summary_file = File.expand_path(input_file + "/summarizer.txt")
        p summary_file
        count_expected = 0
        count_actual = read_json_list(input_file).size
        if File.exists?(summary_file)
            f = File.open(summary_file, "r")
            count_expected = f.readline().to_i
            f.close()
        end
        return count_actual != count_expected
    end

    def callback(input_file)
        print("Summarizer callback called for #{input_file}\n")
        json_files = read_json_list(input_file)
        p json_files
    end
end
