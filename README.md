<div align="center">
  <h1>The traffic concentration effects of urban navigation services</h1> 
  <img src="images/img_intro.webp" width="700">
</div>

### Authors:

* Giuliano Cornacchia <sup>1</sup> [<img src="https://img.shields.io/badge/ORCID-0000--0003--2263--7654-brightgreen?logo=orcid&logoColor=white" alt="ORCID" height="16">](https://orcid.org/0000-0003-2263-7654)

* Mirco Nanni <sup>1</sup> [<img src="https://img.shields.io/badge/ORCID-0000--0003--3534--4332-brightgreen?logo=orcid&logoColor=white" alt="ORCID" height="16">](https://orcid.org/0000-0003-3534-4332)

* Dino Pedreschi <sup>2</sup> [<img src="https://img.shields.io/badge/ORCID-0000--0003--4801--3225-brightgreen?logo=orcid&logoColor=white" alt="ORCID" height="16">](https://orcid.org/0000-0003-4801-3225)

* Luca Pappalardo <sup>1,3</sup> [<img src="https://img.shields.io/badge/ORCID-0000--0002--1547--6007-brightgreen?logo=orcid&logoColor=white" alt="ORCID" height="16">](https://orcid.org/0000-0002-1547-6007)


Affiliations:<br>
<sup>1</sup> Institute of Information Science and Technologies (ISTI), National Research Council (CNR), Pisa, Italy <br>
<sup>2</sup> Department of Computer Science, University of Pisa, Pisa, Italy <br>
<sup>3</sup> Scuola Normale Superiore, Pisa, Italy <br>

____


The proliferation of human-AI ecosystems, such as navigation services, raises concerns about their large-scale social and environmental impacts. Our study employs a simulation framework to assess how navigation services influence road network usage and CO2 emissions in urban environments. This repository provides the necessary Python code and tools to reproduce our analysis using the SUMO mobility simulator, offering insights into the collective impact of navigation services at varying adoption rates. To use the code and replicate the analysis, follow the instructions provided in this README file.

## Built with

![python](https://img.shields.io/badge/Python-3776AB.svg?style=for-the-badge&logo=Python&logoColor=white)
![jupyter](https://img.shields.io/badge/Jupyter-F37626.svg?style=for-the-badge&logo=Jupyter&logoColor=white)
![numpy](https://img.shields.io/badge/NumPy-013243.svg?style=for-the-badge&logo=NumPy&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![osm](https://img.shields.io/badge/OpenStreetMap-7EBC6F.svg?style=for-the-badge&logo=OpenStreetMap&logoColor=white)

### Requirements

This project uses the following versions:

![Python](https://img.shields.io/badge/Python-3.9.18-blue) ![SUMO](https://img.shields.io/badge/SUMO-1.19.0-brightgreen)

- **Python**: The code is written in Python 3.9.18.
- **SUMO**: Simulations are run using SUMO version 1.19.0.


<a id='toc' name='toc'></a>

# Table of Contents

 - [Abstract](#abstract)
 - [Repository Structure](#repo-structure)
 - [Code Descriptions](#notebook)
 - [Precomputed Results](#results)
 - [Setup](#setup)
 - [Data Availability](#data)


```

<a id='abstract' name='abstract'></a>
## Abstract

The collective impact of navigation services remains unclear: while often beneficial to individual drivers, they can unintentionally reshape urban traffic patterns. We simulate their impact in Florence, Milan, and Rome (Italy), integrating GPS data, road networks, and route recommendations from leading providers. We identify a concentration effect: as adoption increases, route diversity declines, and traffic and emissions converge onto fewer roads. At full adoption, route diversity decreases by up to 14% compared to a baseline where recommendations are ignored. Moreover, navigation services reduce CO$_2$ emissions at low adoption levels, but these benefits diminish, disappear, or even reverse beyond a city- and service-specific threshold. We replicate our experiments in an abstract setting, obtaining results consistent with those observed in real-world cities.


<a id="repo-structure" name="repo-structure"></a>
## Repository Structure

The repository is organized as follows:
```
.
├── data/
│   ├── bbox_cities/        # Bounding boxes for cities
│   ├── road_networks/      # Road network files used in simulations
│   └── gps_data/           # GPS datasets
│       └── readme.txt
├── images/                 # Figures used in the README
├── results_article/        # Precomputed results used in the paper
│   ├── results_florence.json.gz
│   ├── results_milan.json.gz
│   └── results_rome.json.gz
├── src/                    # Python scripts for simulations
├── README.md

```


### Key folders

- **`data/`**  
  Contains all input data required to build simulations, including road networks and GPS traces.

- **`results_article/`**  
  Contains the **precomputed results** used in the main paper for each city.  
  These can be used to reproduce figures and analyses without running simulations.

- **`src/`**  
  Contains scripts to launch simulations and process outputs.

- **`images/`**  
  Contains visual assets used in this README.


<a id="notebook" name="notebook"></a>
## Code Descriptions

### Notebooks

- **`0_preprocess_trajectory_dataset.ipynb`**: This notebook focuses on preprocessing trajectory data to generate a collection of trips, which will later be used for inferring Origin-Destination (OD) matrices. The notebook is adaptable for any vehicular trace dataset and provides parameters for pre-processing and segmenting trajectories into trips.

- **`1_create_od_matrix.ipynb`**: This notebook computes an OD matrix where each element represents the number of trips starting and ending in specific tiles of an urban environment. It includes routines for generating OD matrices from GPS trajectories or creating random OD matrices. It is flexible and can be adapted to various data sources, with an example provided for Milan.

- **`2_generate_mobility_demand_from_od_matrix.ipynb`**: This notebook aims to generate a realistic Mobility Demand from an OD matrix. It defines a set of trips within an urban environment, selecting origin and destination pairs based on a probability proportional to the OD matrix values. The notebook includes utilities for parameter configuration and handles the iteration process for generating multiple trips.

- **`3_create_routed_paths.ipynb`**: This notebook uses the `duarouter` algorithm to create routes connecting the origins and destinations of vehicles in the mobility demand. It allows for both the fastest path assignment (a navigation service prototype) and randomized path perturbation based on a configurable parameter, simulating variability in driver behavior and route selection.

- **`4_launcher_experiments.ipynb`**: This notebook is responsible for launching SUMO (Simulation of Urban MObility) experiments. It includes settings for experiment parameters to simulate different traffic scenarios.

- **`5_compute_results.ipynb`**: This notebook aggregates the results of simulations into a comprehensive dictionary.

- **`6_create_plots.ipynb`**: This notebook generates plots related to CO2 emissions and route diversity based on the aggregated results computed in the previous notebook. It uses specific dictionaries from the results to visualize the outcomes of the experiments.

### Scripts

- **`launcher_sumo_simulation.py`**: This script is designed to execute a single traffic simulation using the SUMO (Simulation of Urban MObility) simulator. It takes inputs such as a road network file and a route file, simulates the movement of vehicles, and outputs data related to traffic patterns and emissions. The script can also convert XML outputs to CSV for further analysis. It provides options for running the simulation with or without a graphical user interface (GUI) and collecting detailed trip and edge information.
- **`launcher_traffico2.py`**: This script automates the execution of multiple simulations across various adoption rates of navigation services. It calculates "Mixed Routed Paths" (MRPs), which combine different routing strategies and simulates their effects on urban traffic and emissions. The script allows for a detailed analysis of how different levels of navigation service adoption influence route diversity, traffic congestion, and CO2 emissions. It uses the `launcher_sumo_simulation.py` script for each individual simulation.


### Parameters Table for `launcher_sumo_simulation.py`

| Parameter              | Description                                           | Required | Default Value |
|------------------------|-------------------------------------------------------|----------|---------------|
| `-n`, `--net-file`      | Path to the SUMO network file                         | Yes      | None          |
| `-r`, `--route-file`    | Path to the SUMO route file                           | Yes      | None          |
| `-i`, `--exp-id`        | Experiment identifier                                 | Yes      | None          |
| `-o`, `--output-dir`    | Output directory for results                          | Yes      | None          |
| `--edges-info`          | Collect edge-related measures (1 = yes, 0 = no)       | No       | 1             |
| `--trips-info`          | Collect trip-related measures (1 = yes, 0 = no)       | No       | 1             |
| `--log`                 | Create a log of the simulation (1 = yes, 0 = no)      | No       | 1             |
| `--gui`                 | Run SUMO with GUI (1 = yes, 0 = no)                   | No       | 0             |
| `--sumo-opt`            | Additional SUMO options                               | No       | "" (empty)    |

### Example Command:
```bash
python launcher_sumo_simulation.py -n network.net.xml -r routes.rou.xml -i exp1 -o ./output --edges-info 1 --trips-info 1 --log 1 --gui 0 --sumo-opt "--time-to-teleport 120"
```

### Parameters Table for `launcher_traffico2.py`

| Parameter                | Description                                                | Required | Default Value         |
|--------------------------|------------------------------------------------------------|----------|-----------------------|
| `-c`, `--city`           | Name of the city                                            | Yes      | None                  |
| `-v`, `--n-vehicles`     | Number of vehicles                                          | Yes      | None                  |
| `-b`, `--base`           | Base name                                                   | Yes      | None                  |
| `-n`, `--navigator`      | Navigator name                                              | Yes      | None                  |
| `-g`, `--road-network`   | Path to the road network file                               | Yes      | None                  |
| `--path-base`            | Route file for non-routed (base) vehicles                   | Yes      | None                  |
| `--path-navigator`       | Route file for routed (navigator) demands                   | Yes      | None                  |
| `--path-vehicles-mapping` | Path for vehicle mapping (routed vs non-routed)            | Yes      | None                  |
| `--list-pct`             | List of adoption rates (e.g., "0-10-20")                    | No       | "" (0 to 100 in steps of 10) |
| `-o`, `--output-dir`     | Output folder                                               | Yes      | None                  |
| `-z`, `--zipped`         | Zipped option for output files (1 = yes, 0 = no)            | No       | 0                     |
| `--rep-min`              | Minimum repetition                                          | No       | 0                     |
| `--rep-max`              | Maximum repetition                                          | No       | 9                     |
| `--njobs`                | Number of parallel jobs                                     | No       | 20                    |

### Example Command:
```bash
python launcher_traffico2.py -c city_name -v 1000 -b base_name -n navigator_name -g road_network.net.xml --path-base base_route.rou.xml --path-navigator navigator_route.rou.xml --path-vehicles-mapping vehicle_mapping.json --list-pct 0-10-20-30-40-50-60-70-80-90-100 -o ./output_dir --zipped 1 --rep-min 0 --rep-max 9 --njobs 20
```

<a id="results" name="results"></a>
## Precomputed Results

We also include in the repository **precomputed results** for the three analyzed cities used in the main scientific article.  
These results allow users to reproduce figures and analyses **without running the full simulation pipeline**, and can also be used to explore the data further and derive new insights.

Each city is associated with a compressed JSON file located in the `results_article/` folder:

- `results_florence.json.gz`
- `results_milan.json.gz`
- `results_rome.json.gz`

Each file contains a nested dictionary structured as follows:

```python
results[navigation_service][non_routed_routing_strategy][n_vehicles][measure][routed_percentage] = [rep_1, ..., rep_10]
```

### Structure Description

* **`navigation_service`**
  Navigation system used for routed vehicles.
  Examples: `gmaps`, `bing`, `mapbox`, `tomtomFastest`, `tomtomEco`, `tomtomShort`, `IGfastest`.

* **`non_routed_routing_strategy`**
  Routing criterion used for non-routed vehicles (based on `duarouter`).
  Examples: `myduaw3`, `myduaw5`, `myduaw7`.

* **`n_vehicles`**
  Total number of vehicles in the simulation, used to model different traffic loads.
  Values range from `5000` to `100000`.

- **`measure`**  
  Metric computed from the simulation. Key measures include:

  - `total_co2`
  - `total_co2_routed`
  - `total_co2_non_routed`
  - `total_duration`
  - `total_waiting_time`
  - `edge_co2_entropy`
  - `edge_co2_gini`
  - `redundancy`

  Additional measures are also available in the results files.

* **`routed_percentage`**
  Percentage of vehicles following navigation recommendations.
  Values: `0`, `10`, `20`, ..., `100`.

- **Repetitions**  
  Each configuration is repeated **10 times**, and the dictionary stores a list of values corresponding to these repetitions.  
  Note that when the routed percentage is **100%**, only a single value is stored, as no randomness is involved in the routing (i.e., no `duarouter` variability).

---

### Example

```python
results["gmaps"]["myduaw5"]["10000"]["total_co2"]["30"]
```

This returns a list of 10 values corresponding to:

* navigation service: **Google Maps (`gmaps`)**
* non-routed routing strategy: **`myduaw5`**
* number of vehicles: **10,000**
* routed vehicles: **30%**
* metric: **total CO2 emissions**

---

### How to use

You can directly load the results dictionary and compute statistics (e.g., mean, variance) or generate plots without running SUMO simulations:

```python
import gzip
import json
import numpy as np

with gzip.open("results_article/results_milan.json.gz", "rt") as f:
    results = json.load(f)

values = results["gmaps"]["myduaw5"]["10000"]["total_co2"]["30"]
mean_value = np.mean(values)
```

For full reproducibility of figures in the paper, see:

* `5_compute_results.ipynb`
* `6_create_plots.ipynb`



<a id='setup' name='setup'></a>
## Setup

## How to install and configure SUMO (Simulation of Urban MObility) 🚗🚙🛻

<p align="center"><img width=70% src="https://raw.githubusercontent.com/eclipse/sumo/main/docs/web/docs/images/multiple-screenshots.png"></p>

### Install SUMO

Please always refer to the [SUMO Installation page](https://sumo.dlr.de/docs/Installing/index.html)
for the latest installation instructions.

#### > Windows

To install SUMO on Windows it is necessary to download the installer [here](https://sumo.dlr.de/docs/Downloads.php#windows) and run the executable.

#### > Linux

To install SUMO on Linux is it necessary to execute the following commands:

```
sudo add-apt-repository ppa:sumo/stable
sudo apt-get update
sudo apt-get install sumo sumo-tools sumo-doc
```

#### > macOS

SUMO can be installed on macOS via [Homebrew](https://brew.sh/).

You can install and update Homebrew as following:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
brew update
brew install --cask xquartz
```
To install SUMO:
```
brew tap dlr-ts/sumo
brew install sumo
```


### Configure SUMO

After installing SUMO you must configure your `PATH` and `SUMO_HOME` environment variables.

Suppose you installed SUMO at `/your/path/to/sumo-<version>`

#### > Windows
1. On the Windows search box search for "Edit the system environment variables" option and open it;
2. Under user variables select `PATH` and click Edit. If no such variable exists you must create it with the New-Button; 
3. Append `;/your/path/to/sumo-<version>/bin` to the end of the `PATH` value (do not delete the existing values);
4. Under user variables select `SUMO_HOME` and click Edit. If no such variable exists you must create it with the New-Button;
5. Set `/your/path/to/sumo-<version>` as the value of the `SUMO_HOME` variable.

#### > Linux

1. Open a file explorer and go to `/home/YOUR_NAME/`;
2. Open the file named `.bashrc` with a text editor;
3. Place this code export `SUMO_HOME="/your/path/to/sumo-<version>/"` somewhere in the file and save;
4. Reboot your computer.


#### > macOS

First you need to determine which shell (bash or zsh) you are currently working with. In a terminal, `type ps -p $$`.

##### ZSH

In a Terminal, execute the following steps:

1. Run the command `open ~/.zshrc`, this will open the `.zshrc` file in TextEdit;
2. Add the following line to that document: `export SUMO_HOME="/your/path/to/sumo-<version>"` and save it;
3. Apply the changes by entering: `source ~/.zshrc`.

##### bash

In a Terminal, execute the following steps:

1. Run the command `open ~/.bash_profile`, this will open the `.bash_profile` file in TextEdit;
2. Add the following line to that document: `export SUMO_HOME="/your/path/to/sumo-<version>"` and save it;
3. Apply the changes by entering: `source ~/.bash_profile`.

<a id='data' name='data'></a>
## Data Availability
Please note that the OctoTelematics dataset utilized in our study is proprietary and not publicly available. Therefore, the original OD-matrices employed in this research cannot be included in this repository. However, we have provided the necessary code to generate an OD-matrix for Milan using a publicly accessible [dataset](https://ckan-sobigdata.d4science.org/dataset/gps_track_milan_italy). This code is flexible and can be adapted for use with any data source. Additionally, we offer a routine to create random OD matrices, which can be useful in scenarios lacking trajectory data.

Furthermore, due to proprietary restrictions, the specific navigation service suggestions used in our study cannot be included. Nonetheless, we have supplied the code to generate a fastest path assignment, replicating the functionality of a navigation service prototype. Moreover, we include a script to generate perturbations of the fastest paths for non-routed vehicles. This ensures that the code can be adapted and applied to various datasets and scenarios, facilitating research on navigation services' impact on urban traffic patterns and CO2 emissions.
