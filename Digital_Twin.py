import sys, numpy, time, schedule, datetime, pytz, requests, urllib, json
import pandas as pd
import matplotlib.pyplot as plt
import solcast, pvlib
import astral
from astral import LocationInfo
from astral.sun import sun
from requests.sessions import session
from github import Github

print(sys.version)
# ------------------------------------------------------------------------------------------------------------------------
# Github Acess
# Generated access token
access_token ='access_token_instered_here'

# Login into github account
login  = Github(access_token)

# Get the user
user  = login.get_user()

# Get the repository name
# Demo-Repo is for json files with timestamps
repository_name= "Demo-Repo" 

# Get the repo
repo = user.get_repo(repository_name)
# ------------------------------------------------------------------------------------------------------------------------

# Coordinates of the Location 
latitude=55.865408
longitude=-3.199696

# API Key for Solcast (for the Weather API)
API_KEY='API_KEY_inserted_here'
API_KEY2='API_KEY2_inserted_here'
# ------------------------------------------------------------------------------------------------------------------------

# Data about the Solar Array
# Solar Panels Data
tilt_angle = 20 # degrees
surface_azimuth = 180 # the panels are facing south

optimal_winter_tilt_angle = latitude + 15 # degrees
optimal_summer_tilt_angle = latitude - 15 # degrees

power_dc_solar_panel = 335 # Watts
power_dc_array_1 = 12 * power_dc_solar_panel
power_dc_array_2 = 12 * power_dc_solar_panel
total_dc_power_panels = power_dc_array_1 + power_dc_array_2

power_STC = 335 # Watts
power_NOCT = 253 # Watts
module_length = 1.698 # meters
module_width = 1.004 # meters
module_area = module_length * module_width
number_of_cells = 120
I_sc_ref = 10.20 # Amps
V_oc_ref = 42.6 # Volts
I_mp_ref = 9.69 # Amps
V_mp_ref = 34.6 # Volts

T_coef_I_sc = 0.05 # %/K
T_coef_V_oc = -0.29 # %/K
gamma_pdc_solar_panel = - 0.37 / 100 # -0.37 %/K
alpha_sc = T_coef_I_sc * I_sc_ref / 272.15 # A/ deg C
beta_oc = T_coef_V_oc * V_oc_ref / 272.15 # V/ deg C
gamma_pdc_solar_panel_celsius = gamma_pdc_solar_panel * power_STC / 272.15 # %/deg C

T_NOCT = 41 # degrees

# Inverter Parameters
inverter_efficiency = 0.968 # 96.8%
inverter_power_dc = 8000 # Watts
#inverter_power_ac = 6000
inverter_power_ac = 7000 # Trying to see if that is a good inverter for the installation
#inverter_power_dc = 6900 # Watts

Vac = 230 # Volts
Pso = 2 # Watts
Vdco = 330 # Rated input current Volts
Pnt = 2 # Watts
Vdcmax = 600 # Volts
Idcmax = 11 # Amps
Mppt_low = 90 # Min MPPT Volts
Mppt_high = 520 # Max MPPT Volts

C0 = 0
C1 = 0
C2 = 0
C3 = 0

# Defining an Inverter and a Module Object
module_parameters = {'pdc0': total_dc_power_panels, 
                     'gamma_pdc': gamma_pdc_solar_panel_celsius}

inverter_parameters = {'pdc0': inverter_power_dc, 
                       'eta_inv_nom': inverter_efficiency}

module_parameters_extended = pd.DataFrame({'Technology': 'Mono-c-Si',
                              'Bifacial': 0, 
                              'STC': power_STC, 
                              'PTC': power_NOCT, 
                              'A_c': module_area, 
                              'Length': module_length, 
                              'Width': module_width, 
                              'N_s': number_of_cells, 
                              'I_sc_ref': I_sc_ref, 
                              'V_oc_ref': V_oc_ref,
                              'I_mp_ref': I_mp_ref,
                              'V_mp_ref': V_mp_ref,
                              'alpha_sc': alpha_sc,
                              'beta_oc': beta_oc,
                              'T_NOCT': T_NOCT,
                              'BIPV': False,
                              'gamma_r': gamma_pdc_solar_panel_celsius}, index=[0])

inverter_parameters_extended = pd.DataFrame({'Vac': Vac,
                                             'Pso': Pso,
                                             'Paco': inverter_power_ac,
                                             'Pdco': inverter_power_dc,
                                             'Vdco': Vdco,
                                             'C0': C0,
                                             'C1': C1,
                                             'C2': C2,
                                             'C3': C3,
                                             'Pnt': Pnt,
                                             'Vdcmax': Vdcmax,
                                             'Idcmax': Idcmax,
                                             'Mppt_low': Mppt_low,
                                             'Mppt_high': Mppt_high}, index=[0])

new_module = module_parameters_extended.transpose()
modules = pvlib.pvsystem.retrieve_sam('cecmod')
my_new_modules = modules.copy()
my_new_modules['New Module'] = pd.Series(numpy.float64)
my_new_modules['New Module'] = new_module

new_inverter = inverter_parameters_extended.transpose()
inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
my_new_inverters = inverters.copy()
my_new_inverters['New Inverter'] = pd.Series(numpy.float64)
my_new_inverters['New Inverter'] = new_inverter

# Defining a location for PVLIB
location = pvlib.location.Location(latitude=latitude, longitude=longitude)
# ------------------------------------------------------------------------------------------------------------------------

# Functions that will be used in the digital twin loop
def radiation_live_data_f24(latitude, longitude, API_KEY):
    live_radiation=solcast.get_radiation_estimated_actuals(latitude, longitude, API_KEY)
    live_radiation_data=live_radiation.estimated_actuals
    live_radiation_data_df = pd.DataFrame(live_radiation_data)
    radiation_data_f24_yesterday_df = live_radiation_data_df.head(48)
    return radiation_data_f24_yesterday_df

def radiation_forecast_data_f24(latitude, longitude, API_KEY):
    radiation_data=solcast.get_radiation_forecasts(latitude, longitude, API_KEY)
    seven_day_forecast = radiation_data.forecasts
    forecast_data_df = pd.DataFrame(seven_day_forecast)
    radiation_data_f24_tomorrow_df = forecast_data_df.head(48)
    return radiation_data_f24_tomorrow_df

def get_number_of_iterations(dusk, dawn):
    dateTimeDifference = dusk-dawn
    dateTimeDifferencePerCall=dateTimeDifference/24
    dateTimeDifferenceInMinutes = round(dateTimeDifferencePerCall.total_seconds() / 60)
    number_of_iterations=round(dateTimeDifferenceInMinutes/30)
    if (number_of_iterations < dateTimeDifferenceInMinutes/30):
        number_of_iterations = number_of_iterations + 1
    return number_of_iterations

def get_carbon_intensity_SScotland():
    sscotland_carbon_url="https://api.carbonintensity.org.uk/regional/regionid/2"
    sscot = requests.get(sscotland_carbon_url)
    sscot_data = sscot.json()
    carbon_sscot = sscot_data['data'][0]['data'][0].get('intensity').get('forecast')
    return carbon_sscot
# ------------------------------------------------------------------------------------------------------------------------

# The code from here till the end of the script is in a while loop that is looping 24/7 (while(True) ...)
while(True):
    # Using Astral to get the dawn and dusk times 
    loc = LocationInfo(name='Easter Bush Campus', 
                       region='Edinburgh, UK', 
                       timezone='Europe/London',
                       latitude=55.865408, 
                       longitude=-3.199696)
    s = sun(loc.observer, date=datetime.datetime.today(), tzinfo=loc.timezone)

    # Getting the time "now" by taking into consideration the timezones 
    timezone = pytz.timezone("Europe/London")
    UTC = pytz.timezone("UTC")
    time_now_tz = datetime.datetime.now(timezone)
    print(time_now_tz)
    print(s['dusk'])

    # Number of Iterations
    number_of_iterations=get_number_of_iterations(s['dusk'], s['dawn'])
    print("The number of iterations is: ",number_of_iterations)


    # The Digital twin real time loop starts here
    while (s['dawn']<time_now_tz<s['dusk']): # It is a while loop but for trials we put an "if"
        
        data_df = radiation_forecast_data_f24(latitude, 
                                              longitude, 
                                              API_KEY)
        
        live_radiation_data_df = radiation_live_data_f24(latitude, 
                                                         longitude, 
                                                         API_KEY)

        radiation_data = data_df[['ghi', 
                                  'dni', 
                                  'dhi', 
                                  'air_temp', 
                                  'zenith', 
                                  'azimuth', 
                                  'cloud_opacity', 
                                  'period_end']]
        #print(radiation_data)
        
        # A Pandas Series is added to the dataframe for the period end time in the local timezone
        # A Pandas Series is added to the dataframe for the wind speed data
        radiation_data['period_end_local_timezone'] = pd.Series()
        radiation_data['wind_speed']=pd.Series()
        
        live_radiation_data = live_radiation_data_df[['ghi', 
                                                      'dni', 
                                                      'dhi', 
                                                      'cloud_opacity', 
                                                      'period_end']]
        
        live_radiation_data['period_end_local_timezone'] = pd.Series()
        live_radiation_data['wind_speed'] = pd.Series()
        
        # for loop for the time conversion from UTC to local timezone
        for index in range(len(radiation_data)):
            radiation_data.iloc[index, 9] = 1
            live_radiation_data.iloc[index, 6] = 1
            old_time = radiation_data.iloc[index,7].astimezone(UTC)
            radiation_data.iloc[index,8] = old_time.astimezone(timezone)
            old_time_2 = live_radiation_data.iloc[index,4].astimezone(UTC)
            live_radiation_data.iloc[index,5] = old_time_2.astimezone(timezone)
            
        
        #print(radiation_data)
        #print(live_radiation_data)
        
        # Weather data format
        weather_data = live_radiation_data[['ghi', 
                                            'dni', 
                                            'dhi', 
                                            'period_end_local_timezone', 
                                            'wind_speed']]
        weather_data = weather_data.rename(columns={'period_end_local_timezone':'end_period'})
        weather_data = weather_data.set_index(['end_period'])
        
        # Here we add the calculations of the POA for one or different angles (also for Tracking)
        # Get the POA (Plane Of Array) Irradiance (With fixed Mount)
        
        df_poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt = tilt_angle,  # tilted 20 degrees from horizontal
            surface_azimuth = surface_azimuth,  # facing South
            dni = radiation_data['dni'],
            ghi = radiation_data['ghi'],
            dhi = radiation_data['dhi'],
            solar_zenith = radiation_data['zenith'],
            solar_azimuth = radiation_data['azimuth'],
            model='isotropic')

        df_poa_winter = pvlib.irradiance.get_total_irradiance(
            surface_tilt = optimal_winter_tilt_angle,  # tilted with an optimal tilt angle for winter
            surface_azimuth = surface_azimuth,  # facing South
            dni = radiation_data['dni'],
            ghi = radiation_data['ghi'],
            dhi = radiation_data['dhi'],
            solar_zenith = radiation_data['zenith'],
            solar_azimuth = radiation_data['azimuth'],
            model='isotropic')

        df_poa_summer = pvlib.irradiance.get_total_irradiance(
            surface_tilt = optimal_summer_tilt_angle,  # tilted with an optimal tilt angle for summer
            surface_azimuth = surface_azimuth,  # facing South
            dni = radiation_data['dni'],
            ghi = radiation_data['ghi'],
            dhi = radiation_data['dhi'],
            solar_zenith = radiation_data['zenith'],
            solar_azimuth = radiation_data['azimuth'],
            model='isotropic')

        # Get the POA Irradiance (With Single Axis Tracking)
        tracker_data = pvlib.tracking.singleaxis(
            radiation_data['zenith'],
            radiation_data['azimuth'],
            axis_azimuth = 180,  # axis is aligned N-S
            )  # leave the rest of the singleaxis parameters like backtrack and gcr at their defaults
        tilt = tracker_data['surface_tilt'].fillna(0)
        azimuth = tracker_data['surface_azimuth'].fillna(0)

        df_poa_tracker = pvlib.irradiance.get_total_irradiance(
            surface_tilt = tilt,  # time series for tracking array
            surface_azimuth = azimuth,  # time series for tracking array
            dni = radiation_data['dni'],
            ghi = radiation_data['ghi'],
            dhi = radiation_data['dhi'],
            solar_zenith = radiation_data['zenith'],
            solar_azimuth = radiation_data['azimuth'])
        tracker_poa = df_poa_tracker['poa_global']

        # Then we add the calculations of the cell temperature 
        # Calculate Cell/Module Temperature for all 4 configurations
        all_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']
        parameters = all_parameters['open_rack_glass_polymer']

        cell_temperature_tracker = pvlib.temperature.sapm_cell(
            tracker_poa, 
            radiation_data['air_temp'], 
            radiation_data['wind_speed'], **parameters)

        cell_temperature_fixed = pvlib.temperature.sapm_cell(
            df_poa['poa_global'], 
            radiation_data['air_temp'], 
            radiation_data['wind_speed'], **parameters)

        cell_temperature_winter = pvlib.temperature.sapm_cell(
            df_poa_winter['poa_global'], 
            radiation_data['air_temp'], 
            radiation_data['wind_speed'], **parameters)

        cell_temperature_summer = pvlib.temperature.sapm_cell(
            df_poa_summer['poa_global'], 
            radiation_data['air_temp'], 
            radiation_data['wind_speed'], **parameters)
        
        # Calculate the power output of the array

        # PVWatts Method
        # With fixed panels
        dc_power_output = pvlib.pvsystem.pvwatts_dc(df_poa['poa_global'],
                                                    cell_temperature_fixed, 
                                                    total_dc_power_panels, 
                                                    gamma_pdc_solar_panel_celsius)
        ac_power_output = pvlib.inverter.pvwatts(dc_power_output, 
                                                 inverter_power_ac/inverter_efficiency, 
                                                 inverter_efficiency, 
                                                 eta_inv_ref=0.9637)

        dc_power_winter = pvlib.pvsystem.pvwatts_dc(df_poa_winter['poa_global'], 
                                                    cell_temperature_winter, 
                                                    total_dc_power_panels, 
                                                    gamma_pdc_solar_panel_celsius)
        ac_power_winter = pvlib.inverter.pvwatts(dc_power_winter, 
                                                 inverter_power_ac/inverter_efficiency, 
                                                 inverter_efficiency, 
                                                 eta_inv_ref=0.9637)

        dc_power_summer = pvlib.pvsystem.pvwatts_dc(df_poa_summer['poa_global'], 
                                                    cell_temperature_summer, 
                                                    total_dc_power_panels, 
                                                    gamma_pdc_solar_panel_celsius)
        ac_power_summer = pvlib.inverter.pvwatts(dc_power_summer, 
                                                 inverter_power_ac/inverter_efficiency,
                                                 inverter_efficiency, 
                                                 eta_inv_ref=0.9637)

        # With Single Axis Tracking
        dc_power_tracker = pvlib.pvsystem.pvwatts_dc(tracker_poa, 
                                                     cell_temperature_tracker, 
                                                     total_dc_power_panels, 
                                                     gamma_pdc_solar_panel_celsius)
        ac_power_tracker = pvlib.inverter.pvwatts(dc_power_tracker, 
                                                  inverter_power_ac/inverter_efficiency, 
                                                  inverter_efficiency, 
                                                  eta_inv_ref=0.9637)

        # We transform the Series into dataframes
        ac_power_output_df = ac_power_output.to_frame()
        ac_power_winter_df = ac_power_winter.to_frame()
        ac_power_summer_df = ac_power_summer.to_frame()
        ac_power_tracker_df = ac_power_tracker.to_frame()
        
        # We rename the column to each new dataframe
        ac_power_output_df.columns = ['AC_Power']
        ac_power_summer_df.columns = ['AC_Power']
        ac_power_winter_df.columns = ['AC_Power']
        ac_power_tracker_df.columns = ['AC_Power']
        
        # We add time as a column to each new dataframe
        ac_power_output_df['end_period'] = pd.Series(numpy.float64)
        ac_power_summer_df['end_period'] = pd.Series(numpy.float64)
        ac_power_winter_df['end_period'] = pd.Series(numpy.float64)
        ac_power_tracker_df['end_period'] = pd.Series(numpy.float64)
        
        ac_power_output_df['end_period'] = radiation_data['period_end_local_timezone'].fillna(0)
        ac_power_winter_df['end_period'] = radiation_data['period_end_local_timezone'].fillna(0)
        ac_power_summer_df['end_period'] = radiation_data['period_end_local_timezone'].fillna(0)
        ac_power_tracker_df['end_period'] = radiation_data['period_end_local_timezone'].fillna(0)
        
        # The dataframes are converted into json to be used for the website
        print(ac_power_output_df)
        ac_power_output_js = ac_power_output_df.to_json(orient = 'records')
        ac_power_winter_js = ac_power_winter_df.to_json(orient = 'records')
        ac_power_summer_js = ac_power_summer_df.to_json(orient = 'records')
        ac_power_tracker_js = ac_power_tracker_df.to_json(orient = 'records')
        
        
        # Update the files in GitHub
        ac_power_output_contents = repo.get_contents("ac_power_output_data.json")
        repo.update_file("ac_power_output_data.json",
                         "commit_message", 
                         ac_power_output_js, 
                         ac_power_output_contents.sha)
        ac_power_winter_contents = repo.get_contents("ac_power_winter_data.json")
        repo.update_file("ac_power_winter_data.json", 
                         "commit_message", 
                         ac_power_winter_js, 
                         ac_power_winter_contents.sha)
        ac_power_summer_contents = repo.get_contents("ac_power_summer_data.json")
        repo.update_file("ac_power_summer_data.json", 
                         "commit_message", 
                         ac_power_summer_js, 
                         ac_power_summer_contents.sha)
        ac_power_tracker_contents = repo.get_contents("ac_power_tracker_data.json")
        repo.update_file("ac_power_tracker_data.json", 
                         "commit_message", 
                         ac_power_tracker_js, 
                         ac_power_tracker_contents.sha)

        
        # Get the total carbon emissions predicted to be saved for the next 24 hrs
        total = ac_power_output_df['AC_Power'].sum()
        carbon_emissions = get_carbon_intensity_SScotland()
        
        
        # This is the value that will displayed on the website, it needs to be in a json format
        carbon_saved = round(carbon_emissions * total,3)
        carbon_emissions_js = json.dumps(carbon_saved)
        
        # Update the file on GitHub
        carbon_emissions_contents = repo.get_contents("carbon_data.json")
        repo.update_file("carbon_data.json", 
                         "commit_message", 
                         carbon_emissions_js, 
                         carbon_emissions_contents.sha)
        
        # ModelChain Method
        # Done only with fixed panels & 20 deg tilt angle
        system = pvlib.pvsystem.PVSystem(name='Easter Bush Educational Array',
                                    module = my_new_modules['New Module'],
                                    module_parameters = {'pdc0': power_STC, 
                                                         'gamma_pdc': gamma_pdc_solar_panel_celsius},
                                    surface_tilt = tilt_angle,
                                    surface_azimuth = surface_azimuth,
                                    temperature_model_parameters = parameters,
                                    inverter = my_new_inverters['New Inverter'],
                                    inverter_parameters = {'pdc0': inverter_power_dc, 
                                                           'eta_inv_nom': inverter_efficiency},
                                    modules_per_string = 12,
                                    strings_per_inverter = 2)
        
        mc = pvlib.modelchain.ModelChain(system, location,
                                    aoi_model='physical', spectral_model='no_loss')

        mc.run_model(weather_data)
        
        # The Pandas Series is converted into a dataframe then to a json to be used for the website
        modelchain_result = mc.results.ac.to_frame()
        modelchain_result.reset_index(inplace=True)
        
        print('The power generated yesterday by the solar array is: ')
        print(modelchain_result)
        #print(modelchain_result.loc[::-1])
        
        #JSON Data
        modelchain_result_js = modelchain_result.loc[::-1].to_json(orient = 'records')
        modelchain_result_contents = repo.get_contents("modelchain_data.json")
        repo.update_file("modelchain_data.json", 
                         "commit_message", 
                         modelchain_result_js,
                         modelchain_result_contents.sha)
        
        index=1
        starttime_2 = time.time()
        
        # This while loop is responsible for the real time response of the Digital twin
        # Waits for 30 mins to retrieve and display data
        while(index <= number_of_iterations):
            print("The index is: ", index)
            print('The half hourly forecast data is: ')
            half_hourly_forecast_data = radiation_data.head(index+number_of_iterations)
            print(half_hourly_forecast_data)
            
            # The dataframes are converted to json for the website and updated on GitHub
            half_hourly_AC_power = ac_power_output_df.head(index+number_of_iterations)
            half_hourly_power_js = half_hourly_AC_power.to_json(orient = 'records')
            half_hourly_power_contents = repo.get_contents("half_hourly_data.json")
            repo.update_file("half_hourly_data.json", 
                             "commit_message", 
                             half_hourly_power_js, 
                             half_hourly_power_contents.sha)
            
            print('The AC Power generated by the Solar Array is: ')
            print(half_hourly_AC_power)
            
            # Carbon emissions saved
            carbon_emission = get_carbon_intensity_SScotland()
            total_1 = half_hourly_AC_power['AC_Power'].sum()
            carbon_emission_saved = round(total_1 * carbon_emission,3)
            
            print('The total carbon emissions saved is equal to: ')
            print(carbon_emission_saved)
            
            print("Small loop time: ", datetime.datetime.fromtimestamp(time.time()))
            time.sleep(60*30-((time.time() - starttime_2) % 60.0)) # Wait for 30 minute
            index+=1

