import requests
import json
import time
import datetime
import teslapy

# Error message with truncated data.
def printerror(error, err): 
    print(str(err).split("}")[0], "}\n", datetime.datetime.now().strftime( "%a %H:%M:%S %p" ), error)

# Used to add a timestamp() to the output messages
def timestamp():
    return datetime.datetime.now().strftime( "%a %H:%M:%S %p") 

# Used to wake the car before issuing API calls that require the car to be awake.
def wake(car):
    try:
        car.sync_wake_up()
    except teslapy.VehicleError as e:
        printerror("Failed to wake", e)
        return(False)
    return(True)

def start_charging(car):
    try:
        wake(car)
        car.command('START_CHARGE')
    except teslapy.VehicleError as e: printerror("V: ", e)
    except teslapy.HTTPError as e: printerror("H: ", e)

def stop_charging(car):
    try:
        wake(car)
        car.command('STOP_CHARGE')
    except teslapy.VehicleError as e: printerror("V: ", e)
    except teslapy.HTTPError as e: printerror("H: ", e)

def set_amps(car, amps):
    try:
        wake(car)
        car.command('CHARGING_AMPS', charging_amps=amps)
    except teslapy.VehicleError as e: printerror("V: ", e)
    except teslapy.HTTPError as e: printerror("H: ", e)

# Checks if the current time is in the approved rage of start_time and end_time.
# Use this to set appropriate time windows for power rates and solar power generation periods.
def charging_time(start_time, end_time):
    time_now = datetime.datetime.now()
    if time_now > start_time and time_now < end_time:
        print(timestamp(),"Time to charge.")
        return(True)
    print(timestamp(),"Not time to charge.")
    return(False)

# This function could be extended to determine if the charger is plugged in or not.
def charging_status(charge_data):
    if charge_data['charging_state'] == "Charging":
        return True
    return False

# Display charging information.
def charge_info(charge_data):
    print( "\nLevel:",
    charge_data['battery_level'], "%, Limit",
    charge_data['charge_limit_soc'], "%,",
    charge_data['charge_rate'], "KPH",
    charge_data['charger_voltage'], "Volts",
    charge_data['charge_energy_added'], "kWh added,")
    print(charge_data['charger_actual_current'], "of a possible",
    charge_data['charge_current_request_max'], "Amps,",
    charge_data['time_to_full_charge'], "Hours remaining\n" )

# URL for the Solar API endpoint to retrieve current data using your Fronius inverter's IP.
solar_api_url = "http://<your_fronius_inverter_IP>/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
buffer = 1750               # Power in Watts to reserve for home usage spikes.
min_charge_rate = 3600      # Power in Watts to set as the minimum charge rate. A function of amps*volts*phases, e.g. 5*240*3 - 3600 
min_charge_amps = 5         # Amps that correspond to the minimum charge rate. 5 amps on 3 phase in Australia.
max_charge_amps = 16        # Amps that correspond to the maximum charge rate. 16 amps on 3 phase in Australia.
min_solar = 6000            # Power in Watts from solar generation before you consider to start charing the car.
current_charge_amps = 0     # Used to store what number of amps the car is charging at.
new_charge_amps = 0         # Used to calculate and store the next desired charge rate.
volts = 720                 # Your country's voltage * the number of phases, 240 * 3 in this case.
restart_charge_time = 300   # Seconds to wait if the charging needs to be stopped due to the lack of available solar power.
refresh_rate = 60           # Seconds to wait before checking for solar power changes
charging = False            # Simply boolean to determine if the car is charging or not.
now = datetime.datetime.now()   # Time of program start.
start_time = now.replace(hour=8, minute=0, second=0, microsecond=0) # Earliest time to start charging.
end_time = now.replace(hour=16, minute=0, second=0, microsecond=0)  # Latest time to be charging.
retry = teslapy.Retry(total=3, status_forcelist=(500,502,503,504))  # Teslapy parameters.

# Main program that sets up the Tesla API tokens on the first run.
# It will open a Tesla URL in a browser to authenticate your account (works with 2 factor).
# After authentication you need to copy the URL from the browser and paste it on the command line as instructed
with teslapy.Tesla('<your_email_address_for_tesla_account>', retry=retry, timeout=30) as tesla:
    tesla.fetch_token()
    vehicles = tesla.vehicle_list()
    car = vehicles[0]
    print(timestamp(),"Connecting to", car.get_vehicle_summary()['display_name'])
    wake(car)
    print(timestamp(),"Car is awake!")
    charge_data = car.get_vehicle_data()['charge_state']
    charge_info(charge_data)
    
    # Check if the car is charging to set variables to ensure correct amps for avaiable power usage calculation
    if charging_status(charge_data):
        current_charge_amps = charge_data['charge_amps']
        charging = True
    else:
        set_amps(car, 5)    # Always start the car at the lowest level of charge.
        
    while charging_time(start_time, end_time)==True:
        # Send a request to the Solar API endpoint to retrieve the current inverter information and load into a JSON variable.
        response = requests.get(solar_api_url)
        solar_data = json.loads(response.text)

        # Extract the current solar energy, house power draw and grid export numbers in Watts.
        # Note that house_power and grid_power (when exporting) are negative numbers.
        solar_power = solar_data["Body"]["Data"]["Inverters"]["1"]["P"]
        house_power = solar_data["Body"]["Data"]["Site"]["P_Load"]
        grid_power = solar_data["Body"]["Data"]["Site"]["P_Grid"]
        
        # Print the current charging rate and inverter information.
        print(" ")
        print(timestamp(),"Current amps",current_charge_amps,"- charging at",current_charge_amps*volts,"Watts")
        print(timestamp(),"Current Solar Power: {} W".format(solar_power))
        print(timestamp(),"Current House Power: {} W".format(-house_power))
        print(timestamp(),"Current Grid Power:  {} W".format(grid_power),"\n")
        
        # Only proceed if there is enough solar power to make charging reliable
        if solar_power > min_solar:
            print(timestamp(),"Enough solar")
            # We need to add the exporting power and the car charge power (part of house consumption) otherwise if you just look at
            # the grid export it will be too low as soon as we start to charge and consume that capacity. Thus the charging will
            # constantly start and stop.
            if (-grid_power + current_charge_amps*volts) > (min_charge_rate+buffer):
                print(timestamp(),"Enough excess solar")
                # Calculate the desired charge amps by using the available solar power (including car charge power) minus the buffer.
                new_charge_amps = int((-grid_power + (current_charge_amps*volts) - buffer)/volts)
                # Large solar installations may be able to provide more power than the charger allows, so reset to max amps
                if new_charge_amps > max_charge_amps:
                    new_charge_amps = max_charge_amps
                # Start charging at the desired amps or change the amps if already charging.
                if charging == False:
                    print(timestamp(),"Starting charging at", new_charge_amps, "amps")
                    set_amps(car, new_charge_amps)
                    current_charge_amps = new_charge_amps
                    start_charging(car)
                    charging = True
                else:
                    # During clear sky period you will have stable power, so only call the API if there is a change.
                    if current_charge_amps != new_charge_amps:
                        set_amps(car, new_charge_amps)
                        print(timestamp(),"Changed charge rate from", current_charge_amps, "amps to", new_charge_amps, "amps\n")                        
                        current_charge_amps = new_charge_amps
                    else:
                        print(timestamp(),"Keeping charge rate at",new_charge_amps, "amps\n")
            # House power draw too high or not enough buffer.
            elif charging == True:
                stop_charging(car)
                print(timestamp(),"Charging stopped - House draw is too high, or not enough buffer")
                current_charge_amps = 0
                charging = False
                # If it's cloudy or at the edge of enough excess power then wait some time.
                print(timestamp(),"Waiting for",restart_charge_time,"s before checking again.\n")
                time.sleep(restart_charge_time)
            else:
                print(timestamp(),"Not charging. Excess house draw.\n")
        # Not enough solar, so can't charge or have to stop charging.
        elif charging == True:
            stop_charging(car)
            print(timestamp(),"Charging stopped, not enough solar")
            current_charge_amps = 0
            charging = False
            # Wait some time for more solar.
            print(timestamp(),"Waiting for",restart_charge_time,"s before checking again.\n")
            time.sleep(restart_charge_time) 
        else:
            print(timestamp(),"Not charging. Not enough solar.\n")
        time.sleep(refresh_rate)
