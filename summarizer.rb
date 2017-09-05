#!/usr/bin/env ruby

require 'json'
require './scanner'

SUMMARIZER_HEADER = <<-HERE_HEADER
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-type" content="text/html; charset=utf-8">
    <title>Security Cam Summary</title>
    <style type="text/css" media="screen">
        div.summary {
            display:inline-block;
            width:300px;
            margin:10px;
            padding:0;
            vertical-align:top;
        }
        img.gif_thumbnail {
            width:300px;
            height:169px;
            border:none;
            margin:0;
            padding:0;
        }
        div.thumbnail {
            display:block;
        }
        div.filename {
            display:block;
            font-size:50%;
        }
        div.filename > a {
            color:black;
            text-decoration:none;
        }
        div.flagged {
            width:300px;
            display:block;
            font-weight:bold;
        }
        div.important {
            width:300px;
            display:block;
        }
        ul.tags {
            list-style:none;
            padding:0;
        }
    </style>
    
</head>
<body id="summarizer" onload="">
HERE_HEADER
SUMMARIZER_FOOTER = <<-HERE_HEADER
</body>
</html>
HERE_HEADER

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
        f << "<div class=\"#{class_container}\"><ul class=\"tags tags_#{class_container}\">"
        tags.each { |item|
            tag = item.keys[0]
            percent = item[tag]
            f << "<li>"
            f << "<span class=\"#{class_item}\">#{tag}</span>"
            f << "<span class=\"#{class_percent}\">(#{percent}%)</span>"
            f << "</li>"
        }
        f << "</ul></div>"
    end
    
    def write_json_to_html(f, json_file_name)
        image_filename = json_file_name.gsub(".json", ".gif")
        video_filename = File.basename(json_file_name.gsub(".json", ".mp4"))
        data = JSON.parse(File.read(json_file_name))
        f << "<div class=\"summary\">"
        f << "<div class=\"thumbnail\">"
        f << "<a href=\"#{video_filename}\"><img src=\"#{image_filename}\" class=\"gif_thumbnail\" alt=\"animated thumbnail\"/></a>"
        f << "<div class=\"filename\"><a href=\"#{video_filename}\">#{video_filename}</a></div>"
        f << "</div>"
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
        f << SUMMARIZER_HEADER
        write_count = 0
        json_files = read_json_list(input_file)
        json_files.each { |json_file|
            write_json_to_html(f, json_file)
            write_count += 1
        }
        f << SUMMARIZER_FOOTER
        f.close()
        f = File.open(summary_file, "w")
        f << write_count
        f.close()
    end
end
