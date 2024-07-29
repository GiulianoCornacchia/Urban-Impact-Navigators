import pandas as pd
import geopandas as gpd
import skmob
from skmob.preprocessing import detection, compression
import pygeos
from pygeos import contains, Geometry
import numpy as np
from datetime import datetime, timedelta

from skmob.utils import gislib, utils, constants
from skmob.core.trajectorydataframe import *
import numpy as np
import inspect



def my_stay_locations(tdf, stop_radius_factor=0.5, minutes_for_a_stop=20.0, spatial_radius_km=0.2, leaving_time=True, no_data_for_minutes=1e12, min_speed_kmh=None):
    
    #print("My stay location")

    # Sort
    tdf = tdf.sort_by_uid_and_datetime()

    # Save function arguments and values in a dictionary
    frame = inspect.currentframe()
    args, _, _, arg_values = inspect.getargvalues(frame)
    arguments = dict([('function', my_stay_locations.__name__)]+[(i, arg_values[i]) for i in args[1:]])

    groupby = []

    if utils.is_multi_user(tdf):
        groupby.append(constants.UID)
    if utils.is_multi_trajectory(tdf):
        groupby.append(constants.TID)

    # Use the spatial_radius in the tdf parameters, if present, otherwise use the default argument.
    try:
        stop_radius = tdf.parameters[constants.COMPRESSION_PARAMS]['spatial_radius_km'] * stop_radius_factor
    except (KeyError, TypeError):
        pass
    if spatial_radius_km is not None:
        stop_radius = spatial_radius_km

    if len(groupby) > 0:
        # Apply simplify trajectory to each group of points
        stdf = tdf.groupby(groupby, group_keys=False, as_index=False).apply(_my_stay_locations_trajectory, stop_radius=stop_radius,
                           minutes_for_a_stop=minutes_for_a_stop, leaving_time=leaving_time,
                           no_data_for_minutes=no_data_for_minutes, min_speed_kmh=min_speed_kmh).reset_index(drop=True)
    else:
        stdf = _my_stay_locations_trajectory(tdf, stop_radius=stop_radius, minutes_for_a_stop=minutes_for_a_stop,
                            leaving_time=leaving_time, no_data_for_minutes=no_data_for_minutes,
                            min_speed_kmh=min_speed_kmh).reset_index(drop=True)

    # TODO: remove the following line when issue #71 (Preserve the TrajDataFrame index during preprocessing operations) is solved.
    stdf.reset_index(inplace=True, drop=True)

    stdf.parameters = tdf.parameters
    stdf.set_parameter(constants.DETECTION_PARAMS, arguments)
    return stdf


def _my_stay_locations_trajectory(tdf, stop_radius, minutes_for_a_stop, leaving_time, no_data_for_minutes, min_speed_kmh):

    # From dataframe convert to numpy matrix
    lat_lng_dtime_other = list(utils.to_matrix(tdf))
    columns_order = list(tdf.columns)

    stay_locations, leaving_times = _my_stay_locations_array(lat_lng_dtime_other, stop_radius,
                                        minutes_for_a_stop, leaving_time, no_data_for_minutes, min_speed_kmh)

    #print(utils.get_columns(data))
    # stay_locations = utils.to_dataframe(stay_locations, utils.get_columns(data))
    stay_locations = nparray_to_trajdataframe(stay_locations, utils.get_columns(tdf), {})

    # Put back to the original order
    stay_locations = stay_locations[columns_order]

    if leaving_time:
        stay_locations.loc[:, constants.LEAVING_DATETIME] = pd.to_datetime(leaving_times)

    return stay_locations


def _my_stay_locations_array(lat_lng_dtime_other, stop_radius, minutes_for_a_stop, leaving_time, no_data_for_minutes, min_speed_kmh):
    """
    Create a stop if the user spend at least `minutes_for_a_stop` minutes
    within a distance `stop_radius` from a given point.
    """
    # Define the distance function to use
    measure_distance = gislib.getDistance

    stay_locations = []
    leaving_times = []

    lat_0, lon_0, t_0 = lat_lng_dtime_other[0][:3]
    sum_lat, sum_lon, sum_t = [lat_0], [lon_0], [t_0]
    speeds_kmh = []
    
    #print("My version of the stay location detection")

    count = 1
    lendata = len(lat_lng_dtime_other) - 1

    for i in range(lendata):

        lat, lon, t = lat_lng_dtime_other[i+1][:3]

        Dt = utils.diff_seconds(t_0, t) / 60.
        Dr = measure_distance([lat_0, lon_0], [lat, lon])

        if Dr > stop_radius or i == lendata - 1:
            if Dt > minutes_for_a_stop or i == lendata - 1:                
                extra_cols = list(lat_lng_dtime_other[i][3:])

                # estimate the leaving time
                estimated_final_t = t

                if len(sum_lat) > 0 and utils.diff_seconds(t_0, estimated_final_t) / 60. > minutes_for_a_stop:
                    if leaving_time:
                        #leaving_times.append(estimated_final_t)
                        
                        # if the stop has more than 1 point
                        if len(sum_t)>1:              
                            if utils.diff_seconds(sum_t[-1], estimated_final_t) / 60. > minutes_for_a_stop:
                                #print("Above Dt th [take the 1st OUTside]")
                                #print(sum_t)
                                #print(estimated_final_t)
                                leaving_times.append(estimated_final_t)
                            else:
                                #print("[take the last INside]")
                                #print(sum_t[-1])
                                leaving_times.append(sum_t[-1])
                                
                        else:
                            # if the stop has only ONE point X it is the end of the 
                            # incoming trip. So I'll take the first outside
                            #print("Stop of 1 point only [take the 1st OUTside]")
                            leaving_times.append(estimated_final_t)

                    stay_locations += [[np.median(sum_lat), np.median(sum_lon), t_0] + extra_cols]

                count = 0
                lat_0, lon_0, t_0 = lat, lon, t
                sum_lat, sum_lon, sum_t = [], [], []
                speeds_kmh = []
            else:
                # Not a stop
                count = 0
                lat_0, lon_0, t_0 = lat, lon, t
                sum_lat, sum_lon, sum_t = [], [], []
                speeds_kmh = []

        count += 1
        sum_lat += [lat]
        sum_lon += [lon]
        sum_t += [t]

    return stay_locations, leaving_times




def print_stats(df, uid="uid", trip_id=None):
   
    print("# gps points", len(df))
    print("# users", len(df[uid].unique()))
    
    if trip_id:
        print("# trips", len(df[trip_id].unique()))


def filter_in_shape_pygeos(tdf, shape, identifier, drop=True):
    
    pygeos_shape = Geometry(str(shape["geometry"].iloc[0]))
    
    list_points = list(gpd.points_from_xy(tdf.lng, tdf.lat))
    pygeos_points = [Geometry(str(p)) for p in list_points]
    
    tdf['points'] = list_points
    tdf['isin'] = contains(pygeos_shape, pygeos_points)
    
    return tdf
    

def split_trajectories_in_tdf(tdf, stop_tdf, identifier="uid"):
   

    tdf_with_tid = tdf.groupby(identifier).apply(_split_trajectories, stop_tdf)
    return tdf_with_tid.reset_index(drop=True)


def _split_trajectories(tdf, stop_tdf):

    c_uid = tdf.uid[:1].item()
    stop_tdf_current_user = stop_tdf[stop_tdf.uid == c_uid]

    if stop_tdf_current_user.empty:
        return
    else:
        first_traj = [tdf[tdf.datetime <= stop_tdf_current_user.datetime[:1].item()]]
        last_traj = [tdf[tdf.datetime >= stop_tdf_current_user.leaving_datetime[-1:].item()]]
        all_other_traj = [tdf[(tdf.datetime >= start_traj_time) & (tdf.datetime <= end_traj_time)] for end_traj_time, start_traj_time in zip(stop_tdf_current_user['datetime'][1:], stop_tdf_current_user['leaving_datetime'][:-1])]
        all_traj = first_traj + all_other_traj + last_traj
        tdf_with_tid = pd.concat(all_traj)
        list_tids = [list(np.repeat(i, len(df))) for i, df in zip(range(1,len(all_traj)+1), all_traj)]
        list_tids_ravel = [item for sublist in list_tids for item in sublist]
        tdf_with_tid['tid'] = list_tids_ravel
        return tdf_with_tid
    
    
    
def segment_trajectories_area(x, identifier):
    
    tid=-1
    list_tids = []
    
    tmp = pd.DataFrame()
    
    tmp["isin"] = x["isin"]
    tmp["isin_prev"] = x["isin"].shift(+1)
    tmp["id"] = x[identifier]
    tmp["id_prev"] = x[identifier].shift(+1)

    for isin, isin_prev, uid, uid_prev in zip(tmp["isin"], tmp["isin_prev"], 
                                              tmp["id"], tmp["id_prev"]):

        if uid != uid_prev:
            tid+=1          
        elif isin != isin_prev:
            tid+=1
            
        list_tids.append(str(uid)+"_"+str(tid))
            
    return list_tids



def tdf_identifier_two_point_inside_shape(df, city_shape, identifier, th=1, use_pygeos=False):
    
    if use_pygeos:
        df_filter_shape = filter_in_shape_pygeos(df, city_shape, "")
    else:
        df_filter_shape = filter_in_shape(df, city_shape, "")
    
    gb = df_filter_shape.groupby(identifier, as_index=False).count()
    
    list_identifiers_2_keep = gb[gb["isin"]>th][identifier].unique()

    tdf_2_inside = df_filter_shape[df_filter_shape[identifier].isin(list_identifiers_2_keep)]
    
    return tdf_2_inside



def is_inside_bounding_box(list_lat, list_lng, minx, miny, maxx, maxy):
    
    list_inside_bbox = []

    for lat, lng in zip(list_lat, list_lng):
        if minx <= lng <= maxx and miny <= lat <= maxy:
            # The point (lat, lng) is inside the bounding box
            list_inside_bbox.append(1)
        else: 
            # The point is outside the bounding box
            list_inside_bbox.append(0)
            
    return list_inside_bbox




def create_trips_from_gps(df, city_shape, date_col, max_speed_kmh=250, spatial_radius_km_stops=0.2, minutes_for_a_stop=20):
    
    
    # STEP 2. ----- Reduce cardinality: if ALL the coordinates of a user are outside the bbox discard that user

    minx, miny, maxx, maxy = city_shape.bounds.iloc[0]
    
    list_inside_bbox = is_inside_bounding_box(df["lat"], df["lon"], minx, miny, maxx, maxy)
    df["inside_bbox"] = list_inside_bbox
    df_gb = df.groupby("userid", as_index=False).max()
    df_gb = df_gb[df_gb["inside_bbox"]==1]
    
    ids_2_keep = list(df_gb["userid"])
    df_2 = df[df["userid"].isin(ids_2_keep)]
    
    # convert to a TrajDataFrame
    tdf_2 = skmob.TrajDataFrame(df_2, latitude='lat', longitude='lon', 
                          datetime="datetime", user_id='userid')
    
    # STEP 3. ----- Keep only users with (at least) two GPS in the area of interest
    identifier = "uid"
    tdf_3 = tdf_identifier_two_point_inside_shape(tdf_2, city_shape, identifier, th=1, use_pygeos=True)
    
    
    # STEP 4. ----- Speed Filtering
    tdf_filtered = skmob.preprocessing.filtering.filter(tdf_3, max_speed_kmh=max_speed_kmh, include_loops=False)
    
    
    # keep only users with at leat two points in the area of interest
    identifier = "uid"
    tdf_5 = tdf_identifier_two_point_inside_shape(tdf_filtered, city_shape, identifier, th=1, use_pygeos=True)
    
    
    # STEP 6. ----- Stop Detection
    
    stdf = my_stay_locations(tdf_5, stop_radius_factor=None, minutes_for_a_stop=minutes_for_a_stop, 
                           spatial_radius_km=spatial_radius_km_stops, leaving_time=True)
    
    traj_seg = split_trajectories_in_tdf(tdf_5, stdf)
    
    
    # create the IDENTIFIER "trip_id" of a TRIP as {uid}_{tid}
    # e.g., 123_45 means the 45th trips of user with ID = 123
    trip_id_list = [f"{uid}_{tid}" for uid, tid in zip(traj_seg["uid"], traj_seg["tid"])]
    traj_seg["trip_id"] = trip_id_list
    
    
    # Remove trips with only one GPS point (not enough to define a trip)
    gb_6 = traj_seg.groupby("trip_id", as_index=False).count().sort_values("isin")
    trip_ids_2_keep = gb_6[gb_6["isin"]>1]["trip_id"]
    traj_seg_6 = traj_seg[traj_seg["trip_id"].isin(trip_ids_2_keep)]
    
    
    # STEP 7. ----- Remove all the TRIPS completely outside the Shape
    identifier = "trip_id"
    trip_id_at_least_one_inside = list(traj_seg_6.query("isin == True")[identifier].unique())
    tdf_7 = traj_seg_6[traj_seg_6[identifier].isin(trip_id_at_least_one_inside)]
    tdf_discarded = traj_seg_6[~traj_seg_6[identifier].isin(trip_id_at_least_one_inside)]
    
    if len(tdf_discarded) > 0:
        assert tdf_discarded["isin"].unique()[0] == False
    
    
    
    # STEP 8. ----- TRIP segmentation wrt boundaries
    # ID trip_id
    
    identifier = "trip_id"
    identifier_segment = segment_trajectories_area(tdf_7, identifier)
    tdf_8 = tdf_7.copy()
    tdf_8['trip_id_segment'] = identifier_segment
    
    
    
    # STEP 9. ----- Keep only the TRIP INSIDE the geographic region (ALL THE POINTS)
    at_least_one_outside = list(tdf_8[tdf_8["isin"]==False]["trip_id_segment"].unique())
    tdf_9 = tdf_8[~tdf_8["trip_id_segment"].isin(at_least_one_outside)]
    assert len(tdf_9[tdf_9["isin"]==False]) == 0
    
    
    # Create identifier as date + trip_id
    # ID: DATE of the departure time + trip_id (trip_id)
    
    tdf_departures = tdf_9.groupby("trip_id_segment", as_index=False).min()[["trip_id_segment", "datetime"]]
    dict_id_departure = {k: v for k, v in zip(tdf_departures["trip_id_segment"], tdf_departures["datetime"])}
    
    final_trip_id = []
    
    for trip_id in tdf_9["trip_id_segment"]:
        date = dict_id_departure[trip_id]
        str_date = str(date).split(" ")[0].replace("-","")
        final_trip_id.append(str_date+"_"+trip_id)
    
    tdf_9["trip_id"] = final_trip_id
    tdf_9["user"] = tdf_9["uid"]
    
    
    gb_9 = tdf_9.groupby("trip_id", as_index=False).count().sort_values("user")
    trip_ids_2_keep = gb_9[gb_9["user"]>1]["trip_id"]
    tdf_final = tdf_9[tdf_9["trip_id"].isin(trip_ids_2_keep)]
    
    
    return tdf_final