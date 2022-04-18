# Intro
This repo contains scrips of a digital twin of the Easter Bush Educational Solar Array at the University of Edinburgh (digital_twin.py), test runs for the simulation model of the array (AllYearLong.py), a simulation model of the whole solar farm not the educational array only (AllYearLong2.py) and a Demand Side Management Algorithm for the Easter Bush Campus (DemandResponse.py).

# How to run Digital_Twin.py
The simulation model of the solar array has been built using the open source PVLIB library. The model uses weather data such as the solar irradiances (GHI, DNI and DHI), in addition to the azimuth and zenith angles of the sun as inputs. These inputs are fetched from the weather API: Solcast. The access to Solcast’s data is granted with a special API key given by registering for a student license. The API key is denoted "API_KEY" and "API_KEY2" in the file.

The code will not run unless the API keys are inserted. 48 API calls can be made per day. Usually, 10 API calls are allowed per day however after exchanging emails with a member from Solcast, the API calls have been increased to 48.

The simulation model calculates the expected power output of the solar array for the current configuration and for other configurations as well. Different scenarios have been built, each representing a different tilt angle. The scenarios include modifying the tilt angle of the installation to match the optimal summer angle and the optimal winter angle. A single axis tracker system has also been added as a separate scenario. 

The digital twin operates in real-time and the outputs are generated every half hour. 

The data produced by the digital twin are published as JSON files on a GitHub public repo (the repo in question is called Demo-Repo) and displayed on the following online website:
https://digitaltwinpv.github.io/digitaltwinpv/

To be able to update the JSON data files in the GitHub repo an SSH key is required and has to be generated. This key is denoted as "access_key" in the file.

Latitude and Longitude parameters of the location in question (Easter Bush campus in this case) are also needed for the simulation model and to track the dawn and dusk times of the day.

# How to run AllYearLong2.py
This script consists in testing the simulation model of the Easter Bush Educational Solar Array that has been built in the script "Digital_Twin.py". 

The power output of the solar array has been calculated for a whole year based on TMY or Typical Meteorological Year weather data provided from Solcast as a CSV file (HourlyTmy.csv). The csv is turned into a dataframe and then filtered to contain the relevant information only. 

The result is plotted and analysed. 

# How to run DemandResponse.py
This script contains the Demand Response Algorithm of the Easter Bush Campus. The algorithm starts with devising the simulation model of the Easter Bush Solar Farm, not just the Educational Solar Array. The model has been built with PVLIB. The weather inputs of the model are provided from a dataframe that has been built by calculating typical values of the solar irradiances, the azimuth and zenith angles of the sun for the month of June. The historical data for the month of June are extracted from a CSV file downloaded from Solcast (HourlyTmy_June.csv). This CSV file is an extract of the historical TMY data "HourlyTmy.csv" downloaded as a CSV (mentioned in the AllYearLong2.py file). 

After getting the generation profile of the campus from the solar farm simulation model, the demand response algorithm is built by starting with scheduling the domestic heaters to scheduling the chillers and finally the freezer farm. This Demand Side Management algorithm is customised for the Easter Bush Campus. Therefore the schedules of the flexible loads, the cooling network schedule and other variables are personalised to the campus.

The final result of the script is a plot containing both the generation profile and the new demand profile adjusted to optimally utilise the generated electricity by the solar farm. 
# How to run AllYearLong.py
Similarly to "AllYearLong2.py". The following script tests the validity of the simulation model of the Easter Bush Solar Array that has been used to build the generation output of the Easter Bush Campus in the Demand response Algorithm.
# ...

