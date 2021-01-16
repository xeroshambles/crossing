import sys
import os
import random

config_file = "intersection.sumocfg"
junction_id = 7
lanes_per_road = 2
lanes = []
node_ids = [2, 6, 8, 12]
tailLengths = {}  # dizionario con chiavi gli id delle lane e con valori le liste delle code

for i in node_ids:
    zero_lane = ''
    if i < 12:
        zero_lane = '0'
    for lane in range(0, lanes_per_road):
        enter = f'e{zero_lane}{i}_0{junction_id}_{lane}'
        exit = f'e0{junction_id}_{zero_lane}{i}_{lane}'
        lanes.append(enter)
        lanes.append(exit)
        tailLengths[enter] = []


if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Dichiara la variabile d'ambiente 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa


def run(numberOfVehicles=50):
    """Funzione che avvia la simulazione dato un certo numero di veicoli e di time step"""
    vehicles = {}  # dizionario contente gli id dei veicoli
    totalTime = 0  # tempo totale di simulazione
    vehiclesSpeeds = {}  # dizionario con chiavi gli id dei veicoli e con valori le velocità assunte in ogni step

    """Con il seguente ciclo inizializzo i veicoli assegnadogli una route generata casualmente e dandogli un colore
    diverso per distinguerli meglio all'interno della simulazione"""
    for n in range(1, numberOfVehicles + 1):
        idV = str(n)
        # oggetto veicolo:
        # headStopTime: considera il tempo passato in testa (con un piccolo delay dovuto alla ripartenza del veicolo)
        # followerStopTime: considera il tempo passato in coda
        # speeds: lista con i valori delle velocità assunte in ogni step
        # stopped: variabile che indica che il veicolo si è fermato almeno una volta
        vehicle = {'id': idV, 'headStopTime': 0, 'followerStopTime': 0, 'speeds': [], 'stopped': 0}
        vehicles[idV] = vehicle
        vehiclesSpeeds[idV] = []
        node_ids = [2, 6, 8, 12]
        start = random.choice(node_ids)
        node_ids.remove(start)
        end = random.choice(node_ids)
        zero_start = ''
        zero_end = ''
        if start != 12:
            zero_start = '0'
        if end != 12:
            zero_end = '0'
        traci.route.add(f'route_{n}', [f'e{zero_start}{start}_0{junction_id}', f'e0{junction_id}_{zero_end}{end}'])
        traci.vehicle.add(idV, f'route_{n}')
        if n % 8 == 1:
            traci.vehicle.setColor(f'{n}', (0, 255, 255))  # azzurro
        if n % 8 == 2:
            traci.vehicle.setColor(f'{n}', (160, 100, 100))  # rosa
        if n % 8 == 3:
            traci.vehicle.setColor(f'{n}', (255, 0, 0))  # rosso
        if n % 8 == 4:
            traci.vehicle.setColor(f'{n}', (0, 255, 0))  # verde
        if n % 8 == 5:
            traci.vehicle.setColor(f'{n}', (0, 0, 255))  # blu
        if n % 8 == 6:
            traci.vehicle.setColor(f'{n}', (255, 255, 255))  # bianco
        if n % 8 == 7:
            traci.vehicle.setColor(f'{n}', (255, 0, 255))  # viola
        if n % 8 == 8:
            traci.vehicle.setColor(f'{n}', (255, 100, 0))  # arancione

    """Di seguito il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa."""
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        totalTime += 1
        for lane in lanes:
            # considero solo le lane entranti
            if lane[4:6] == '07':
                tail_dim = 0
                vehs_in_lane = traci.lane.getLastStepVehicleIDs(lane)
                for veh in vehs_in_lane:
                    vehicles[veh]['speeds'].append(traci.vehicle.getSpeed(veh))
                    distance = traci.vehicle.getNextTLS(veh)[0][2]
                    veh_length = traci.vehicle.getLength(veh)
                    check = veh_length / 2 + 0.2
                    leader = traci.vehicle.getLeader(veh)
                    spawn_distance = traci.vehicle.getDistance(veh)
                    if traci.vehicle.getSpeed(veh) <= 1:
                        tail_dim += 1
                        # verifico se il veicolo si è fermato
                        if spawn_distance > 0:
                            vehicles[veh]['stopped'] = 1
                        # verifico se il veicolo è in testa
                        if check >= distance and ((leader and leader[1] > 1) or not leader):
                            # print(f"{veh} è in testa alla lane {lane}")
                            vehicles[veh]['headStopTime'] += 1
                            continue
                        # verifico se il veicolo è in coda
                        if leader and leader[1] <= 1:
                            if leader[0] not in vehs_in_lane:
                                # print(f"{leader[0]} è in testa alla lane {lane}")
                                vehicles[leader[0]]['headStopTime'] += 1
                            # print(f"{veh} è in coda alla lane {lane}")
                            vehicles[veh]['followerStopTime'] += 1
                            continue
                tailLengths[lane].append(tail_dim)
    """Salvo tutti i risultati e li ritorno."""
    headTimes = []
    tailTimes = []
    meanSpeeds = []
    maxSpeed = -1
    nStoppedVehicles = []
    meanTailLength = []
    maxTail = -1
    for veh in vehicles:
        # print(vehicles[veh])
        headTimes.append(vehicles[veh]['headStopTime'])
        tailTimes.append(vehicles[veh]['followerStopTime'])
        meanSpeeds.append(sum(vehicles[veh]['speeds']) / len(vehicles[veh]['speeds']))
        speed_max = max(vehicles[veh]['speeds'])
        if speed_max > maxSpeed:
            maxSpeed = speed_max
        nStoppedVehicles.append(vehicles[veh]['stopped'])
    for lane in tailLengths:
        meanTailLength.append(sum(tailLengths[lane]) / len(tailLengths[lane]))
        lane_max = max(tailLengths[lane])
        if lane_max > maxTail:
            maxTail = lane_max
    return totalTime, sum(headTimes) / len(headTimes), max(headTimes), sum(tailTimes) / len(tailTimes), \
           max(tailTimes), sum(meanSpeeds) / len(meanSpeeds), maxSpeed, sum(meanTailLength) / len(meanTailLength), \
           maxTail, sum(nStoppedVehicles)


def printFile(s, f):
    print(s, file=f)


if __name__ == "__main__":
    choice = ''
    while choice not in ['d', 'D', 'g', 'G']:
        choice = input('\nVuoi raccogliere dati o avere una visualizzazione grafica? (d=dati, g=grafica): ')
        if choice not in ['d', 'D', 'g', 'G']:
            print('\nInserire un carattere tra d e g!')
    if choice in ['d', 'D']:
        sumoBinary = checkBinary('sumo')
        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"]
    else:
        sumoBinary = checkBinary('sumo-gui')
        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"]
    numberOfSimulations = 0
    while numberOfSimulations <= 0:
        numberOfSimulations = int(input('\nInserire il numero di simulazioni: '))
        if numberOfSimulations <= 0:
            print('\nInserire un numero di simulazioni positivo!')
    with open("output.txt", "w") as f:
        for i in range(1, numberOfSimulations + 1):
            numberOfVehicles = 0
            while numberOfVehicles <= 0:
                numberOfVehicles = int(input(f'\nInserire il numero di veicoli nella simulazione {i}: '))
                if numberOfVehicles <= 0:
                    print('\nInserire un numero di veicoli positivo!')
            traci.start(sumoCmd)
            time, avgHeadTime, maxHeadTime, avgTailTime, maxTailTime, avgSpeed, maxSpeed, avgTailLength, \
            maxTailLength, nStoppedVehicles = run(numberOfVehicles)
            printFile('----------------------------------------------------\n', f)
            printFile(f'SIMULAZIONE NUMERO {i}\n', f)
            printFile('----------------------------------------------------\n', f)
            printFile(f'NUMERO DI VEICOLI: {numberOfVehicles}\n', f)
            printFile(f'TEMPO TOTALE DI SIMULAZIONE: {time} step\n', f)
            printFile(f'TEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(avgHeadTime, 2)} step\n', f)
            printFile(f'TEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {maxHeadTime} step\n', f)
            printFile(f'TEMPO MEDIO PASSATO IN CODA: {round(avgTailTime, 2)} step\n', f)
            printFile(f'TEMPO MASSIMO PASSATO IN CODA: {maxTailTime} step\n', f)
            printFile(f'VELOCITA MEDIA DEI VEICOLI: {round(avgSpeed, 2)} m/s\n', f)
            printFile(f'VELOCITA MASSIMA DEI VEICOLI: {round(maxSpeed, 2)} m/s\n', f)
            printFile(f'LUNGHEZZA MEDIA DELLE CODE: {round(avgTailLength, 2)} auto\n', f)
            printFile(f'LUNGHEZZA MASSIMA DELLE CODE: {round(maxTailLength, 2)} auto\n', f)
            printFile(f'NUMERO DI VEICOLI FERMI: {nStoppedVehicles} ({round(nStoppedVehicles / numberOfVehicles * 100, 2)}%)\n', f)
            traci.close()
