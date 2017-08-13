#!/usr/bin/env ruby

class Callback
    def initialize()
    end
    def callback(input_file)
    end
end

class Scanner
    def initialize(directory, input_extension, callback_list)
        @directory = File.expand_path(directory)
        @input_extension = input_extension
        @callback_list = Array.new
        @callback_list.push(callback_list)
        @callback_list.flatten!
    end

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
                @callback_list.each { |obj|
                    obj.callback(full_path)
                }
            }
        }
    end
    private :scan_dir
end

