import sys
import os
import random
from math import sqrt

config_file = "intersection.sumocfg"
junction_id = 7
lanes_per_road = 3
lanes = []
node_ids = [2, 6, 8, 12]

for i in node_ids:
    zero_lane = ''
    if i < 12:
        zero_lane = '0'
    for lane in range(0, lanes_per_road):
        enter = f'e{zero_lane}{i}_0{junction_id}_{lane}'
        exit = f'e0{junction_id}_{zero_lane}{i}_{lane}'
        lanes.append(enter)
        lanes.append(exit)


# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa


def run(numberOfVehicles, schema='n'):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    vehicles = {}  # dizionario contente gli id dei veicoli
    totalTime = 0  # tempo totale di simulazione
    throughput = []  # lista dei throughput misurati per ogni step
    headTimes = []  # lista dei tempi passati in testa per ogni veicolo
    var_meanHeadTime = 0  # varianza rispetto al tempo passato in testa
    tailTimes = []  # lista dei tempi in coda per ogni veicolo
    var_meanTailTime = 0  # varianza rispetto al tempo passato in coda
    meanSpeeds = []  # medie delle velocità assunte dai veicoli ad ogni step
    var_meanSpeed = 0  # varianza rispetto alla velocità media
    maxSpeed = -1  # velocità massima rilevata su tutti i veicoli
    nStoppedVehicles = []  # lista che dice se i veicoli si sono fermati all'incrocio o no
    meanTailLength = []  # medie delle lunghezze delle code rilevate sulle lane entranti ad ogni step
    var_meanTailLength = 0  # varianza rispetto alla lunghezza media delle code
    tails = {}  # dizionario contenente le code per ogni lane
    tailLengths = {}  # dizionario con chiavi gli id delle lane e con valori le liste delle code
    for lane in lanes:
        if lane[4:6] == '07':
            tails[lane] = 0
            tailLengths[lane] = []
    maxTail = -1  # coda massima rilevata su tutte le lane entranti

    """Con il seguente ciclo inizializzo i veicoli assegnadogli una route generata casualmente e dandogli un colore
    diverso per distinguerli meglio all'interno della simulazione"""
    for n in range(1, numberOfVehicles + 1):
        idV = str(n)
        # oggetto veicolo:
        # headStopTime: considera il tempo passato in testa (con un piccolo delay dovuto alla ripartenza del veicolo)
        # followerStopTime: considera il tempo passato in coda
        # speeds: lista con i valori delle velocità assunte in ogni step
        # stopped: variabile che indica che il veicolo si è fermato all'incrocio
        vehicle = {'id': idV, 'headStopTime': 0, 'followerStopTime': 0, 'speeds': [], 'hasStopped': 0, 'isCrossing': 0,
                   'hasCrossed': 0, 'startingLane': ''}
        vehicles[idV] = vehicle
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
        if schema in ['n', 'N']:
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
        vehs_loaded = traci.vehicle.getIDList()
        n_vehicles_entering = 0
        n_vehicles_exiting = 0
        for tail in tails:
            tails[tail] = 0
        # loop per tutti i veicoli
        for veh in vehs_loaded:
            veh_current_lane = traci.vehicle.getLaneID(veh)
            # controllo se il veicolo è nella junction
            if veh_current_lane[1:3] == 'n7':
                vehicles[veh]['isCrossing'] = 1
                leader = traci.vehicle.getLeader(veh)
                leader_lane = ''
                if leader:
                    leader_lane = traci.vehicle.getLaneID(leader[0])
                if traci.vehicle.getSpeed(veh) <= 1:
                    # verifico se il veicolo è in testa
                    if (leader and leader_lane != veh_current_lane) or not leader:
                        vehicles[veh]['headStopTime'] += 1
                        tails[vehicles[veh]['startingLane']] += 1
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                        continue
                    # verifico se il veicolo è in coda
                    if leader and leader[1] <= 0.5 and leader and leader_lane == veh_current_lane:
                        vehicles[veh]['followerStopTime'] += 1
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                        continue
                else:
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (255, 255, 0))  # giallo
            # controllo se il veicolo è nella lane uscente
            if veh_current_lane[1:3] == '07':
                vehicles[veh]['isCrossing'] = 0
                vehicles[veh]['hasCrossed'] = 1
                if schema in ['s', 'S']:
                    traci.vehicle.setColor(veh, (0, 255, 0))  # verde
            # controllo se il veicolo è in una lane entrante
            if veh_current_lane[4:6] == '07':
                vehicles[veh]['startingLane'] = veh_current_lane
                vehicles[veh]['speeds'].append(traci.vehicle.getSpeed(veh))
                distance = traci.vehicle.getNextTLS(veh)[0][2]
                veh_length = traci.vehicle.getLength(veh)
                check = veh_length / 2 + 0.2
                leader = traci.vehicle.getLeader(veh)
                spawn_distance = traci.vehicle.getDistance(veh)
                if traci.vehicle.getSpeed(veh) <= 1:
                    # verifico se il veicolo si è fermato al di fuori del punto di spawn
                    if spawn_distance > 0:
                        vehicles[veh]['hasStopped'] = 1
                        tails[veh_current_lane] += 1
                    # verifico se il veicolo è in testa
                    if check >= distance and ((leader and leader[1] > 0.5) or not leader):
                        vehicles[veh]['headStopTime'] += 1
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                        continue
                    # verifico se il veicolo è in coda
                    if leader and leader[1] <= 0.5:
                        vehicles[veh]['followerStopTime'] += 1
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                        continue
            for tail in tails:
                tailLengths[tail].append(tails[tail])

    """Salvo tutti i risultati e li ritorno."""
    for veh in vehicles:
        headTimes.append(vehicles[veh]['headStopTime'])
        tailTimes.append(vehicles[veh]['followerStopTime'])
        meanSpeeds.append(sum(vehicles[veh]['speeds']) / len(vehicles[veh]['speeds']))
        speed_max = max(vehicles[veh]['speeds'])
        if speed_max > maxSpeed:
            maxSpeed = speed_max
        nStoppedVehicles.append(vehicles[veh]['hasStopped'])

    meanHeadTime = sum(headTimes) / len(headTimes)
    for headTime in headTimes:
        var_meanHeadTime += (headTime - meanHeadTime) ** 2
    var_meanHeadTime /= len(headTimes)

    meanTailTime = sum(tailTimes) / len(tailTimes)
    for tailTime in tailTimes:
        var_meanTailTime += (tailTime - meanTailTime) ** 2
    var_meanTailTime /= len(tailTimes)

    for lane in tailLengths:
        meanTailLength.append(sum(tailLengths[lane]) / len(tailLengths[lane]))
        lane_max = max(tailLengths[lane])
        if lane_max > maxTail:
            maxTail = lane_max

    return totalTime, meanHeadTime, var_meanHeadTime, max(headTimes), meanTailTime, var_meanTailTime, \
           max(tailTimes), sum(meanSpeeds) / len(meanSpeeds), maxSpeed, sum(meanTailLength) / len(meanTailLength), \
           maxTail, sum(nStoppedVehicles)


def printFile(s, f):
    print(s, file=f)


if __name__ == "__main__":
    choice = ''
    schema = 'n'
    while choice not in ['d', 'D', 'g', 'G']:
        choice = input('\nVuoi raccogliere dati o avere una visualizzazione grafica? (d = dati, g = grafica): ')
        if choice not in ['d', 'D', 'g', 'G']:
            print('\nInserire un carattere tra d e g!')
    if choice in ['d', 'D']:
        sumoBinary = checkBinary('sumo')
        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"]
    else:
        sumoBinary = checkBinary('sumo-gui')
        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"]
        choice = ''
        while choice not in ['s', 'S', 'n', 'N']:
            choice = input('\nDesideri visualizzare le auto con uno schema di colori significativo? (s, n): ')
            if choice not in ['s', 'S', 'n', 'N']:
                print('\nInserire un carattere tra s e n!')
        schema = choice
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
            time, avgHeadTime, varHeadTime, maxHeadTime, avgTailTime, varTailTime, maxTailTime, avgSpeed, maxSpeed, avgTailLength, \
            maxTailLength, nStoppedVehicles = run(numberOfVehicles, schema)
            printFile('----------------------------------------------------\n', f)
            printFile(f'SIMULAZIONE NUMERO {i}\n', f)
            printFile('----------------------------------------------------\n', f)
            printFile(f'NUMERO DI VEICOLI: {numberOfVehicles}\n', f)
            printFile(f'TEMPO TOTALE DI SIMULAZIONE: {time} step\n', f)
            printFile(f'TEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(avgHeadTime, 2)} step\n', f)
            printFile(f'VARIANZA DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(varHeadTime, 2)} step\n', f)
            printFile(f'DEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(sqrt(varHeadTime), 2)} step\n', f)
            printFile(f'TEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {maxHeadTime} step\n', f)
            printFile(f'TEMPO MEDIO PASSATO IN CODA: {round(avgTailTime, 2)} step\n', f)
            printFile(f'VARIANZA DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(varTailTime, 2)} step\n', f)
            printFile(f'DEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(sqrt(varTailTime), 2)} step\n', f)
            printFile(f'TEMPO MASSIMO PASSATO IN CODA: {maxTailTime} step\n', f)
            printFile(f'VELOCITA MEDIA DEI VEICOLI: {round(avgSpeed, 2)} m/s\n', f)
            printFile(f'VELOCITA MASSIMA DEI VEICOLI: {round(maxSpeed, 2)} m/s\n', f)
            printFile(f'LUNGHEZZA MEDIA DELLE CODE: {round(avgTailLength, 2)} auto\n', f)
            printFile(f'LUNGHEZZA MASSIMA DELLE CODE: {round(maxTailLength, 2)} auto\n', f)
            printFile(f'NUMERO DI VEICOLI FERMI: {nStoppedVehicles} ({round(nStoppedVehicles / numberOfVehicles * 100, 2)}%)\n', f)
            traci.close()
