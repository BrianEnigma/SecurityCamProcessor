#!/usr/bin/env ruby

class Mover
    def initialize(input_folder, output_folder, stabilize_delay)
        @input_folder = File.expand_path(input_folder)
        @output_folder = File.expand_path(output_folder)
        @stabilize_delay = stabilize_delay
        @file_sizes = {}
    end
    
    def move()
        Dir.foreach(@input_folder) { |filename|
            puts "Scanning #{filename}"
            path = "#{@input_folder}/#{filename}"
            scan_subfolder(filename) if File.directory?(path) and not filename.start_with?('.')
        }
        sleep(@stabilize_delay)
        Dir.foreach(@input_folder) { |filename|
            puts "Rescanning #{filename}"
            path = "#{@input_folder}/#{filename}"
            scan_subfolder_move(filename) if File.directory?(path) and not filename.start_with?('.')
        }
    end
    
    def scan_subfolder(folder)
        path = "#{@input_folder}/#{folder}"
        puts "Scanning Subfolder #{path}"
        Dir.foreach(path) { |filename|
            filename = File.expand_path("#{@input_folder}/#{folder}/#{filename}")
            next if not filename.end_with?('.mp4')
            if File.file?(filename)
                @file_sizes[filename] = File.size(filename)
            end
        }
    end
    
    def date_transform(date_string)
        if date_string.length == 8
            #
            # MMDDYYYY
            # 01234567
            result = ''
            result += date_string[4..7]
            result += date_string[0..3]
        else
            return date_string
        end
    end
    
    def scan_subfolder_move(folder)
        path = "#{@input_folder}/#{folder}"
        puts "Re-Scanning Subfolder #{path}"
        Dir.foreach(path) { |filename|
            src = File.expand_path("#{@input_folder}/#{folder}/#{filename}")
            next if not src.end_with?('.mp4')
            puts "Checking for stable size of #{folder}/#{filename}"
            if File.file?(src) and @file_sizes[src] == File.size(src)
                puts "File is of stable size and can be moved and remuxed."
                dst = File.expand_path("#{@output_folder}/#{date_transform(folder)}/#{filename}")
                begin
                    Dir.mkdir(File.expand_path("#{@output_folder}/#{date_transform(folder)}"))
                rescue
                end
                remux_move(src, dst)
            end
        }
    end
    
    def remux_move(in_filename, out_filename)
        cmd = "ffmpeg -i \"#{in_filename}\" -vcodec copy -acodec copy -y \"#{out_filename}\""
        if system(cmd)
            File.unlink(in_filename)
        else
            puts "Error remuxing \"#{in_filename}\" to \"#{out_filename}\""
        end
    end
end
