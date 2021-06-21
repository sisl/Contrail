# Author: Ritchie Lee, ritchie.lee@sv.cmu.edu
# Date: 04/06/2015
#
# According to file format specified in Matlab script
# written by Mykel Kochenderfer, mykel@stanford.edu
#
# This script converts a json file produced by RLES and converts it to a "waypoints" file
# of the following format.
#
#   WAYPOINTS FILE:
#   The waypoints file contains a set of encounters. Each encounter is
#   defined by a set of waypoints associated with a fixed number of
#   aircraft. The waypoints are positions in space according to a fixed,
#   global coordinate system. All distances are in feet. Time is specified
#   in seconds since the beginning of the encounter. The file is organized
#   as follows:
#
#   [Header]
#   uint32 (number of encounters)
#   uint32 (number of aircraft)
#       [Encounter 1]
#           [Initial positions]
#               [Aircraft 1]
#               double (north position in feet)
#               double (east position in feet)
#               double (altitude in feet)
#               ...
#               [Aircraft n]
#               double (north position in feet)
#               double (east position in feet)
#               double (altitude in feet)
#           [Updates]
#               [Aircraft 1]
#               uint16 (number of updates)
#                   [Update 1]
#                   double (time in seconds)
#                   double (north position in feet)
#                   double (east position in feet)
#                   double (altitude in feet)
#                   ...
#                   [Update m]
#                   double (time in seconds)
#                   double (north position in feet)
#                   double (east position in feet)
#                   double (altitude in feet)
#               ...
#               [Aircraft n]
#                   ...
#       ...
#       [Encounter k]

include("corr_aem_save_scripts.jl")

using JSON
using Base.Test

json_to_waypoints_batch{T<:String}(filenames::Vector{T}) = pmap(f -> json_to_waypoints(f), filenames)

json_to_waypoints(filename::String) = json_to_waypoints([filename], outfile = string(splitext(filename)[1], "_waypoints.dat"))

function json_to_waypoints{T<:String}(filenames::Vector{T}; outfile::String = "waypoints.dat")

  d = trajLoad(filenames[1]) #use the first one as a reference
  number_of_aircraft = length(d["sim_log"]["wm"]["aircraft"]) #read from wm log
  number_of_encounters = length(filenames) #one encounter per json file
  encounters = Array(Dict{String, Array{Float64, 2}}, number_of_aircraft, number_of_encounters)

  #encounter i
  for (i, file) in enumerate(filenames)

    d = trajLoad(file)

    #make sure all of them have the same number of aircraft
    @test number_of_aircraft == length(d["sim_log"]["wm"]["aircraft"])

    #aircraft j
    for j = 1 : number_of_aircraft
      encounters[j, i] = Dict{String, Array{Float64, 2}}()
      encounters[j, i]["initial"] = get_initial(d, j)
      encounters[j, i]["update"] = get_update(d, j)'
    end
  end

  save_waypoints(outfile, encounters, numupdatetype = Uint16)

  return encounters
end

function get_initial(d::Dict{String,Any}, aircraft_number::Int64)
  #d is the loaded json / encounter

  wm_names = d["sim_log"]["var_names"]["wm"]
  wm = d["sim_log"]["wm"]["aircraft"]["$(aircraft_number)"]["time"]["1"]
  out = Array(Float64, 1, 3)

  pos_east = wm[findfirst(x -> x == "x", wm_names)]
  pos_north = wm[findfirst(x -> x == "y", wm_names)]
  altitude = wm[findfirst(x -> x == "z", wm_names)]

  out[1, :] = [pos_north, pos_east, altitude]

  return out
end

function get_update(d::Dict{String, Any}, aircraft_number::Int64)
  #d is the loaded json / encounter,
  #j is aircraft number

  wm_names = d["sim_log"]["var_names"]["wm"]
  wm = d["sim_log"]["wm"]["aircraft"]["$(aircraft_number)"]["time"]
  t_end = length(wm)
  out = Array(Float64, t_end - 1, 4)

  for t = 2 : t_end #ignore init values
    t_ = wm["$t"][findfirst(x -> x == "t", wm_names)]
    pos_east = wm["$t"][findfirst(x -> x == "x", wm_names)]
    pos_north = wm["$t"][findfirst(x -> x == "y", wm_names)]
    altitude = wm["$t"][findfirst(x -> x == "z", wm_names)]

    out[t - 1, :] = Float64[t_, pos_north, pos_east, altitude]
  end

  return out
end

