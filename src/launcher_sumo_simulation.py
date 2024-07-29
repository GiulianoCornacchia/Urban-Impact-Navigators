import subprocess
import xml
import os
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import numpy as np
import time
import json
import argparse
import shutil



def create_additional_file_emissions(emissions_filename, output_filename):

    # Create the root element
    root = ET.Element("additional")

    # Create the edgeData element with attributes
    edge_data = ET.SubElement(root, "edgeData")
    edge_data.set("id", "EMISSIONS")
    edge_data.set("type", "emissions")
    edge_data.set("withInternal", "true")
    edge_data.set("file", emissions_filename)
    edge_data.set("excludeEmpty", "true")

    # Create the XML tree
    tree = ET.ElementTree(root)

    # Save the XML tree to a file
    tree.write(output_filename)

    
def convert_xml_to_csv(xml_filename, csv_filename):
    """Convert XML output to CSV."""
    command = ["python", script_xml_csv, xml_filename,"-o", csv_filename]
    
    script = subprocess.Popen(command, cwd=".")
    script.wait()
    
    
def create_sim_id(rand_int=False):

    now = datetime.now()
    dt_string = now.strftime("%d_%m_%H_%M_%S")
    
    if rand_int:
        return f"{dt_string}_{str(np.random.randint(0, 1e7))}"
    else:
        return dt_string



# Parse the arguments

parser = argparse.ArgumentParser()

# network and route file
parser.add_argument('-n', '--net-file', required=True)
parser.add_argument('-r', '--route-file', required=True)

# experiment info
parser.add_argument('-i', '--exp-id', required=True)
parser.add_argument('-o', '--output-dir', required=True)

# output
parser.add_argument('--edges-info', type=int, default=1)
parser.add_argument('--trips-info', type=int, default=1)
parser.add_argument('--log', type=int, default=1)


# sim info
parser.add_argument('--gui', type=int, default=0)
parser.add_argument('--sumo-opt', default="")


args = parser.parse_args()


# path to the xml2csv.py script
path_sumo = shutil.which("sumo").replace("\\","/")

script_xml_csv = "./xml2csv.py"


# Parameters
net_file = args.net_file
route_file = args.route_file
experiment_id = args.exp_id
results_folder = args.output_dir

output_edges = True if int(args.edges_info) == 1 else False
output_trips = True if int(args.trips_info) == 1 else False
output_log = True if int(args.log) == 1 else False

use_gui = True if int(args.gui) == 1 else False

sumo_opt = args.sumo_opt



# Create a simulation identifier
simulation_id = f"{experiment_id}{create_sim_id(rand_int=True)}"


# create a folder in the output directory with a name equal to the simulation id
output_folder = results_folder+simulation_id+"/"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)


print("TraffiCO2 version 3.0")
print("\nSimulation id: "+simulation_id)
print("\nParameters: \n")
print("Network file:",net_file)
print("Route file:",route_file)
print("SUMO options: "+str(sumo_opt))
print("Output Directory:",output_folder)
print("Collect measures edges:",output_edges)
print("Collect measures trips:",output_trips)
print("Create log:",output_log)
print("<><><><><>") 

    

# Output Filenames
emissions_filename = f"{output_folder}edge_emissions.xml"
trip_info_filename = f"{output_folder}trips_info.xml"
add_file_filename = f"./add_{simulation_id}.xml"
stats_filename = f"{output_folder}simulation_info.xml"
log_filename = f"{output_folder}log.json"


# Create additional file for the emissions
if output_edges:
    create_additional_file_emissions(emissions_filename, add_file_filename)


# Launch the SUMO simulation

opt_measures = ""

if output_edges:
    opt_measures += f"-a {add_file_filename}"
    
if output_trips:
    opt_measures += f" --device.emissions.probability 1 --tripinfo-output {trip_info_filename}"
    
if output_log:   
    opt_measures += f" --statistic-output {stats_filename}"
    
opt_measures+=f" {sumo_opt}"


# Run command
if use_gui:
    command_sumo = f"sumo-gui -n {net_file} -r {route_file} -W {opt_measures}".split(" ")
else:
    command_sumo = f"sumo -n {net_file} -r {route_file} -W {opt_measures}".split(" ")
    
script = subprocess.Popen(command_sumo, cwd=".")   
    
    
print("Simulation started.")
script.wait()
print("Simulation ended!")



# Convert XML to CSV

# Edge Emissions

if output_edges:
    
    convert_xml_to_csv(emissions_filename, emissions_filename.replace(".xml", ".csv"))
    df = pd.read_csv(emissions_filename.replace(".xml", ".csv"), sep=";")

    ''' uncomment to save all the info about the edges
    df_edge = df[["edge_id", "edge_CO2_abs", "edge_CO_abs", 
                  "edge_HC_abs", "edge_NOx_abs", "edge_PMx_abs",
                  "edge_fuel_abs", "edge_traveltime"]]
    '''
    
    # added to save disk space
    df_edge = df[["edge_id", "edge_CO2_abs", "edge_traveltime"]]

    df_edge.to_csv(emissions_filename.replace(".xml", ".csv.gz"), compression='zip', index=False)
    
    # Remove unnecessary files
    # Emissions
    os.remove(emissions_filename)
    os.remove(emissions_filename.replace(".xml", ".csv"))
    
    # Additional File for emissions
    os.remove(add_file_filename)
    




# Trip Info
if output_trips:
    
    convert_xml_to_csv(trip_info_filename, trip_info_filename.replace(".xml", ".csv"))
    df = pd.read_csv(trip_info_filename.replace(".xml", ".csv"), sep=";")

    ''' uncomment to save all the info about the trips
    df_trips = df[["tripinfo_id", "tripinfo_duration", "tripinfo_routeLength", "tripinfo_stopTime", 
        "tripinfo_timeLoss", "tripinfo_waitingCount", "tripinfo_waitingTime", 'emissions_CO2_abs', 
                   'emissions_CO_abs', 'emissions_HC_abs','emissions_NOx_abs', 'emissions_PMx_abs', 
                   'emissions_electricity_abs','emissions_fuel_abs']]
    '''

    # added to save disk space
    df_trips = df[["tripinfo_id", "tripinfo_duration", "tripinfo_routeLength", "tripinfo_stopTime", 
        "tripinfo_timeLoss", "tripinfo_waitingCount", "tripinfo_waitingTime", 'emissions_CO2_abs']]
    
    
    df_trips.to_csv(trip_info_filename.replace(".xml", ".csv.gz"), compression='zip', index=False)
    total_co2_mg = df_trips["emissions_CO2_abs"].sum()

    print(f"Total CO2 (mg): {total_co2_mg}")
    print(f"Total CO2 (tons): {total_co2_mg/1e9}")
    
    # Trips
    os.remove(trip_info_filename)
    os.remove(trip_info_filename.replace(".xml", ".csv"))


if output_log:
    # Log File
    # Parse the XML file for the statistics
    tree = ET.parse(stats_filename)
    root = tree.getroot()


    dict_log = {}
    dict_log["id"] = simulation_id
    dict_log["net_filename"] = net_file
    dict_log["route_filename"] = route_file
    dict_log["total_co2"] = total_co2_mg

    # Execute the SUMO command to get the version
    command_output = subprocess.check_output(["sumo", "--version"]).decode("utf-8")
    sumo_version = command_output.splitlines()[0].split()[-1]
    dict_log["sumo_version"] = sumo_version

    tags_to_include = ["performance", "vehicles", "teleports", "safety", "vehicleTripStatistics"]

    for tag in tags_to_include:
        elements = root.findall(f'.//{tag}')
        dict_log[tag] = elements[0].attrib

    # Write the dictionary to a JSON file
    with open(log_filename, 'w') as json_file:
        json.dump(dict_log, json_file)

    os.remove(stats_filename)




