import datetime, pytz, time, csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pvlib


latitude=55.865408
optimal_winter_tilt_angle = latitude + 15 # degrees
optimal_summer_tilt_angle = latitude - 15 # degrees

# Weather Data Monthly Average
hourly_tmy_df = pd.read_csv('HourlyTmy.csv')
#hourly_tmy_df = pd.read_csv('Hourly_TMY_June.csv')
weather_data = hourly_tmy_df[['PeriodEnd', 
                              'PeriodStart',
                              'AirTemp', 
                              'Azimuth', 
                              'CloudOpacity', 
                              'Dhi', 
                              'Dni', 
                              'Ghi', 
                              'WindSpeed10m', 
                              'Zenith']]

#weather_data = hourly_tmy_df[['PeriodEnd', 'PeriodStart','AirTemp', 'Azimuth', 'CloudOpacity', 'Dhi', 'Dni', 'Ghi', 'Zenith']]
#weather_data['wind_speed']=pd.Series()

'''for index in range(len(weather_data)):
    weather_data.iloc[index, 9] = 1

print(weather_data)'''

# Calculation of the Solar Power Generated by the Array

# Data regarding the solar panels and inverter
tilt_angle = 20 # degrees
surface_azimuth = 180 # degrees (panels facing south)

power_dc_solar_panel = 335 # Watts
power_dc_array = 20 * power_dc_solar_panel
dc_power_config_1 = 15 * power_dc_array
dc_power_config_2 = 14 * power_dc_array
total_dc_power_panels = dc_power_config_1 + dc_power_config_2

'''power_dc_array_1 = 12 * power_dc_solar_panel
power_dc_array_2 = 12 * power_dc_solar_panel
total_dc_power_panels = power_dc_array_1 + power_dc_array_2'''

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

# Inverter Parameters
inverter_efficiency = 0.983 # 98.3%
inverter_power_dc = 112000 # Watts
inverter_power_ac = 80000


'''inverter_efficiency = 0.968 # 96.8%
inverter_power_dc = 6900 # Watts
inverter_power_ac = 6000'''


# Get the POA (Plane Of Array) Irradiance (With fixed Mount)
df_poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt = tilt_angle,  # tilted 20 degrees from horizontal
        surface_azimuth = surface_azimuth,  # facing South
        dni = weather_data['Dni'],
        ghi = weather_data['Ghi'],
        dhi = weather_data['Dhi'],
        solar_zenith = weather_data['Zenith'],
        solar_azimuth = weather_data['Azimuth'],
        model='isotropic')

# Then we add the calculations of the cell temperature 
# Calculate Cell/Module Temperature
all_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']
parameters = all_parameters['open_rack_glass_polymer']

cell_temperature_fixed = pvlib.temperature.sapm_cell(
    df_poa['poa_global'], weather_data['AirTemp'], weather_data['WindSpeed10m'], **parameters)

# Calculate the power output of the array

# PVWatts Method
# With fixed panels

dc_power_output_config_1 = pvlib.pvsystem.pvwatts_dc(df_poa['poa_global'], 
                                                     cell_temperature_fixed, 
                                                     dc_power_config_1, 
                                                     gamma_pdc_solar_panel_celsius)
#dc_power_output_config_1 = pvlib.pvsystem.pvwatts_dc(df_poa['poa_global'], cell_temperature_fixed, total_dc_power_panels, gamma_pdc_solar_panel_celsius)
ac_power_output_config_1 = pvlib.inverter.pvwatts(dc_power_output_config_1, 
                                                  inverter_power_ac/inverter_efficiency, 
                                                  inverter_efficiency, 
                                                  eta_inv_ref=0.9637)

dc_power_output_config_2 = pvlib.pvsystem.pvwatts_dc(df_poa['poa_global'], 
                                                     cell_temperature_fixed, 
                                                     dc_power_config_2, 
                                                     gamma_pdc_solar_panel_celsius)
ac_power_output_config_2 = pvlib.inverter.pvwatts(dc_power_output_config_2, 
                                                  inverter_power_ac/inverter_efficiency, 
                                                  inverter_efficiency, 
                                                  eta_inv_ref=0.9637)

ac_power_output = 14 * ac_power_output_config_1 + ac_power_output_config_2
#ac_power_output = ac_power_output_config_1
ac_power_output_df = ac_power_output.to_frame()
ac_power_output_df.columns = ['AC_Power']

start_date = datetime.datetime(2021, 1, 1)
end_date = datetime.datetime(2022, 1, 1)
delta = datetime.timedelta(hours=1)
for index in range(len(weather_data)):
    if start_date < end_date:
        weather_data.iloc[index, 0] = start_date
        start_date += delta

ac_power_output_df['end_period'] = pd.Series(np.float64)
ac_power_output_df['end_period'] = weather_data['PeriodEnd'].fillna(0)


print(ac_power_output_df)

ac_power_output_df['AC_Power'] = ac_power_output_df['AC_Power'].div(1e3)

total = round(ac_power_output_df['AC_Power'].sum(),2)
print('Total Energy (MWh) of the array: ', total)

ax = ac_power_output_df.plot(x = 'end_period', y = 'AC_Power')

plt.ylabel("AC Power (kW)")
plt.title("Power generated by the Easter Bush Solar Array all year long")
plt.show()

#ac_power_output_df.to_csv('Yearly_Hourly_power_output.csv', index = False)