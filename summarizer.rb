#!/usr/bin/env ruby

require './scanner'

class Summarizer < DirectoryCallback
    def initialize()
        super()
    end
    
    def needs_processing(input_file)
        print("Summarizer needs_processing called for #{input_file}\n")
        return true
    end

    def callback(input_file)
        print("Summarizer callback called for #{input_file}\n")
    end
end
