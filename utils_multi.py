from math import sqrt
from config_multi import *

from trafficElements_multi.vehicle import Vehicle
from trafficElements_multi.junction import FourWayJunction

import traci


def generateVehicles(numberOfSteps, numberOfVehicles, vehicles, routeMode, instantPay, seed):
    """Genero veicoli per ogni route possibile nel caso di incrocio multiplo"""

    c = 0
    t = 0
    depart = 0
    auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]

    for i in range(0, sum(numberOfVehicles)):
        if t < numberOfVehicles[c]:
            t += 1
        else:
            t = 0
            c += 1
            auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]
        depart += auto_every
        idV = f'idV{i}'
        vehicles[idV] = Vehicle(idV, seed, iP=instantPay)
        base_route = vehicles[idV].generateRoute(static=routeMode)
        route = traci.simulation.findRoute(base_route[0], base_route[1])
        traci.route.add(f'route_{i}', route.edges)
        vehicles[idV].setEdgeObjective(base_route[1])
        traci.vehicle.add(idV, f'route_{i}', depart=depart)

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


def createJunctions(vehicles):
    """Funzione che inizializza gli incroci della simulazione"""

    junctions = []

    for i in range(1, 26):
        junctions.append(FourWayJunction(i, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                                         groupDimension=dimensionOfGroups))

    return junctions


def getLaneIndexFromEdges(edges, vehicle, node_ids):
    """Funzione che trova la lane corretta da far seguire al veicolo dati il nodo di partenza e quello di
    destinazione correnti"""

    distance = -1
    i = 0
    trovato = False

    start = int(edges[vehicle.edgeIndex][1:3])
    end = int(edges[vehicle.edgeIndex + 1][4:6])

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

    return lane, start, end


def getDistanceFromLaneEnd(spawn_distance, lane_length, shape, ID):
    """Calcolo la distanza tra il veicolo e l'inizio dell'incrocio"""

    min_x = shape[0][0]
    max_x = shape[0][0]
    min_y = shape[0][1]
    max_y = shape[0][1]

    for point in shape:
        if point[0] < min_x:
            min_x = point[0]
        if point[0] > max_x:
            max_x = point[0]
        if point[1] < min_y:
            min_y = point[1]
        if point[1] > max_y:
            max_y = point[1]
    if max_x - min_x >= max_y - min_y:
        lane_end = lane_length - (max_x - min_x) / 2
    else:
        lane_end = lane_length - (max_y - min_y) / 2

    return lane_end - spawn_distance


def checkRoute(vehicles, numberOfVehicles):
    """Controllo se i veicoli hanno raggiunto l'obbiettivo e, nel caso, riassegno una nuova route"""

    for i in range(0, sum(numberOfVehicles)):
        vehicles[f'idV{i}'].travelTimes[vehicles[f'idV{i}'].index] += 1
        vehicles[f'idV{i}'].changeTarget(staticRoutes=routeMode)

    return vehicles


def checkVehicles(vehicles, departed_vehicles, junctions, time, schema):
    """Funzione che controlla il posizionamento dei veicoli e calcola le relative misure"""

    for junction in junctions:

        junction.departed.append(0)
        junction.arrived.append(0)

        vehs_in_junction = junction.getActualVehicles(departed_vehicles)
        for lane in junction.tails_per_lane:
            junction.tails_per_lane[lane].append(0)
        # loop per tutti i veicoli
        for veh in vehs_in_junction:
            veh_current_lane = traci.vehicle.getLaneID(veh)

            # controllo se il veicolo è in una lane entrante
            if veh_current_lane in junction.incomingLanes:
                vehicles[veh].startingLane = veh_current_lane
                if veh not in junction.vehiclesEntering:
                    junction.vehiclesEntering.append(veh)
                    junction.departed[time - 1] += 1
                    vehicles[veh].spawnDistances.append(0)
                    vehicles[veh].edgeIndex += 1
                spawn_distance = traci.vehicle.getDistance(veh) - sum(vehicles[veh].spawnDistances[:-1])
                vehicles[veh].spawnDistances[-1] = spawn_distance
                distance = getDistanceFromLaneEnd(spawn_distance, traci.lane.getLength(veh_current_lane),
                                                  junction.junction_shape, junction.nID)
                # if distance > 60:
                #     vehicles[veh].checkLane()
                if distance < 15:
                    vehicles[veh].speeds[vehicles[veh].index].append(traci.vehicle.getSpeed(veh))
                veh_length = traci.vehicle.getLength(veh)
                check = veh_length / 2 + 0.2
                leader = traci.vehicle.getLeader(veh)
                if traci.vehicle.getSpeed(veh) <= 1:
                    # verifico se il veicolo è in testa
                    if check >= distance and ((leader and leader[1] < 0) or not leader):
                        junction.tails_per_lane[veh_current_lane][time - 1] += 1
                        vehicles[veh].headTimes[vehicles[veh].index] += 1
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                    # verifico se il veicolo è in coda
                    elif leader and leader[1] <= 0.5 and vehicles[leader[0]].startingLane == veh_current_lane:
                        junction.tails_per_lane[veh_current_lane][time - 1] += 1
                        vehicles[veh].tailTimes[vehicles[veh].index] += 1
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                else:
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

            # controllo se il veicolo è all'interno della junction
            elif veh_current_lane in junction.crossingLanes:
                spawn_distance = traci.vehicle.getDistance(veh) - \
                                 sum(vehicles[veh].spawnDistances[:-1])
                vehicles[veh].spawnDistances[-1] = spawn_distance
                leader = traci.vehicle.getLeader(veh)
                leader_lane = ''
                if leader:
                    leader_lane = traci.vehicle.getLaneID(leader[0])
                vehicles[veh].speeds[vehicles[veh].index].append(traci.vehicle.getSpeed(veh))
                if traci.vehicle.getSpeed(veh) <= 1:
                    # verifico se il veicolo è in testa
                    if (leader and leader_lane != veh_current_lane) or not leader:
                        junction.tails_per_lane[vehicles[veh].startingLane][time - 1] += 1
                        vehicles[veh].headTimes[vehicles[veh].index] += 1
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                    # verifico se il veicolo è in coda
                    elif leader and leader[1] <= 0.5 and leader_lane == veh_current_lane:
                        junction.tails_per_lane[vehicles[veh].startingLane][time - 1] += 1
                        vehicles[veh].tailTimes[vehicles[veh].index] += 1
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                else:
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

            # controllo se il veicolo è in una lane uscente
            elif veh_current_lane in junction.outgoingLanes:
                if veh in junction.vehiclesEntering:
                    vehicles[veh].startingLane = ''
                    junction.vehiclesEntering.remove(veh)
                    junction.arrived[time - 1] += 1

    return vehicles, junctions


def saveResults(vehicles, departed, junctions):
    travelTimes = []  # lista dei tempi di percorrenza medi per ogni veicolo
    varTravelTime = 0  # varianza rispetto al tempo di percorrenza
    headTimes = []  # lista dei tempi passati in testa medi per ogni veicolo
    varHeadTime = 0  # varianza rispetto al tempo passato in testa
    tailTimes = []  # lista dei tempi in coda medi per ogni veicolo
    varTailTime = 0  # varianza rispetto al tempo passato in coda
    meanSpeeds = []  # lista delle velocità medie assunte dai veicoli nei pressi dell'incrocio
    varSpeed = 0  # varianza rispetto alla velocità dei veicoli
    meanTailLength = []  # lista delle lunghezze medie delle code rilevate sulle lane entranti
    varTail = 0  # varianza rispetto alla coda
    maxTail = -1  # coda massima rilevata su tutte le lane entranti

    for veh in vehicles:
        if int(veh[-1]) < departed:
            travelTimes.append(sum(vehicles[veh].travelTimes) / len(vehicles[veh].travelTimes))
            headTimes.append(sum(vehicles[veh].headTimes) / len(vehicles[veh].headTimes))
            tailTimes.append(sum(vehicles[veh].tailTimes) / len(vehicles[veh].tailTimes))
            sps = []
            for speeds in vehicles[veh].speeds:
                if len(speeds) > 0:
                    sps.append(sum(speeds) / len(speeds))
            if len(sps) > 0:
                meanSpeeds.append(sum(sps) / len(sps))

    meanTravelTime = sum(travelTimes) / len(travelTimes)
    for travelTime in travelTimes:
        varTravelTime += (travelTime - meanTravelTime) ** 2
    stDevTravelTime = sqrt(varTravelTime / len(travelTimes))
    maxTravelTime = max(travelTimes)

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

    meanTails = []
    stDevTails = []
    maxTails = []
    meanThroughput = []

    for junction in junctions:
        meanTp = []
        for i in range(0, len(junction.arrived)):
            if junction.departed[i] == 0:
                meanTp.append(1)
            else:
                meanTp.append(junction.arrived[i] / junction.departed[i])
        meanThroughput.append(sum(meanTp) / len(meanTp))
        for lane in junction.tails_per_lane:
            meanTailLength.append(sum(junction.tails_per_lane[lane]) / len(junction.tails_per_lane[lane]))
            lane_max = max(junction.tails_per_lane[lane])
            if lane_max > maxTail:
                maxTail = lane_max
        meanTail = sum(meanTailLength) / len(meanTailLength)
        for tail in meanTailLength:
            varTail += (tail - meanTail) ** 2
        meanTails.append(meanTail)
        stDevTails.append(sqrt(varTail / len(meanTailLength)))
        maxTails.append(maxTail)
        maxTail = -1

    meanTail = round(sum(meanTails) / len(meanTails), 2)
    stDevTail = round(sum(stDevTails) / len(stDevTails), 2)
    maxTail = max(maxTails)
    meanTp = round(sum(meanThroughput) / len(meanThroughput), 2)

    return meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, \
           stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, meanTails, \
           stDevTails, maxTails, meanThroughput
