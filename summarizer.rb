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
        div.subdirectory {
            width:300px;
            margin:10px;
            padding:0;
            vertical-align:top;
        }
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
        div.gap {
            width:50%;
            font-size:85%;
            font-family:monospace;
        }
        div.gapWarning {
            background-color:#ccf;
            font-weight:bold;
        }
        div.gapError {
            background-color:#00f;
            color:#ff0;
            font-weight:bold;
        }
        div.filename {
            display:block;
            width:50%;
        }
        div.filename > a {
            font-size:50%;
            color:black;
            text-decoration:none;
        }
        div.duration {
            display:block;
            width:50%;
            float:right;
            text-align:right;
            font-family:monospace;
        }
        div.durationWarning {
            background-color:#ff0;
            font-weight:bold;
        }
        div.durationError {
            background-color:#f00;
            color:#ff0;
            font-weight:bold;
        }
        div.subdirectory > a {
            color:blue;
            font-size:16pt;
        }
        div.flagged {
            width:300px;
            display:block;
            font-weight:bold;
            color:red;
            background-color:#ffffcc;
        }
        div.important {
            width:300px;
            display:block;
        }
        ul.tags {
            list-style:none;
            padding:0;
        }
        span.timespan {
            font-size:85%;
            font-family:monospace;
        }
    </style>
    
</head>
<body id="summarizer" onload="">
HERE_HEADER
SUMMARIZER_FOOTER = <<-HERE_HEADER
</body>
</html>
HERE_HEADER

MIN_DURATION_WARN = 30
MIN_DURATION_ERROR = 60
MAX_GAP_ERROR = 0
MAX_GAP_WARN = 15

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
    
    def read_subdirectory_list(directory_name)
        result = Array.new
        directory_name = File.expand_path(directory_name)
        Dir.open(directory_name) { |dir|
            dir.each { |item|
                full_path = File.expand_path(directory_name + "/" + item)
                next if item.empty? || '.' == item[0]
                next if !File.directory?(full_path)
                result << item
            }
        }
        result.sort!
        result.reverse!
        return result
    end
    private :read_subdirectory_list    

    def needs_processing(input_file)
        summary_file = File.expand_path(input_file + "/summarizer.txt")
        index_file = File.expand_path(input_file + "/index.html")
        return true if !File.exists?(index_file)
        count_expected = -1
        count_actual = read_json_list(input_file).size
        count_actual = -2 if 0 == count_actual
        if File.exists?(summary_file)
            f = File.open(summary_file, "r")
            count_expected = f.readline().to_i
            f.close()
        end
        return count_actual != count_expected
    end
    
    def print_tag_list(f, tags, class_container, class_item, class_percent)
        f << "<div class=\"#{class_container}\"><ul class=\"tags tags_#{class_container}\">"
        if nil != tags
            tags.each_pair { |tag, percent|
                f << "<li>"
                f << "<span class=\"#{class_item}\">#{tag}</span>"
                f << "<span class=\"#{class_percent}\">(#{percent}%)</span>"
                f << "</li>"
            }
        end
        f << "</ul></div>"
    end
    
    def format_time(seconds, include_am_pm)
        return "err:err:err" if (nil == seconds) or (seconds < 0)
        hours = (seconds / 60 / 60).to_i
        seconds = seconds % (60 * 60)
        minutes = (seconds / 60).to_i
        seconds = seconds % 60
        ampm = 'am'
        if hours > 12
            ampm = 'pm'
            hours -= 12
        end
        result = sprintf("%d:%02d:%02d", hours, minutes, seconds)
        result += ampm if include_am_pm
        return result
    end
    
    def write_json_to_html(f, json_file_name)
        image_filename = File.basename(json_file_name.gsub(".json", ".gif"))
        video_filename = File.basename(json_file_name.gsub(".json", ".mp4"))
        data = JSON.parse(File.read(json_file_name))
        duration_extra = ''
        duration_extra = 'durationWarning' if data['duration'].to_i >= MIN_DURATION_WARN
        duration_extra = 'durationError' if data['duration'].to_i >= MIN_DURATION_ERROR
        summary_extra = ''
        summary_extra = 'summaryShort' if data['duration'].to_i < MIN_DURATION_WARN
        summary_extra = 'summaryLong' if data['duration'].to_i >= MIN_DURATION_ERROR
        gap_extra = ''
        gap_extra = 'gapWarning' if data['since'].to_i <= MAX_GAP_WARN
        gap_extra = 'gapError' if data['since'].to_i <= MAX_GAP_ERROR
        
        f << "<div class=\"summary #{summary_extra}\">"
        f << "<div class=\"thumbnail\">"
        f << "<a href=\"#{video_filename}\"><img src=\"#{image_filename}\" class=\"gif_thumbnail\" alt=\"animated thumbnail\"/></a>"
        if nil != data['since'] and data['since'] >= 0
            f << "<div class=\"gap #{gap_extra}\">Gap: #{format_time(data['since'], false)}</div>"
        else
            f << "<div class=\"gap gapWarning\">Gap: UNDEFINED</div>"
        end
        f << "<div class=\"duration #{duration_extra}\">#{format_time(data['duration'], false)}</div>"
        f << "<div class=\"filename\"><a href=\"#{video_filename}\">#{video_filename}</a><br /><span class=\"timespan\">#{format_time(data['time_start'], true)} &mdash; #{format_time(data['time_end'], true)}</span></div>"
        f << "</div>"
        flagged = data['flagged_tags']
        print_tag_list(f, flagged, 'flagged', 'flagged_tag', 'flagged_tag_percent')
        important = data['important_tags']
        print_tag_list(f, important, 'important', 'important_tag', 'important_tag_percent')
        f << "</div>\n\n"
    end
    private :write_json_to_html

    def write_directory_to_html(f, input_file, directory_name)
        size = `du -sh "#{input_file}/#{directory_name}" | sed 's/^ *//' | cut -f 1`
        parsed_name = directory_name
        if 8 == directory_name.length
            m = directory_name[4..5]
            d = directory_name[6..7]
            y = directory_name[0..3]
            dow = Time.new(y.to_i, m.to_i, d.to_i).strftime('%A')
            parsed_name = "#{dow} #{y}-#{m}-#{d}"
        end
        f << "<div class=\"subdirectory\">"
        f << "<a href=\"#{directory_name}/index.html\">#{parsed_name}</a> &mdash; #{size}"
        f << "</div>"
    end
    private :write_directory_to_html

    def write_screenshot(f, image_file)
        cmd = "screencapture -xt png \"#{image_file}\""
        system(cmd)
        f << "<p><a href=\"screen.png\"><img src=\"screen.png\" style=\"width:75%; display:block; margin:0 auto;\" /></a></p>"
    end
    private :write_screenshot

    def write_free_space(f)
        cmd = 'df -h /'
        output = `#{cmd}`
        f << "<pre>#{output}</pre>"
    end

    def callback(input_file)
        summary_file = File.expand_path(input_file + "/summarizer.txt")
        index_file = File.expand_path(input_file + "/index.html")
        print("Summarizing #{index_file}\n")
        f = File.open(index_file, "w")
        f << SUMMARIZER_HEADER
        write_count = 0
        subdirectories = read_subdirectory_list(input_file)
        subdirectories.each { |subdirectory|
            write_directory_to_html(f, input_file, subdirectory);
        }
        json_files = read_json_list(input_file)
        json_files.each { |json_file|
            write_json_to_html(f, json_file)
            write_count += 1
        }
        write_screenshot(f, File.expand_path(input_file + "/screen.png")) unless subdirectories.empty?
        f << SUMMARIZER_FOOTER
        f.close()
        f = File.open(summary_file, "w")
        f << write_count
        f.close()
    end
end
