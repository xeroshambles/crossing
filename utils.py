import random
from math import sqrt
from config import *

from precedence_with_auction.trafficElements.vehicle import Vehicle

import traci


def checkIfMainStep(total_time, n_steps, n_vehs, step, vehicles, departed, mean_th_per_num):

    check, temp = saveIntermediateResults(total_time, n_steps, n_vehs, step, vehicles, departed)
    if check:
        mean_th_per_num[step] = temp
        step += 1
        departed = 0

    return mean_th_per_num, step, departed


def saveIntermediateResults(total_time, n_steps, n_vehs, step, vehicles, departed):

    mean_th = -1
    mod = total_time % (n_steps / len(n_vehs))
    if mod == 0 and total_time <= n_steps:
        passed = 0
        floor = sum(n_vehs[0: step])
        ceil = floor + n_vehs[step]
        ids = [k for k in vehicles]
        ids_c = ids[floor: ceil]
        dummy = {k: vehicles[k] for k in vehicles if k in ids_c}
        for veh in dummy:
            if int(veh[-1]) < departed:
                passed += vehicles[veh].hasPassed
        mean_th = passed / departed

    if mean_th == -1:
        return False, mean_th
    else:
        return True, mean_th


def getLaneIndexFromEdges(start, end, node_ids):
    """Funzione che trova la lane corretta da far seguire al veicolo dati il nodo di partenza e quello di
    destinazione"""

    distance = -1
    i = 0
    trovato = False

    while True:
        if node_ids[i % 4] == start:
            trovato = True
        if trovato:
            distance += 1
            if node_ids[i % 4] == end:
                break
        i += 1

    lane = 0

    if distance == 1:
        lane = 2
    if distance == 2:
        lane = 1
    if distance == 3:
        lane = 0

    return lane


def getDistanceFromLaneEnd(spawn_distance, lane_length, shape):
    """Calcolo la distanza tra il veicolo e l'inizio dell'incrocio"""

    min_x = shape[0][0]
    max_x = shape[0][0]

    for point in shape:
        if point[0] < min_x:
            min_x = point[0]
        if point[0] > max_x:
            max_x = point[0]

    lane_end = lane_length - (max_x - min_x) / 2

    return lane_end - spawn_distance


def generateRoutes(junction_id, node_ids):
    """Genero tutte le route possibili per l'incrocio"""

    n = 0

    for i in node_ids:
        for j in node_ids:
            if i == j:
                continue
            start = i
            end = j
            traci.route.add(f'route_{n}', [f'e{"0" if start != 12 else ""}{start}_0{junction_id}',
                                           f'e0{junction_id}_{"0" if end != 12 else ""}{end}'])
            n += 1

    routes = traci.route.getIDList()
    routes_per_lane_start = {'0': [], '1': [], '2': []}

    for route in routes:
        edges = traci.route.getEdges(route)
        index = getLaneIndexFromEdges(int(edges[0][1:3]), int(edges[1][4:6]), node_ids)
        routes_per_lane_start[str(index)].append(route)

    return routes_per_lane_start


def generateLaneSequence(px, py, numberOfVehicles, seed):
    """Genero la sequenza di lane equiprobabili"""

    random.seed(seed)
    sequence = []

    for _ in range(0, numberOfVehicles):
        r = random.randint(1, 100)
        if r <= px:
            sequence.append(0)
        elif r <= (px + py):
            sequence.append(1)
        else:
            sequence.append(2)

    return sequence


def generateVehicles(numberOfSteps, numberOfVehicles, vehicles, seed, junction_id, node_ids, wallet=False):
    """Genero veicoli per ogni route possibile"""

    c = 0
    t = 0

    depart = 0
    auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]

    random.seed(seed)

    routes = generateRoutes(junction_id, node_ids)
    sequence = generateLaneSequence(33, 33, sum(numberOfVehicles), seed)

    for i in range(0, sum(numberOfVehicles)):
        if t < numberOfVehicles[c]:
            t += 1
        else:
            t = 0
            c += 1
            auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]
        depart += auto_every
        idV = f'idV{i}'
        vehicles[idV] = Vehicle(idV, iP=instantPay)
        route = random.choice(routes[str(sequence[i])])
        edges = traci.route.getEdges(route)
        lane = getLaneIndexFromEdges(int(edges[0][1:3]), int(edges[1][4:6]), node_ids)
        traci.vehicle.add(idV, route, depart=depart, departLane=lane)
        if wallet:
            traci.vehicle.setParameter(idV, "wallet", str(50))

    return vehicles


def colorVehicles(numberOfVehicles):
    """Assegno un colore diverso alle auto"""

    for i in range(0, numberOfVehicles):
        if i % 8 == 1:
            traci.vehicle.setColor(f'{i}', (0, 255, 255))  # azzurro
        if i % 8 == 2:
            traci.vehicle.setColor(f'{i}', (160, 100, 100))  # rosa
        if i % 8 == 3:
            traci.vehicle.setColor(f'{i}', (255, 0, 0))  # rosso
        if i % 8 == 4:
            traci.vehicle.setColor(f'{i}', (0, 255, 0))  # verde
        if i % 8 == 5:
            traci.vehicle.setColor(f'{i}', (0, 0, 255))  # blu
        if i % 8 == 6:
            traci.vehicle.setColor(f'{i}', (255, 255, 255))  # bianco
        if i % 8 == 7:
            traci.vehicle.setColor(f'{i}', (255, 0, 255))  # viola
        if i % 8 == 8:
            traci.vehicle.setColor(f'{i}', (255, 100, 0))  # arancione


def checkVehicles(vehicles, tails_per_lane, time, schema):
    """Funzione che controlla il posizionamento dei veicoli nell'incrocio e prende le misure"""

    vehs_loaded = traci.vehicle.getIDList()
    junction_shape = traci.junction.getShape("n" + str(junction_id))

    for lane in tails_per_lane:
        tails_per_lane[lane].append(0)

    # loop per tutti i veicoli
    for veh in vehs_loaded:
        veh_current_lane = traci.vehicle.getLaneID(veh)

        # controllo se il veicolo è in una lane entrante
        if veh_current_lane[4:6] == '07':
            vehicles[veh].startingLane = veh_current_lane
            spawn_distance = traci.vehicle.getDistance(veh)
            distance = getDistanceFromLaneEnd(spawn_distance, traci.lane.getLength(veh_current_lane),
                                              junction_shape)
            if distance < 15:
                vehicles[veh].speeds.append(traci.vehicle.getSpeed(veh))
            veh_length = traci.vehicle.getLength(veh)
            check = veh_length / 2 + 0.2
            leader = traci.vehicle.getLeader(veh)
            if traci.vehicle.getSpeed(veh) <= 1:
                # verifico se il veicolo è in testa
                if check >= distance and ((leader and leader[1] < 0) or not leader):
                    vehicles[veh].hasStopped = 1
                    tails_per_lane[veh_current_lane][time - 1] += 1
                    vehicles[veh].headTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                    continue
                # verifico se il veicolo è in coda
                if leader and leader[1] <= 0.5 and vehicles[leader[0]].startingLane == veh_current_lane:
                    vehicles[veh].hasStopped = 1
                    tails_per_lane[veh_current_lane][time - 1] += 1
                    vehicles[veh].tailTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                    continue
            else:
                if schema in ['s', 'S']:
                    traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

        # controllo se il veicolo è all'interno della junction
        if veh_current_lane[1:3] == 'n7':
            vehicles[veh].speeds.append(traci.vehicle.getSpeed(veh))
            leader = traci.vehicle.getLeader(veh)
            leader_lane = ''
            if leader:
                leader_lane = traci.vehicle.getLaneID(leader[0])
            if traci.vehicle.getSpeed(veh) <= 1:
                tails_per_lane[vehicles[veh].startingLane][time - 1] += 1
                # verifico se il veicolo è in testa
                if (leader and leader_lane != veh_current_lane) or not leader:
                    vehicles[veh].headTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                    continue
                # verifico se il veicolo è in coda
                if leader and leader[1] <= 0.5 and leader_lane == veh_current_lane:
                    vehicles[veh].tailTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                    continue
            else:
                if schema in ['s', 'S']:
                    traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

        # controllo se il veicolo è in una lane uscente
        if veh_current_lane[1:3] == '07':
            if vehicles[veh].hasPassed == 0:
                vehicles[veh].hasPassed = 1
            if schema in ['s', 'S']:
                traci.vehicle.setColor(veh, (0, 255, 0))  # verde

    return vehicles, tails_per_lane


def saveResults(vehicles, departed, tails_per_lane):
    """Funzione che calcola le misure adottate"""

    headTimes = []  # lista dei tempi passati in testa per ogni veicolo
    varHeadTime = 0  # varianza rispetto al tempo passato in testa
    tailTimes = []  # lista dei tempi passati in coda per ogni veicolo
    varTailTime = 0  # varianza rispetto al tempo passato in coda
    meanSpeeds = []  # medie delle velocità assunte dai veicoli nei pressi dell'incrocio
    varSpeed = 0  # varianza rispetto alla velocità dei veicoli
    stopped = []  # lista che dice se i veicoli si sono fermati all'incrocio o no
    meanTailLength = []  # medie delle lunghezze delle code rilevate sulle lane entranti ad ogni step
    varTail = 0  # varianza rispetto alla coda
    maxTail = -1  # coda massima rilevata su tutte le lane entranti
    passed = 0  # numero di veicoli arrivati a destinazione

    for veh in vehicles:
        if int(veh[-1]) < departed:
            headTimes.append(vehicles[veh].headTime)
            tailTimes.append(vehicles[veh].tailTime)
            if len(vehicles[veh].speeds) > 0:
                meanSpeeds.append(sum(vehicles[veh].speeds) / len(vehicles[veh].speeds))
            stopped.append(vehicles[veh].hasStopped)
            passed += vehicles[veh].hasPassed

    meanHeadTime = sum(headTimes) / len(headTimes)
    for headTime in headTimes:
        varHeadTime += (headTime - meanHeadTime) ** 2
    stDevHeadTime = sqrt(varHeadTime / len(headTimes))
    maxHeadTime = max(headTimes)

    meanTailTime = sum(tailTimes) / len(tailTimes)
    for tailTime in tailTimes:
        varTailTime += (tailTime - meanTailTime) ** 2
    stDevTailTime = sqrt(varTailTime / len(tailTimes))
    maxTailTime = max(tailTimes)

    if len(meanSpeeds) > 0:
        meanSpeed = sum(meanSpeeds) / len(meanSpeeds)
        for speed in meanSpeeds:
            varSpeed += (speed - meanSpeed) ** 2
        stDevSpeed = sqrt(varSpeed / len(meanSpeeds))
    else:
        meanSpeed = 0
        stDevSpeed = 0

    for lane in tails_per_lane:
        meanTailLength.append(sum(tails_per_lane[lane]) / len(tails_per_lane[lane]))
        lane_max = max(tails_per_lane[lane])
        if lane_max > maxTail:
            maxTail = lane_max

    meanTail = sum(meanTailLength) / len(meanTailLength)
    for tail in meanTailLength:
        varTail += (tail - meanTail) ** 2
    stDevTail = sqrt(varTail / len(meanTailLength))

    stoppedVehicles = sum(stopped)

    throughput = passed / departed

    return meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime, \
           meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput