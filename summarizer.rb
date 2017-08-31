#!/usr/bin/env ruby

require 'json'
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
        index_file = File.expand_path(input_file + "/index.html")
        return true if !File.exists?(index_file)
        count_expected = 0
        count_actual = read_json_list(input_file).size
        if File.exists?(summary_file)
            f = File.open(summary_file, "r")
            count_expected = f.readline().to_i
            f.close()
        end
        return count_actual != count_expected
    end
    
    def print_tag_list(f, tags, class_container, class_item, class_percent)
        f << "<div class=\"#{class_container}\">"
        tags.each { |item|
            tag = item.keys[0]
            percent = item[tag]
            f << "<div class=\"#{class_item}\">#{tag}</div>"
            f << "<div class=\"#{class_percent}\">(#{percent}%)</div>"
        }
        f << "</div>"
    end
    
    def write_json_to_html(f, json_file_name)
        data = JSON.parse(File.read(json_file_name))
        f << "<div class=\"summary\">"
        
        # TODO: gif file
        
        flagged = data['flagged_tags']
        print_tag_list(f, flagged, 'flagged', 'flagged_tag', 'flagged_tag_percent')
        important = data['important_tags']
        print_tag_list(f, important, 'important', 'important_tag', 'important_tag_percent')
        f << "</div>\n\n"
    end
    private :write_json_to_html

    def callback(input_file)
        summary_file = File.expand_path(input_file + "/summarizer.txt")
        index_file = File.expand_path(input_file + "/index.html")
        f = File.open(index_file, "w")
        write_count = 0
        print("Summarizer callback called for #{input_file}\n")
        json_files = read_json_list(input_file)
        json_files.each { |json_file|
            write_json_to_html(f, json_file)
            write_count += 1
        }
        f.close()
        f = File.open(summary_file, "w")
        f << write_count
        f.close()
    end
end
