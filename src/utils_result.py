import os
import json
import gzip
import numpy as np
from collections import defaultdict
import pandas as pd
from tqdm.notebook import tqdm
from multiprocessing import Pool
from scipy.stats import entropy
import sumolib
from datetime import datetime


def get_formatted_date():
    # Get current date
    today = datetime.today()
    
    # Format the date as "dd_mon_yyyy"
    formatted_date = today.strftime("%d_%b_%Y").lower()
    
    return formatted_date



def save_dict_to_gzipped_json(data, filename):
    with gzip.open(filename, 'wt') as gzipped_file:
        json.dump(data, gzipped_file)

def load_dict_from_gzipped_json(filename):
    with gzip.open(filename, 'rt') as gzipped_file:
        data = json.load(gzipped_file)
    return data

def pct_and_rep_from_sim_info(f):
    
    with open(f, 'r') as file:
        data = json.load(file)
        pct = int(data["route_filename"].split("/")[-1].split("_")[1])
        rep = int(data["route_filename"].split("/")[-1].split("_")[5].split(".")[0])
        
    return pct, rep


def compute_measures_parallel(city, list_navigators, list_bases, list_N, list_pct, road_network_edge_list, folder_output_results):
    pool = Pool()  # Create a pool of processes
    for navigator in list_navigators:
        for base in list_bases:
            pool.apply_async(process_and_save, args=(city, navigator, base, list_N, list_pct, road_network_edge_list, folder_output_results))
    pool.close()
    pool.join()


def process_and_save(city, navigator, base, list_N, list_pct, road_network_edge_list, folder_output_results, save=True, return_dict=False, sim_output_folder="../data/sim_output/"):

    
    # Define a lambda function that returns a defaultdict with default value of list
    leaf_default_factory = lambda: defaultdict(list)


    # Create a nested defaultdict with default value of defaultdict(list)
    dict_result_nav_exp = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(leaf_default_factory))))

    for N in list_N:
        # Load the info about MRP
        path_dict_rc = f"../data/route_measures/{city}/{navigator}_N{N}_{navigator}_{base}/"
        list_filename_rc_json = [path_dict_rc+f for f in os.listdir(path_dict_rc) if ".json" in f]
        list_filename_rc_json_sorted = sorted(list_filename_rc_json)
        filename_rc_json = list_filename_rc_json_sorted[-1]
        
        with open(filename_rc_json, 'r') as file:
            data_info_routes = json.load(file)
        
        # sim_outputs_folder
        sim_outputs_folder = f"{sim_output_folder}{city}/N{N}_{navigator}_{base}/"
        output_folders_list = [sim_outputs_folder+f for f in os.listdir(sim_outputs_folder) if ".ipynb" not in f]

        #print(city, navigator, base, len(output_folders_list))

        for output_folder in output_folders_list:
            # retrieve the routed percentage and number of rep
            pct, rep = pct_and_rep_from_sim_info(output_folder+"/log.json")

            if pct in list_pct:

                # info trips
                df_trips = pd.read_csv(f"{output_folder}/trips_info.csv.gz", compression="zip")
    
                # info simulation
                with open(f"{output_folder}/log.json", 'r') as file:
                    data_log = json.load(file)
    
                # total CO2 emissions
                total_co2 = df_trips["emissions_CO2_abs"].sum()
                dict_result_nav_exp[navigator][base][N]["total_co2"][pct].append(total_co2)

                # total CO2 emission routed vehicles
                df_routed_trips = df_trips[~df_trips["tripinfo_id"].str.contains("duarouter", na=False)]#["emissions_CO2_abs"].sum()
                if len(df_routed_trips) > 0:
                    total_co2_routed = df_routed_trips["emissions_CO2_abs"].sum()
                else:
                    total_co2_routed = 0

                dict_result_nav_exp[navigator][base][N]["total_co2_routed"][pct].append(total_co2_routed)
        

                # total CO2 emission NON-routed vehicles
                df_non_routed_trips = df_trips[df_trips["tripinfo_id"].str.contains("duarouter", na=False)]
                if len(df_non_routed_trips["emissions_CO2_abs"])>0:
                    total_co2_non_routed = df_non_routed_trips["emissions_CO2_abs"].sum()
                else:
                    total_co2_non_routed = 0

                dict_result_nav_exp[navigator][base][N]["total_co2_non_routed"][pct].append(total_co2_non_routed)
                
                #assert int(total_co2) == int(total_co2_routed + total_co2_non_routed), "Error sum total CO2 routed vs. non-routed"

                
                # The time the vehicle needed to accomplish the route (i.e., traveltime)
                total_duration = df_trips["tripinfo_duration"].sum()
                dict_result_nav_exp[navigator][base][N]["total_duration"][pct].append(total_duration)
    
                # The time in which the vehicle speed was below or equal 0.1 m/s
                total_waiting_time = df_trips["tripinfo_waitingTime"].sum()
                dict_result_nav_exp[navigator][base][N]["total_waiting_time"][pct].append(total_waiting_time)
    
                # Total number of teleports
                total_teleports = data_log["teleports"]["total"]
                dict_result_nav_exp[navigator][base][N]["total_teleports"][pct].append(int(total_teleports))


                # Entropy CO2 emissions edges
                df_edges = pd.read_csv(f"{output_folder}/edge_emissions.csv.gz", compression="zip")
                df_edges["is_internal"] = df_edges["edge_id"].apply(lambda x: x[0]==":")
                
                df_edges_co2 = df_edges[df_edges["is_internal"]==False]
                vector_edge_co2 = df_edges_co2["edge_CO2_abs"].values
                
                ent = entropy(vector_edge_co2)
                max_entropy = np.log(len(vector_edge_co2))
                norm_entropy = ent / max_entropy

                dict_result_nav_exp[navigator][base][N]["edge_co2_entropy"][pct].append(ent)
                dict_result_nav_exp[navigator][base][N]["NORM_edge_co2_entropy"][pct].append(norm_entropy)

                # Entropy CO2 emissions all edges (also the ones with 0 emissions)
                dict_edge_to_co2 = {eid:co2 for eid, co2 in zip(df_edges_co2["edge_id"], df_edges_co2["edge_CO2_abs"])}
                vector_edge_co2 = [dict_edge_to_co2.get(edge_id, 0) for edge_id in road_network_edge_list]
                ent = entropy(vector_edge_co2)
                max_entropy = np.log(len(vector_edge_co2))
                norm_entropy = ent / max_entropy

                dict_result_nav_exp[navigator][base][N]["all_edge_co2_entropy"][pct].append(ent)
                dict_result_nav_exp[navigator][base][N]["NORM_all_edge_co2_entropy"][pct].append(norm_entropy)
                
                
    
                # traveled edges
                try:
                    traveled_edges = data_info_routes[str(pct)][str(rep)]["n_edges"]
                    dict_result_nav_exp[navigator][base][N]["traveled_edges"][pct].append(traveled_edges)
                except:
                    print(navigator, base, N, pct, rep)
                    return 
                # redundancy
                redundancy = data_info_routes[str(pct)][str(rep)]["redundancy"]
                dict_result_nav_exp[navigator][base][N]["redundancy"][pct].append(redundancy)

    # Save the dictionary
    if save:
        print(f"SAVING results_{city}_{navigator}_{base}...")
        save_dict_to_gzipped_json(dict_result_nav_exp, f"{folder_output_results}/results_{city}_{navigator}_{base}.json.gz")
        
    if return_dict:
        return dict_result_nav_exp





def merge_navigator_results(city, list_navigators, list_bases, list_N, list_adoption_rates, folder_output_results):
    """
    Merges results from different navigators and bases into a single dictionary and saves it as a gzipped JSON file.

    Args:
    city (str): Name of the city.
    list_navigators (list): List of navigators.
    list_bases (list): List of bases.
    list_N (list): List of vehicle counts.
    list_adoption_rates (list): List of adoption rates.
    folder_output_results (str): Folder path to save the output results.

    Returns:
    None
    """
    list_bases_merge = list_bases
    dict_merged_results = {}

    for navigator in list_navigators:
        dict_merged_results[navigator] = {}
        for base in list_bases_merge:
            path_dict_result = os.path.join(folder_output_results, f"results_{city}_{navigator}_{base}.json.gz")
            dict_tmp = load_dict_from_gzipped_json(path_dict_result)
            
            # TESTS
            # N vehicles
            if navigator != "interplay":
                assert set(int(n) for n in dict_tmp[navigator][base].keys()) == set(list_N), f"ERROR N vehicles {navigator} - {base}"

            for tmp_N in dict_tmp[navigator][base]:
                for tmp_measure in dict_tmp[navigator][base][tmp_N]:
                    assert set(int(n) for n in dict_tmp[navigator][base][tmp_N][tmp_measure]) == set(list_adoption_rates), f"ERROR % {navigator} - {base}"

            dict_merged_results[navigator].update(dict_tmp[navigator])

    str_date = get_formatted_date()
    save_dict_to_gzipped_json(dict_merged_results, f"{folder_output_results}/results_{city}_navigators_{str_date}.json.gz")

    print("done!")
    print(dict_merged_results.keys())