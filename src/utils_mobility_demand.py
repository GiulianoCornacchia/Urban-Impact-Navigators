import warnings
warnings.filterwarnings("ignore")

import skmob
import numpy as np
import pandas as pd
import geopandas as gpd
import sumolib
from tqdm.notebook import tqdm
#from routing_utils import from_sumo_to_igraph_network, get_shortest_path
from math import sqrt, sin, cos, pi, asin
import xml
from xml.dom import minidom
from itertools import groupby
from skmob.measures.evaluation import common_part_of_commuters
from scipy.stats import pearsonr
import subprocess
import re
import os
import json

''' USED FUNCTIONS

create_mixed_route_demands
create_mixed_route_demands_interplay
load_route_file_in_dict

'''

def create_dict_tile_edges(road_network, tessellation, exclude_roundabouts=False):
    
    lng_list, lat_list, edge_id_list = [], [], []

    edges_in_roundabouts = []

    if exclude_roundabouts:
        for r in road_network.getRoundabouts():
            for e in r.getEdges():
                edges_in_roundabouts.append(e)
    
    for edge in road_network.getEdges():

        edge_id = edge.getID()

        if edge_id not in edges_in_roundabouts:

            lng, lat = gps_coordinate_of_edge_from(road_network, edge_id)

            edge_id_list.append(edge_id)
            lng_list.append(lng)
            lat_list.append(lat)


    edge_coords = gpd.points_from_xy(lng_list, lat_list)
    
    gpd_edges = gpd.GeoDataFrame(geometry=edge_coords)
    gpd_edges['edge_ID'] = edge_id_list
    
    sj = gpd.sjoin(tessellation, gpd_edges)
    sj = sj.drop(["index_right", "geometry"], axis=1)
    
    res = sj.groupby(["tile_ID"])["edge_ID"].apply(list).to_dict()
    
    return res


def gps_coordinate_of_edge_from(net, edge_id):

    x, y = net.getEdge(edge_id).getFromNode().getCoord()
    lon, lat = net.convertXY2LonLat(x, y)

    return lon, lat



def create_dict_tile_nodes(road_network, tessellation, exclude_roundabouts=False):
    
    lng_list, lat_list, node_id_list = [], [], []

    nodes_in_roundabouts = []

    if exclude_roundabouts:
        for r in road_network.getRoundabouts():
            for n in r.getNodes():
                nodes_in_roundabouts.append(n)

    for node in road_network.getNodes():

        node_id = node.getID()

        if node_id not in nodes_in_roundabouts:

            lng, lat = gps_coordinate_of_node(road_network, node_id)

            node_id_list.append(node_id)
            lng_list.append(lng)
            lat_list.append(lat)


    node_coords = gpd.points_from_xy(lng_list, lat_list)

    gpd_nodes = gpd.GeoDataFrame(geometry=node_coords)
    gpd_nodes['node_ID'] = node_id_list

    sj = gpd.sjoin(tessellation, gpd_nodes)
    sj = sj.drop(["index_right", "geometry"], axis=1)

    res = sj.groupby(["tile_ID"])["node_ID"].apply(list).to_dict()
    
    return res
    
    
def gps_coordinate_of_node(net, node_id):

    x, y = net.getNode(node_id).getCoord()
    lon, lat = net.convertXY2LonLat(x, y)

    return lon, lat



# Function for weighted random choice
def weighted_choice(choices, weights, n_samples=1):
    chosen = np.random.choice(choices, p=weights, size=n_samples)
    return chosen




def create_traffic_demand_from_matrix(od_matrix, dict_mapping, n_vehicles, road_network, node_mode=True, threshold_km=1.2,
                                      max_tries=100, random_seed=None, allow_self_tiles=True, show_progress=True):
    
    if random_seed is not None:
        np.random.seed(random_seed)
        print(f"seed set to: {random_seed}")
        
    if show_progress:
         pbar = tqdm(total=n_vehicles) 

    # n_vehicles pairs in the form of (edge_start, edge_end)
    od_list, choices_list = [], []


    size = od_matrix.shape[0]

    for i in range(size):
        if str(i) not in dict_mapping.keys():
            od_matrix[i] = 0
            od_matrix[:, i] = 0


    #random choice of tile_start, tile_end
    weights = od_matrix.flatten()


    # Convert the sumo network into an Igraph network
    G = from_sumo_to_igraph_network(road_network)


    # Generate a list of random indices based on weights
    list_random_inds = list(weighted_choice(np.arange(len(weights)), weights/sum(weights), n_samples=1000000))
    current_ind = 0

    # Iterate over the number of vehicles
    for v in range(n_vehicles):

        valid_od = False

        # Selection of a single OD pair
        while not valid_od:

            tries = 0

            # Random choice of origin and destination tile using pre-generated indices
            ind = list_random_inds[current_ind]
            current_ind += 1

            # Convert index to row and column
            tile_start, tile_end = str(int(ind/size)), str(ind%size)

            # Ensure that self-tiles are not allowed
            if not allow_self_tiles:
                while tile_start == tile_end:
                    ind = list_random_inds[current_ind]
                    current_ind += 1
                    tile_start, tile_end = str(int(ind/size)), str(ind%size)

            # List of elements in origin and destination
            element_list_start = dict_mapping[tile_start]
            element_list_end = dict_mapping[tile_end]

            while tries < max_tries:

                # Randomly choose elements from the origin and destination lists
                ind_start = np.random.randint(0, len(element_list_start))
                ind_end = np.random.randint(0, len(element_list_end))

                element_start = element_list_start[ind_start]
                element_end = element_list_end[ind_end]

                # Compute element distance
                if node_mode:
                    lon_o, lat_o = gps_coordinate_of_node(road_network, element_start)
                    lon_d, lat_d = gps_coordinate_of_node(road_network, element_end)
                else:
                    lon_o, lat_o = gps_coordinate_of_edge_avg(road_network, element_start)
                    lon_d, lat_d = gps_coordinate_of_edge_avg(road_network, element_end)

                d_km = distance_earth_km({"lat":lat_o, "lon":lon_o}, {"lat":lat_d, "lon":lon_d})

                if d_km >= threshold_km:

                    # Check if the elements are connected
                    if node_mode:
                        connected = are_nodes_connected(G, element_start, element_end)
                    else:
                        connected = are_edges_connected(G, element_start, element_end)

                    if connected:
                        od_list.append([element_start, element_end])
                        choices_list.append((int(ind/size), ind%size))
                        tries = 0
                        if show_progress:
                            pbar.update(1)
                        valid_od = True
                        break
                    else:
                        tries += 1
                else:
                    # Origin and destination are too close
                    tries += 1

                if tries == max_tries:

                    # Permute the lists of elements and try again
                    element_list_start_P = np.random.permutation(element_list_start)
                    element_list_end_P = np.random.permutation(element_list_end)

                    for element_start, element_end in ((e1, e2) for e1 in element_list_start_P for e2 in element_list_end_P):

                        # Compute element distance
                        if node_mode:
                            lon_o, lat_o = gps_coordinate_of_node(road_network, element_start)
                            lon_d, lat_d = gps_coordinate_of_node(road_network, element_end)
                        else:
                            lon_o, lat_o = gps_coordinate_of_edge_avg(road_network, element_start)
                            lon_d, lat_d = gps_coordinate_of_edge_avg(road_network, element_end)

                        d_km = distance_earth_km({"lat":lat_o, "lon":lon_o}, {"lat":lat_d, "lon":lon_d})

                        if d_km >= threshold_km:

                            # Check if the elements are connected
                            if node_mode:
                                connected = are_nodes_connected(G, element_start, element_end)
                            else:
                                connected = are_edges_connected(G, element_start, element_end)

                            if connected:
                                od_list.append([element_start, element_end])
                                choices_list.append((int(ind/size), ind%size))

                                if show_progress:
                                    pbar.update(1)
                                valid_od = True
                                break
                                
                  
    return od_list, choices_list




def are_nodes_connected(G, origin_node, dest_node):
    
    edges_from = [e.replace("_from","") for e in G["vertices_to_subvertices"][origin_node] if "_from" in e]
    edges_to = [e.replace("_to","") for e in G["vertices_to_subvertices"][dest_node] if "_to" in e]

    if len(edges_from) == 0 or len(edges_to) == 0:
        return False

    for ef in edges_from:
        for et in edges_to:
            if are_edges_connected(G, ef, et):
                #print("Connected", ef, et, sp)
                return True
                
    return False


def are_edges_connected(G, ex, ey):
    
    sp = get_shortest_path(G, ex, ey, attribute="traveltime")
    
    return len(sp["sumo"])>0
    
    
def distance_earth_km(src, dest):
            
    lat1, lat2 = src['lat']*pi/180, dest['lat']*pi/180
    lon1, lon2 = src['lon']*pi/180, dest['lon']*pi/180
    dlat, dlon = lat1-lat2, lon1-lon2

    ds = 2 * asin(sqrt(sin(dlat/2.0) ** 2 + cos(lat1) * cos(lat2) * sin(dlon/2.0) ** 2))
    return 6371.01 * ds



def create_xml_flows(dict_flows={}, filename=None, node_mode=True, lane_best=False):
    
    # xml creation
    root = minidom.Document()
    xml = root.createElement("routes")
    xml.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    xml.setAttribute("xsi:noNamespaceSchemaLocation", "http://sumo.dlr.de/xsd/routes_file.xsd")
    root.appendChild(xml)

    #vehicle type(s)
    xml_element = root.createElement("vType")
    xml_element.setAttribute("id", "type1")
    xml_element.setAttribute("accel", "2.6")
    xml_element.setAttribute("decel", "4.5")
    xml_element.setAttribute("sigma", "0.5")
    xml_element.setAttribute("length", "5")
    xml_element.setAttribute("maxSpeed", "70")
    xml.appendChild(xml_element)

    valid_list = []
    invalid_list = []

    # _______ FLOW ________

    # flows e.g. <flow id="flow_x" type="type1" begin="0" end="0" 
    # number="1" from="edge_start" to="edge_end" via="e_i e_j e_k"/>

    # sort the dict
    dict_flows_time_sorted = dict(sorted(dict_flows.items(), key=lambda item: item[1]['time']))


    for traj_id in dict_flows_time_sorted.keys():

        element_list = dict_flows_time_sorted[traj_id]['element']
        element_list = [e for e in element_list if str(e)!="-1"]

        #remove consecutive duplicates
        element_list = [x[0] for x in groupby(element_list)]

        intermediate_list = str(element_list[1:-1]).replace(",","").replace("'","")[1:-1]
        start_element = element_list[0]
        end_element = element_list[-1]

        departure_time = dict_flows_time_sorted[traj_id]['time']

        dt = 10
        flow_num = 1
        via = "false"
        col = "blue"

        xml_element = root.createElement("flow")
        xml_element.setAttribute("type", "type1")
        xml_element.setAttribute("begin", str(departure_time))
        xml_element.setAttribute("end", str(departure_time+dt))
        xml_element.setAttribute("number", str(flow_num))
        xml_element.setAttribute("color", col)
        
        if lane_best:
            xml_element.setAttribute("departLane", "best")

        if node_mode:
            xml_element.setAttribute("fromJunction", start_element)
            xml_element.setAttribute("toJunction", end_element)
        else:
            xml_element.setAttribute("from", start_element)
            xml_element.setAttribute("to", end_element)

        if len(element_list)>2:
            if via:
                xml_element.setAttribute("via", intermediate_list)
        xml_element.setAttribute("id", traj_id)
        xml.appendChild(xml_element)

    xml_str = root.toprettyxml(indent="\t")

    with open(filename, "w") as f:
        f.write(xml_str)
        
        
        
import gzip

def create_xml_vehicles(dict_vehicles, filename, lane_best=True, compress=False, text_comment=""):
    
    # xml creation
    root = minidom.Document()
    xml = root.createElement("routes")
    xml.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    xml.setAttribute("xsi:noNamespaceSchemaLocation", "http://sumo.dlr.de/xsd/routes_file.xsd")
    root.appendChild(xml)

    #vehicle type(s)
    element = root.createElement("vType")
    element.setAttribute("id", "type1")
    element.setAttribute("accel", "2.6")
    element.setAttribute("decel", "4.5")
    element.setAttribute("sigma", "0.5")
    element.setAttribute("length", "5")
    element.setAttribute("maxSpeed", "70")
    xml.appendChild(element)
    
    # Adding comment at the beginning of the file
    if text_comment != "":
        comment = root.createComment(text_comment)
        root.insertBefore(comment, xml)

    # sort the dict by departure time
    dict_vehicles_time_sorted = dict(sorted(dict_vehicles.items(), 
                                            key=lambda item: item[1]['time']))


    for traj_id in dict_vehicles_time_sorted.keys():

            edge_list = dict_vehicles_time_sorted[traj_id]['edges']
            start_second = str(dict_vehicles_time_sorted[traj_id]['time'])

            try:
                col = str(dict_vehicles_time_sorted[traj_id]['color'])
            except:
                col = "blue"
            
            element = root.createElement("vehicle")
            element.setAttribute("color", col)
            element.setAttribute("id", traj_id)
            element.setAttribute("type", "type1")
            
            if lane_best:
                element.setAttribute("departLane", "best")
                
            element.setAttribute("depart", start_second)
            
            route_element = root.createElement("route")
            
            if type(edge_list) is list:
                edge_list = str(edge_list).replace("'","").replace("[","").replace("]","").replace(",","")
                
            route_element.setAttribute("edges", edge_list)
            
            element.appendChild(route_element)

            xml.appendChild(element)

    xml_str = root.toprettyxml(indent="\t")

    if compress:
        with gzip.open(filename+".gz", "wt") as f:
            f.write(xml_str)
    
    else:  
        with open(filename, "w") as f:
            f.write(xml_str)




def load_route_file_in_dict(filename, original_name=False):
    
    if ".gz" in filename:    
        with gzip.open(filename, 'rt') as f:
            xml_content = f.read()
        route_nav_xml = xml.dom.minidom.parseString(xml_content)
    else:
        route_nav_xml = xml.dom.minidom.parse(filename)
        
    dict_path_nav = {}

    for v in route_nav_xml.getElementsByTagName('vehicle'):
        if original_name:
            v_id = v.attributes['id'].value.replace(".0","")
        else:
            v_id = int(v.attributes['id'].value.split("_")[-1].replace(".0",""))
        
        str_edges = v.getElementsByTagName('route')[0].attributes['edges'].value.split(" ")
        
        dep_time = float(v.attributes['depart'].value)
        
        dict_path_nav[v_id] = {"edges":str_edges, "time":dep_time}
        
    return dict_path_nav



def pearson_cpc_matrices(m1, m2):
    
    flatten_m1 = m1.flatten()
    flatten_m2 = m2.flatten()
    
    pearson = pearsonr(flatten_m1, flatten_m2)[0]
    cpc = common_part_of_commuters(flatten_m1, flatten_m2)  
    
    return pearson, cpc 


def invalid_routes_in_demand(dict_mobility_demand, road_network_path):


    filename_tmp = f"./tmp_route_file.rou.xml"
    output_tmp = f"./tmp_output_route_file.rou.xml"

    create_xml_flows(dict_mobility_demand, filename=filename_tmp, node_mode=True)

    command_str = "duarouter --route-files "+filename_tmp+" "+\
        " --net-file "+road_network_path+" --routing-threads 16 "\
    " --random false --output-file "+output_tmp+ " --junction-taz true --ignore-errors"

    p = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retval = p.wait()

    # Read the output and error streams
    _, error = p.communicate()
    error_str = error.decode("utf-8")
    
    # Define a regular expression pattern to match the relevant information
    pattern = r"(vehicle_\d+\.\d+).*?has no valid route"
    
    # Use re.findall to find all occurrences of the pattern in the text
    matches = re.findall(pattern, error_str)
    
    # remove temporary files
    os.remove(filename_tmp)
    os.remove(output_tmp)
    os.remove(output_tmp.replace("xml","alt.xml"))

    
    if len(matches)>0:
        return [match.replace(".0","") for match in matches]
    
    else:
        return []
    
    
    
    
def create_mixed_route_demands(navigator, path_base_demand, path_demand_navigator, path_dict_set_vehicles, result_folder, 
                               n_rep_min=0, n_rep_max=9, percentages=list(np.arange(0, 101, 10)), lane_best=True, compress=True):
    
    suffix_comp = ""
    if compress:
        suffix_comp=".gz"
    
    # Create the output folder
    if not os.path.exists(result_folder):
        os.makedirs(result_folder, exist_ok=True)
        
    # Load the route demand for NON routed vehicles
    dict_demand_base = load_route_file_in_dict(path_base_demand)
    
    # Load the route demand for ROUTED vehicles
    dict_demand_navigator = load_route_file_in_dict(path_demand_navigator)
    
    # Load the dict associating the vehicle to route for each % and rep
    with open(path_dict_set_vehicles) as json_file:
        dict_set_vehicles = json.load(json_file)
    
    
    # Create 0% (only 1 rep since it is deterministic)
    if 0 in percentages:
        dict_demand_0pct = assemble_mixed_demand(navigator, dict_demand_base, dict_demand_navigator, [])
        filename_save = f"{navigator}_0_dua_100_rep_0.rou.xml"
        create_xml_vehicles(dict_demand_0pct, result_folder+filename_save, lane_best=lane_best, compress=compress);
        
        ## TEST
        test_0pct = load_route_file_in_dict(result_folder+filename_save+suffix_comp)
        assert test_0pct == dict_demand_base, "Error creation demand 0%"
        
    
    # Create 100% (only 1 rep since it is deterministic)
    if 100 in percentages:
        dict_demand_100pct = assemble_mixed_demand(navigator, dict_demand_base, dict_demand_navigator, list(dict_demand_base.keys()))
        filename_save = f"{navigator}_100_dua_0_rep_0.rou.xml"
        create_xml_vehicles(dict_demand_100pct, result_folder+filename_save, lane_best=lane_best, compress=compress);
        
        ## TEST
        test_100pct = load_route_file_in_dict(result_folder+filename_save+suffix_comp)
        assert test_100pct == dict_demand_navigator, "Error creation demand 100%"
    
    
    # Create the other percentages
    for pct in [p for p in percentages if 0<p<100]:
        
        str_pct = str(pct)
        str_pct_inv = str(int(100-pct))

        for rep in range(n_rep_min, n_rep_max+1):
        
            list_id_routed_vehicles = dict_set_vehicles[str(pct)][str(rep)]
            
            dict_demand_xpct = assemble_mixed_demand(navigator, dict_demand_base, dict_demand_navigator, list_id_routed_vehicles)

            filename_save = f"{navigator}_{str_pct}_dua_{str_pct_inv}_rep_{rep}.rou.xml"
            create_xml_vehicles(dict_demand_xpct, result_folder+filename_save, lane_best=lane_best, compress=compress);
            
            ## TEST x%
            count_routed, count_non_routed = 0, 0
            
            test_Xpct = load_route_file_in_dict(result_folder+filename_save+suffix_comp)
            for vid in test_Xpct:
                if vid in list_id_routed_vehicles:
                    count_routed+=1
                    assert test_Xpct[vid] == dict_demand_navigator[vid], f"Error creation demand {pct}% rep {rep}"
                else:
                    count_non_routed+=1
                    assert test_Xpct[vid] == dict_demand_base[vid], f"Error creation demand {pct}% rep {rep}"
                    
            
            assert count_routed+count_non_routed == len(dict_demand_base), f"Error SUM {pct}%"
            
            assert count_routed == int(np.round(len(dict_demand_base)*(pct/100))), f"Error {pct}% {count_routed} {int(np.round(len(dict_demand_base)*(pct/100)))}"
                

    
    
def assemble_mixed_demand(nav_name, dict_demand_base, dict_demand_navigator, list_id_routed):
    
        
    list_id_routed = set(list_id_routed)
    
    dict_demand_tmp = {}
    
    for vid in dict_demand_base:

        dep_time = dict_demand_base[vid]['time']

        if vid in list_id_routed:
            vid_demand = f"{nav_name}_{vid}"
            edge_list = dict_demand_navigator[vid]["edges"]
        else:
            vid_demand = f"duarouter_{vid}"
            edge_list = dict_demand_base[vid]["edges"]

        dict_demand_tmp[vid_demand] = {'edges':str(edge_list).replace(",","").replace("'","")[1:-1], 
                                   'time': dep_time} 
        
    return dict_demand_tmp






def create_mixed_route_demands_interplay(interplay_name, list_navs_interplay, path_base_demand, path_folder_routed_navs, path_dict_set_vehicles, result_folder, n_rep_min=0, n_rep_max=9, percentages=list(np.arange(0, 101, 10)), lane_best=True, compress=True):
    
    suffix_comp = ""
    if compress:
        suffix_comp=".gz"
    
    # Create the output folder
    if not os.path.exists(result_folder):
        os.makedirs(result_folder, exist_ok=True)
        
    # Load the route demand for NON routed vehicles
    dict_demand_base = load_route_file_in_dict(path_base_demand)
    
    # Load the route demands for ROUTED vehicles with interplay navs
    dict_demands_navigator_interplay = {}
    
    for navigator in list_navs_interplay:
        path_demand_navigator = f"{path_folder_routed_navs}{navigator}.rou.xml{suffix_comp}"
        print(path_demand_navigator)
        dict_tmp_demand_navigator = load_route_file_in_dict(path_demand_navigator)
        dict_demands_navigator_interplay[navigator] = dict_tmp_demand_navigator

    
    # Load the dict associating the vehicle to route for each % and rep
    with open(path_dict_set_vehicles) as json_file:
        dict_set_vehicles = json.load(json_file)
    
    
    # Create 0% (only 1 rep since it is deterministic)
    if 0 in percentages:
        dict_demand_0pct = assemble_mixed_demand(interplay_name, dict_demand_base, {}, [])
        filename_save = f"{interplay_name}_0_dua_100_rep_0.rou.xml"
        create_xml_vehicles(dict_demand_0pct, result_folder+filename_save, lane_best=lane_best, compress=compress);
        
        ## TEST
        test_0pct = load_route_file_in_dict(result_folder+filename_save+suffix_comp)
        assert test_0pct == dict_demand_base, "Error creation demand 0%"

    # --- --- --- ---
    
    # Create the other percentages
    for pct in [p for p in percentages if p>0]:
        
        str_pct = str(pct)
        str_pct_inv = str(int(100-pct))

        if pct == 100:
            rep_range = [0, 1]
        else:
            rep_range = [n_rep_min, n_rep_max+1]

        for rep in range(rep_range[0], rep_range[1]):

            if pct != 100:
                list_id_routed_vehicles = dict_set_vehicles[str(pct)][str(rep)]
            else:
                list_id_routed_vehicles = list(dict_demand_base.keys())

            dict_demand_xpct = assemble_mixed_demand_interplay(dict_demand_base, dict_demands_navigator_interplay, list_id_routed_vehicles)

            filename_save = f"{interplay_name}_{str_pct}_dua_{str_pct_inv}_rep_{rep}.rou.xml"
            create_xml_vehicles(dict_demand_xpct, result_folder+filename_save, lane_best=lane_best, compress=compress);
            
            ## TEST x%
            count_routed, count_non_routed = 0, 0
            
            test_Xpct = load_route_file_in_dict(result_folder+filename_save+suffix_comp)
            for vid in test_Xpct:
                if vid in list_id_routed_vehicles:
                    count_routed+=1
                    #assert test_Xpct[vid] == dict_demand_navigator[vid], f"Error creation demand {pct}% rep {rep}"
                else:
                    count_non_routed+=1
                    assert test_Xpct[vid] == dict_demand_base[vid], f"Error creation demand {pct}% rep {rep}"

            # test fraction interplay
            n_expected_per_nav = (len(dict_demand_base)*pct/100)/len(list_navs_interplay)
            for nav in list_navs_interplay:
                cnt = 0
                for vid in dict_demand_xpct:
                    if nav in vid:
                        cnt+=1
                        
            assert cnt == n_expected_per_nav, f"Error interplay nav={nav} {cnt} {n_expected_per_nav}"
            
            assert count_routed+count_non_routed == len(dict_demand_base), f"Error SUM {pct}%"
            
            assert count_routed == int(np.round(len(dict_demand_base)*(pct/100))), f"Error {pct}% {count_routed} {int(np.round(len(dict_demand_base)*(pct/100)))}"
    


def assemble_mixed_demand_interplay(dict_demand_base, dict_demands_navigator_interplay, list_id_routed):

    # list of navigators
    list_navigators = list(dict_demands_navigator_interplay.keys())
    
    # random order permutation
    permuted_list_id = np.random.permutation(list_id_routed)
    
    # just to check if a vehicle is routed or not
    list_id_routed_check = set(list_id_routed)
    
    # dict that associates to each navigator in the interplay set the list of vehicles routed with it
    dict_navigators_ids = {}
    s_tmp = set()

    intervals_interplay_ids = generate_intervals(len(list_id_routed), len(list_navigators))
    
    for ind, nav in enumerate(list_navigators):
        left_interval_nav = intervals_interplay_ids[ind][0]
        right_interval_nav = intervals_interplay_ids[ind][1]
        dict_navigators_ids[nav] = set(permuted_list_id[left_interval_nav:right_interval_nav])
        s_tmp.update(dict_navigators_ids[nav])
    
    assert len(s_tmp) == len(list_id_routed), "ERROR dict_navigators_ids"
    
    dict_demand_tmp = {}
    
    for vid in dict_demand_base:
    
        dep_time = dict_demand_base[vid]['time']
    
        if vid in list_id_routed_check:
            # which navigator?
            navigator_to_assign = [nav for nav in dict_navigators_ids if vid in dict_navigators_ids[nav]][0]
            
            vid_demand = f"{navigator_to_assign}_{vid}"
            edge_list = dict_demands_navigator_interplay[navigator_to_assign][vid]["edges"]
        else:
            vid_demand = f"duarouter_{vid}"
            edge_list = dict_demand_base[vid]["edges"]
    
        dict_demand_tmp[vid_demand] = {'edges':str(edge_list).replace(",","").replace("'","")[1:-1], 
                                   'time': dep_time} 


    ## test correctness
    for vid in dict_demand_tmp:
    
        vid_int = int(vid.split("_")[1])
        edges_assigned = dict_demand_tmp[vid]["edges"].split(" ")
        
        if vid_int in list_id_routed_check:
            edges_gt = dict_demands_navigator_interplay[vid.split("_")[0]][vid_int]["edges"]
        else:
            edges_gt = dict_demand_base[vid_int]["edges"]
            
        assert edges_assigned == edges_gt, f"ERROR {vid} {edges_assigned} {edges_gt}"

    
    return dict_demand_tmp



def generate_intervals(N, S):
    
    # each interval is [a, b)
    
    interval_size = N // S
    intervals = []
    for i in range(S):
        start = i * interval_size
        end = (i + 1) * interval_size - 1 if i < S - 1 else N - 1
        intervals.append((start, end+1))
    return intervals
    