import warnings
warnings.filterwarnings("ignore")

import sumolib
import json
import numpy as np

import gzip

from routing_utils import from_sumo_to_igraph_network, get_shortest_path_nodes
from tqdm import tqdm

import os
import argparse


def save_dict_to_gzipped_json(data, filename):
    with gzip.open(filename, 'wt') as gzipped_file:
        json.dump(data, gzipped_file)

def load_dict_from_gzipped_json(filename):
    with gzip.open(filename, 'rt') as gzipped_file:
        data = json.load(gzipped_file)
    return data


def apply_randomization_my_duarouter(G, w, default_attribute="", tmp_attribute=""):
    """
    Apply random noise to the edge weights of a graph.

    Args:
    - G: The graph object.
    - w: The randomization factor for the random noise.
    - default_attribute: The name of the default edge attribute representing the original edge weights (optional).
    - tmp_attribute: The name of the temporary edge attribute to store the distorted edge weights (optional).

    Returns:
    None
    """

    # Get the list of edges in the graph
    edge_list = G.es()
    
    # Apply random noise to each edge weight
    rand_noise_list = np.random.uniform(1, w, size=len(edge_list))
    for ind, e in enumerate(edge_list):
        # Check if the edge is not a "connection" (optional)
        if e["id"] != "connection":
            # Apply the random noise to the edge weight
            e[tmp_attribute] = e[default_attribute] * rand_noise_list[ind]

            
            


# ARGUMENTS

parser = argparse.ArgumentParser()

# network and route file
parser.add_argument('-c', '--city', type=str, required=True)
parser.add_argument('-N', type=int, required=True)
parser.add_argument('-w', type=int, required=True)
parser.add_argument('--road-file', type=str, required=True)
parser.add_argument('-d', '--demand-file', type=str, required=True)
parser.add_argument('--ind-from', type=int, required=True)
parser.add_argument('--ind-to', type=int, required=True)
parser.add_argument('--seed', type=int, default=-1)


args = parser.parse_args()

city = args.city

N_max = args.N

w = args.w

ind_from = args.ind_from
ind_to = args.ind_to

path_dict_mobility_demand = args.demand_file
road_network_path = args.road_file

attribute = "traveltime"

if args.seed > 0:
    random_seed = args.seed
else:
    random_seed = None



result_folder = f"../data/{city}/mydua_tmp/tmp_mydua_w{str(w).replace('.','p')}/"
# create the result folder (if it doesn't exist)
if not os.path.exists(result_folder):
    os.makedirs(result_folder)


# ### Load the road network

# Read the road network from a file using SUMO library
road_network = sumolib.net.readNet(road_network_path, withInternal=False)

# Convert the road network to an igraph representation
G = from_sumo_to_igraph_network(road_network)


# Load the Mobility Demand 
# It defines the trips, i.e., the origin and destination nodes
with open(path_dict_mobility_demand, 'r') as f:
    dict_demand = json.load(f)["demand"]


# Apply MYDUA
dict_path_mydua = {}

# traveltime
default_attribute = attribute
# tmp traveltime
tmp_attribute = f"tmp_{attribute}"

# Copy the tmp attribute
G.es[tmp_attribute] = G.es[default_attribute] 

for vid in tqdm(np.arange(ind_from, ind_to)):
    
    # Retrieve the source and destination nodes for the current vehicle from the demand dictionary
    from_node, to_node = dict_demand[f"vehicle_{vid}"]["element"]
    
    if random_seed is not None:
        hash_value = hash((random_seed, vid)) % 2**32
        np.random.seed(hash_value)
    
    # Apply random distortion to the edge weights of the graph using the specified parameters
    apply_randomization_my_duarouter(G, w, default_attribute=default_attribute, tmp_attribute=tmp_attribute)
    
    # Compute the shortest path using the distorted edge weights and store the result
    path_mydua_w = get_shortest_path_nodes(G, from_node, to_node, tmp_attribute)["sumo"]
    
    # Store the computed path for the current vehicle in the dictionary
    dict_path_mydua[int(vid)] = path_mydua_w

    
result_filename = result_folder+f"paths_mydua_{city}_N{N_max}_w{str(w).replace('.','p')}_{ind_from}_{ind_to}.json.gz"
save_dict_to_gzipped_json(dict_path_mydua, result_filename)



