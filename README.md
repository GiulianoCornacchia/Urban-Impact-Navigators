<div align="center">
  <h1>Navigation Services Amplify Concentration <br> of Traffic and Emissions in Our Cities</h1> 
  <img src="images/img_intro2.webp" width="700">
</div>

### Authors:

* Giuliano Cornacchia <sup>1,2</sup> [<img src="https://img.shields.io/badge/ORCID-0000--0003--2263--7654-brightgreen?logo=orcid&logoColor=white" alt="ORCID" height="16">](https://orcid.org/0000-0003-2263-7654)

* Mirco Nanni <sup>1</sup> [<img src="https://img.shields.io/badge/ORCID-0000--0003--3534--4332-brightgreen?logo=orcid&logoColor=white" alt="ORCID" height="16">](https://orcid.org/0000-0003-3534-4332)

* Dino Pedreschi <sup>2</sup> [<img src="https://img.shields.io/badge/ORCID-0000--0003--4801--3225-brightgreen?logo=orcid&logoColor=white" alt="ORCID" height="16">](https://orcid.org/0000-0003-4801-3225)

* Luca Pappalardo <sup>1,3</sup> [<img src="https://img.shields.io/badge/ORCID-0000--0002--1547--6007-brightgreen?logo=orcid&logoColor=white" alt="ORCID" height="16">](https://orcid.org/0000-0002-1547-6007)


Affiliations:<br>
<sup>1</sup> Institute of Information Science and Technologies (ISTI), National Research Council (CNR), Pisa, Italy <br>
<sup>2</sup> Department of Computer Science, University of Pisa, Pisa, Italy <br>
<sup>3</sup> Scuola Normale Superiore, Pisa, Italy <br>

____

Pre-print available [here](XXX).

____


The proliferation of human-AI ecosystems, such as navigation services, raises concerns about their large-scale social and environmental impacts. Our study employs a simulation framework to assess how navigation services influence road network usage and CO2 emissions in urban environments. This repository provides the necessary Python code and tools to reproduce our analysis using the SUMO mobility simulator, offering insights into the collective impact of navigation services at varying adoption rates. To use the code and replicate the analysis, follow the instructions provided in this README file.

## Built with

![python](https://img.shields.io/badge/Python-3776AB.svg?style=for-the-badge&logo=Python&logoColor=white)
![jupyter](https://img.shields.io/badge/Jupyter-F37626.svg?style=for-the-badge&logo=Jupyter&logoColor=white)
![numpy](https://img.shields.io/badge/NumPy-013243.svg?style=for-the-badge&logo=NumPy&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![osm](https://img.shields.io/badge/OpenStreetMap-7EBC6F.svg?style=for-the-badge&logo=OpenStreetMap&logoColor=white)


<a id='toc' name='toc'></a>
# Table of Contents

 - [Abstract](#abstract)
 - [Usage](#usage)
 - [Setup](#setup)
 - [Data Availability](#data)
---




<a id='abstract' name='abstract'></a>
## Abstract

The proliferation of human-AI ecosystems involving human interaction with algorithms, such as assistants and recommenders, raises concerns about large-scale social behaviour. Despite evidence of such phenomena across several contexts, the collective impact of GPS navigation services remains unclear: while beneficial to the user, they can also cause chaos if too many vehicles are driven through the same few roads.  
Our study employs a simulation framework to assess navigation services' influence on road network usage and CO2 emissions. The results demonstrate a universal pattern of amplified conformity: increasing adoption rates of navigation services cause a reduction of route diversity of mobile travellers and increased concentration of traffic and emissions on fewer roads, thus exacerbating an unequal distribution of negative externalities on selected neighbourhoods.
Although navigation services recommendations can help reduce CO2 emissions when their adoption rate is low, these benefits diminish or even disappear when the adoption rate is high and exceeds a certain city- and service-dependent threshold.
We summarize these discoveries in a non-linear function that connects the marginal increase of conformity with the marginal reduction in CO2 emissions.
Our simulation approach addresses the challenges posed by the complexity of transportation systems and the lack of data and algorithmic transparency.






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
Please note that the OctoTelematics dataset utilized in our study is proprietary and not publicly available. Therefore, the original OD-matrices employed in this research cannot be included in this repository. However, we have provided the necessary code to generate a realistic OD-matrix for Milan using publicly accessible datasets. This code is flexible and can be adapted for use with any data source. Additionally, we offer a routine to create random OD matrices, which can be useful in scenarios lacking trajectory data.

Furthermore, due to proprietary restrictions, the specific navigation service suggestions used in our study cannot be included. Nonetheless, we have supplied the code to generate a fastest path assignment, replicating the functionality of a navigation service prototype. Moreover, we include a script to generate perturbations of the fastest paths for non-routed vehicles. This ensures that the code can be adapted and applied to various datasets and scenarios, facilitating research on navigation services' impact on urban traffic patterns and CO2 emissions.
