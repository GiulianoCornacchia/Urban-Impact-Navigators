import warnings
warnings.filterwarnings("ignore")  # Ignore warnings for cleaner output

import numpy as np
import os
import json
from utils_mobility_demand import create_mixed_route_demands, create_mixed_route_demands_interplay, load_route_file_in_dict
import time
import subprocess
import pandas as pd
from collections import defaultdict
import shutil
import multiprocessing
from routing_measures import redundancy, distinct_edges_traveled
import argparse

def split_list(input_list, chunk_size):
    """
    Split a list into smaller chunks of a specified size.
    
    Args:
    input_list (list): List to be split.
    chunk_size (int): Size of each chunk.
    
    Returns:
    list of lists: List containing the chunks.
    """
    return [input_list[i:i + chunk_size] for i in range(0, len(input_list), chunk_size)]

def compute_measures_route(route, shared_list):
    """
    Compute redundancy and the number of distinct edges traveled for a given route.
    
    Args:
    route (str): Path to the route file.
    shared_list (list): Shared list to store the results.
    """
    pct = int(route.split("/")[-1].split("_")[1])
    n_rep = int(route.split("/")[-1].split("_")[-1].split(".")[0])
    
    dict_route = load_route_file_in_dict(route)
    path_list = [dict_route[k]["edges"] for k in dict_route]
    
    # Calculate redundancy and distinct traveled edges
    red = redundancy(path_list)
    n_edges = len(distinct_edges_traveled(path_list))

    # Append results to the shared list
    shared_list.append({"pct": pct, "n_rep": n_rep, "red": red, "n_edges": n_edges})

# Parse command-line arguments
parser = argparse.ArgumentParser()

# Adding required arguments
parser.add_argument('-c', '--city', type=str, required=True, help="City name")
parser.add_argument('-v', '--n-vehicles', type=int, required=True, help="Number of vehicles")
parser.add_argument('-b', '--base', type=str, required=True, help="Base name")
parser.add_argument('-n', '--navigator', type=str, required=True, help="Navigator name")
parser.add_argument('-g', '--road-network', type=str, required=True, help="Road network file")

# Adding optional arguments
parser.add_argument('--path-base', type=str, required=True, help="Route file for non-routed (base) vehicles")
parser.add_argument('--path-navigator', type=str, required=True, help="Route file for routed (navigator) demands")
parser.add_argument('--path-vehicles-mapping', type=str, required=True, help="Path for vehicles mapping intro routed and non-routed")
parser.add_argument('--list-pct', type=str, default="", help="List of adoption rates")
parser.add_argument('-o', type=str, default="../data/sim_output/", help="Output folder")
parser.add_argument('-z', '--zipped', type=int, default=0, help="Zipped option")
parser.add_argument('--rep-min', type=int, default=0, help="Minimum repetition")
parser.add_argument('--rep-max', type=int, default=9, help="Maximum repetition")
parser.add_argument('--njobs', type=int, default=20, help="Number of parallel jobs")

# Parse arguments
args = parser.parse_args()

# Extract argument values
city = args.city
n_vehicles = args.n_vehicles
non_routed = args.base
navigator = args.navigator
n_rep_min = args.rep_min
n_rep_max = args.rep_max

# Set percentages
if args.list_pct == "":
    percentages = list(np.arange(0, 101, 10))
else:
    percentages = [int(n) for n in args.list_pct.split("-")]

njobs = args.njobs

demand_name_result = f"N{n_vehicles}_{navigator}_{non_routed}"
sim_id = demand_name_result
suffix_ext = ".gz" if args.zipped == 1 else ""
path_demand_base = args.path_base
path_demand_navigator = args.path_navigator
path_dict_set = args.path_vehicles_mapping
output_folder_MRP = f"../data/{city}/tmp_mixed_routed_paths_{demand_name_result}/"
folder_out = args.o
output_simulations = f"{folder_out}{city}/{demand_name_result}/"

# Create output directories if they don't exist
os.makedirs(output_simulations, exist_ok=True)

# Road network path
road_net = args.road_network

# SUMO simulation options
sumo_opt = '"--tls.actuated.jam-threshold 30 --ignore-junction-blocker 5 --time-to-impatience 20 --time-to-teleport 120"'

# Create the mixed routed demands (MRD)
if navigator == "interplay":
    print("Interplay")

    list_navs_interplay = ["gmaps", "tomtomFastest", "mapbox", "bing"]
    path_folder_routed_navs = f"../data/{city}/routed_paths/N{n_vehicles}/routed_paths_{city}_N{n_vehicles}_"
    
    list_process = []
    for pct in percentages:
        process = multiprocessing.Process(
            target=create_mixed_route_demands_interplay, 
            args=(navigator, list_navs_interplay, path_demand_base, path_folder_routed_navs, 
                  path_dict_set, output_folder_MRP, n_rep_min, n_rep_max, [pct], True, True)
        )
        list_process.append(process)
    for process in list_process:
        process.start()
    for process in list_process:
        process.join()
else:
    print("Standard Navigator")
    if njobs >= len(percentages):
        list_process = []
        for pct in percentages:
            process = multiprocessing.Process(
                target=create_mixed_route_demands, 
                args=(navigator, path_demand_base, path_demand_navigator, path_dict_set, 
                      output_folder_MRP, n_rep_min, n_rep_max, [pct], True, True)
            )
            list_process.append(process)
        for process in list_process:
            process.start()
        for process in list_process:
            process.join()
    else:
        create_mixed_route_demands(navigator, path_demand_base, path_demand_navigator, path_dict_set, 
                                   output_folder_MRP, n_rep_min=n_rep_min, n_rep_max=n_rep_max, 
                                   percentages=percentages, lane_best=True, compress=True)

# Simulate the MRP using SUMO
routes_list = [output_folder_MRP + f for f in os.listdir(output_folder_MRP) if "rou.xml" in f]
print(f"There are {len(routes_list)} mixed routed paths (MRP) to simulate.")

# Create the route chunks
chunk_size = njobs
routes_chunks = split_list(routes_list, chunk_size)

# Record the start time
start_time = time.time()

for routes_to_simulate in routes_chunks:
    processes = []
    for route_file in routes_to_simulate:
        s = f"-n {road_net} -r {route_file} -i {sim_id + '_'} -o {output_simulations}"
        command_list = ['python', "launcher_sumo_simulation.py"] + s.split(" ") + ["--sumo-opt", sumo_opt.replace('"', "")]
        script = subprocess.Popen(command_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(script)
    for process in processes:
        process.wait()

# Record the end time
end_time = time.time()

# Calculate the elapsed time
elapsed_time = end_time - start_time
print("Elapsed Time:", elapsed_time, "seconds")

# Compute measures on the MRP
output_folder_route_measures = f"../data/route_measures/{city}/{navigator}_{demand_name_result}/"
os.makedirs(output_folder_route_measures, exist_ok=True)

# Shared list to store results
manager = multiprocessing.Manager()
result_list = manager.list()

routes_chunks = split_list(routes_list, chunk_size)

for routes_to_simulate in routes_chunks:
    list_process = []
    for route in routes_to_simulate:
        process = multiprocessing.Process(target=compute_measures_route, args=(route, result_list))
        list_process.append(process)
    for process in list_process:
        process.start()
    for process in list_process:
        process.join()

# Process the results
result_list = list(result_list)
dict_measures_routes = {int(pct): {} for pct in percentages}

for elem in result_list:
    pct = int(elem["pct"])
    n_rep = int(elem["n_rep"])
    red = elem["red"]
    n_edges = elem["n_edges"]

    dict_measures_routes[pct][n_rep] = {"redundancy": red, "n_edges": n_edges}

# Save results to JSON file
with open(f"{output_folder_route_measures}route_measures_{n_rep_min}_{n_rep_max}.json", 'w') as json_file:
    json.dump(dict_measures_routes, json_file)

# Delete the non-necessary files (MRPs)
shutil.rmtree(output_folder_MRP)
