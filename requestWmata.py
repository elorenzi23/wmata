import requests
import time

HEALTHY_STATUS = 200
MULTI_TRACK_STATION_CODE_MAP = {}
LINE_CODES = ['RD', 'BL', 'YL', 'OR', 'GR', 'SV']
API_KEY = 'b18ceda221c645d5bd1d5386f40ca0e1'
BASE_URL = 'https://api.wmata.com/'
HEADERS = {
    'api_key': API_KEY,
}
ARRIVAL_TIME_INDEX = 3
REFRESH_FREQUENCY = 5
WAIT_INTERVAL = .1
COUNTER_MAX = REFRESH_FREQUENCY/WAIT_INTERVAL

def on_keypress(event):
    global counter, station_index, line_index
    key = event.name
    if key == 's':
        print("received s")
        station_index += 1
        counter = COUNTER_MAX
    elif key == "l":
        print("received l")
        line_index = (line_index + 1) % len(LINE_CODES)
        station_index = 0
        counter = COUNTER_MAX
    else:
        print("Unknown key")
    
def sort_by_arrival(train_data):
    arrival_time = train_data[ARRIVAL_TIME_INDEX]
    if(arrival_time) == 'BRD':
        return -1
    elif(arrival_time) == 'ARR':
        return 0
    elif(arrival_time) == 'DLY':
        return 100
    elif(arrival_time) == '':
        return 50
    elif(arrival_time) == '---':
        return 51
    else:
        try:
            return int(arrival_time)
        except Exception as e:
            return 52

def construct_multi_track_station_code_maps(stations_data):
    MULTI_TRACK_STATION_CODE_MAP = {}
    stations_data_list = stations_data['Stations']
    for station in stations_data_list:
        station_name = station['Name']
        station_code = station['Code']
        for station_two in stations_data_list:
            station_two_name = station_two['Name']
            station_two_code = station_two['Code']
            if(station_name == station_two_name and station_code != station_two_code):
                MULTI_TRACK_STATION_CODE_MAP[station_code] = station_two_code

def get_station_data(line_index):
    stations_endpoint = "/Rail.svc/json/jStations/"
    #get all the station codes for the current line:
    line_code = LINE_CODES[line_index]
    stations_url = BASE_URL + stations_endpoint
    response = requests.get(stations_url, headers = HEADERS)
    filtered_station_data = []
    if response.status_code == HEALTHY_STATUS:
        stations_data = response.json()
        construct_multi_track_station_code_maps(stations_data)
        for elem in stations_data['Stations']:
            if elem['LineCode1'] == line_code or elem['LineCode2'] == line_code or elem['LineCode3'] == line_code:
                filtered_station_data.append(elem)
    else:
        print('Error in retreiving station data:', response.status_code)
    #sort filtered station data alphabetically
    sort_lambda = lambda x: x['Name']
    filtered_station_data.sort(key = sort_lambda)
    return filtered_station_data

def get_station_code(station_name, filtered_station_data):
    station_code = 'A01'
    station_dictionary = {element['Name']: element['Code'] for element in filtered_station_data}
    if station_name in station_dictionary:
        station_code = station_dictionary[station_name]
    else:
        print("No station found: {station_name}, using default code 'A01', for Metro Center")
    return station_code

def get_arrivals_data(station_code):
    arrivals_endpoint = 'StationPrediction.svc/json/GetPrediction/' + station_code
    arrivals_url = BASE_URL + arrivals_endpoint
    response = requests.get(arrivals_url, headers = HEADERS)
    return response

def parse_trains(arrival_data):
    filtered_trains = []
    for train in arrival_data['Trains']:
        filtered_train = [train['Line'], train['Car'], train['Destination'], train['Min']]
        #filter out trains that aren't on a line, such as no passenger
        if not filtered_train[1] in LINE_CODES:
            filtered_trains.append(filtered_train)
    return filtered_trains

def print_arrival_data(station_name, filtered_trains):
    print(station_name)
    max_lengths = [max(map(len, col)) for col in zip(*filtered_trains)]
    for row in filtered_trains:
        formatted_row = ' '.join('{{:<{}}}'.format(length).format(elem) for length, elem in zip(max_lengths, row))
        print(formatted_row)

def get_and_print_arrival_data(station_name, station_code):
    arrivals_response = get_arrivals_data(station_code)
    if arrivals_response.status_code == HEALTHY_STATUS:
        arrival_data = arrivals_response.json()
        filtered_trains= parse_trains(arrival_data)
        #check for station that has more than one track
        if station_code in MULTI_TRACK_STATION_CODE_MAP.keys():
            #get the data for the second track too
            additional_response = get_arrivals_data(MULTI_TRACK_STATION_CODE_MAP[station_code])
            if additional_response.status_code == HEALTHY_STATUS:
                additional_data = additional_response.json()
                filtered_trains.extend(parse_trains(additional_data))
                #now we have to sort the filtered trains based on arrival time
                sort_lambda = lambda x: sort_by_arrival(x)
                filtered_trains.sort(key = sort_lambda)
            else: 
                print('Error in retreiving additional arrival data:', additional_response.status_code)
        print_arrival_data(station_name, filtered_trains)
    else:
        print('Error in retreiving arrival data:', arrivals_response.status_code)

def make_requests(line_index, station_index):
    filtered_station_data = get_station_data(line_index)
    station_name = filtered_station_data[station_index % len(filtered_station_data)]["Name"]
    station_code = get_station_code(station_name, filtered_station_data)
    get_and_print_arrival_data(station_name, station_code)

line_index = 0
station_index = 0
counter = 0
keyboard.on_press(on_keypress)
while True:
    try:
        make_requests(line_index, station_index)
    except Exception as e:
        print(f"An exception occurred: {type(e).__name__}: {e}")
    finally:
        while counter < COUNTER_MAX:
            time.sleep(WAIT_INTERVAL)
            counter += 1
        counter = 0
    pass

#two keyboard interrupts
#l: change lines: Red, Blue, Green, Orange, Yellow, Silver, Purple
#s: flick through stations in alphabetical order
#display will immediately update when new station is selected
