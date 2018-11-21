#!/usr/bin/env ruby

class Metadata
    
    # Filenames are of the format `Garage-013843-013900.mp4`.
    # Return value is a hash of the format:
    #  :time_start => seconds in the day (0=midnight)
    #  :time_end   => seconds in the day (0=midnight)
    #  :duration   => seconds duration
    def Metadata.extract_times(filename)
        result = {}
        filename = File.basename(filename)
        matches = /-([0-9][0-9])([0-9][0-9])([0-9][0-9])-/.match(filename)
        if 4 == matches.length
            hours = matches[1].to_i
            minutes = matches[2].to_i
            seconds = matches[3].to_i
            value = hours * 60 * 60 + minutes * 60 + seconds
            result[:time_start] = value
        else
            result[:time_start] = -1
        end
        matches = /-([0-9][0-9])([0-9][0-9])([0-9][0-9])\./.match(filename)
        if 4 == matches.length
            hours = matches[1].to_i
            minutes = matches[2].to_i
            seconds = matches[3].to_i
            value = hours * 60 * 60 + minutes * 60 + seconds
            result[:time_end] = value
        else
            result[:time_end] = -1
        end
        if -1 != result[:time_start] and -1 != result[:time_end]
            duration = result[:time_end] - result[:time_start]
            if duration < 0 # time_end crossed into the next day? Not sure this is even possible.
                duration += 60 * 60 * 24
            end
            result[:duration] = duration
        else
            result[:duration] = -1
        end
        return result
    end

end
