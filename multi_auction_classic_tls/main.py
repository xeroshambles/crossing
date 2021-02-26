import os
import sys
from math import sqrt
from config_multi import *
from utils import *
from multi_auction_classic_tls.trafficElements.junction import ThreeWayJunction, FourWayJunction
from multi_auction_classic_tls.trafficElements.vehicle import Vehicle

import traci
from sumolib import miscutils


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
        traci.vehicle.setMaxSpeed(idV, 9.72)


def run(numberOfSteps, numberOfVehicles, schema, sumoCmd, path, index, queue, seed):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    dir = os.path.join(path, 'terminals')

    if not os.path.exists(dir):
        try:
            os.mkdir(dir)
        except OSError:
            print(f"\nCreazione della cartella {dir} fallita...")
            sys.exit(-1)

    if output_redirection:

        origin_stdout = sys.stdout

        origin_stderr = sys.stderr

        sys.stdout = open(os.path.join(dir, f"{index}.txt"), "w")

        sys.stderr = open(os.path.join(dir, f"{index}.txt"), "w")

    traci.start(sumoCmd, port=port, numRetries=1000)

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    departed = 0
    departed_vehicles = []
    totalTime = 0  # tempo totale di simulazione
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

    """Con il seguente ciclo inizializzo i veicoli assegnadogli una route legale generata casualmente e, in caso di 
    schema di colori non significativo,dandogli un colore diverso per distinguerli meglio all'interno della 
    simulazione"""

    generateVehicles(stepsSpawn, numberOfVehicles, vehicles, routeMode, instantPay, seed)

    if schema in ['n', 'N']:
        colorVehicles(numberOfVehicles)

    """Di seguito inizializzo l'incrocio che fa parte della simulazione, assegnandogli una classe che ne descriva
    il comportamento specifico"""

    junctions = []  # dovrà contenere tutti gli incroci
    for i in range(1, 26):
        if i in two_way_junctions_ids:
            # junctions.append(TwoWayJunction(i))
            pass
        elif i in three_way_junctions_ids:
            junctions.append(ThreeWayJunction(i, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                                              groupDimension=dimensionOfGroups))
        else:
            junctions.append(FourWayJunction(i, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                                             groupDimension=dimensionOfGroups))

    """Di seguito il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        traci.simulationStep()
        totalTime += 1
        departed += traci.simulation.getDepartedNumber()
        departed_vehicles += traci.simulation.getDepartedIDList()

        # controllo se i veicoli hanno raggiunto l'obbiettivo e, nel caso, riassegno una nuova route
        for i in range(0, sum(numberOfVehicles)):
            vehicles[f'idV{i}'].travelTimes[vehicles[f'idV{i}'].index] += 1
            vehicles[f'idV{i}'].changeTarget(staticRoutes=routeMode)

        for junction in junctions:

            junction.departed.append(0)
            junction.arrived.append(0)

            # se l'incrocio è a quattro vie gestisco le aste

            if junction.nID in four_way_junctions_ids:

                # prime operazioni sull'incrocio

                vehAtJunction = junction.getVehiclesAtJunction()
                crossingManager = junction.getCrossingManager()
                crossingManager.updateCrossingStatus(vehicles)

                # flusso principale

                for idVeh in vehAtJunction:
                    if idVeh in vehicles:
                        objVeh = vehicles[idVeh]

                        if objVeh.distanceFromEndLane() < 50:
                            if objVeh not in crossingManager.getCurrentPartecipants():
                                crossingManager.updateVehicleStatus(objVeh)
                            # se non è gia in una auction, non e stoppato
                            if objVeh.distanceFromEndLane() < 15:
                                if objVeh in crossingManager.getCrossingStatus().values() and objVeh not in \
                                        crossingManager.getVehiclesInAuction() and objVeh.checkPosition(junction) \
                                        and objVeh not in crossingManager.nonStoppedVehicles:
                                    junction.createAuction(objVeh, vehicles)

                if len(vehAtJunction) > 0:
                    crossingManager.allowCrossing()

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
                        junction.departed[totalTime - 1] += 1
                    spawn_distance = traci.vehicle.getDistance(veh)
                    distance = getDistanceFromLaneEnd(spawn_distance, traci.lane.getLength(veh_current_lane),
                                                      junction.junction_shape)
                    if distance < 15:
                        vehicles[veh].speeds[vehicles[veh].index].append(traci.vehicle.getSpeed(veh))
                    veh_length = traci.vehicle.getLength(veh)
                    check = veh_length / 2 + 0.2
                    leader = traci.vehicle.getLeader(veh)
                    if traci.vehicle.getSpeed(veh) <= 1:
                        # verifico se il veicolo è in testa
                        if check >= distance and ((leader and leader[1] < 0) or not leader):
                            junction.tails_per_lane[veh_current_lane][totalTime - 1] += 1
                            vehicles[veh].headTimes[vehicles[veh].index] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                            continue
                        # verifico se il veicolo è in coda
                        if leader and leader[1] <= 0.5 and vehicles[leader[0]].startingLane == veh_current_lane:
                            junction.tails_per_lane[veh_current_lane][totalTime - 1] += 1
                            vehicles[veh].tailTimes[vehicles[veh].index] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                            continue
                    else:
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

                # controllo se il veicolo è all'interno della junction
                if veh_current_lane in junction.crossingLanes:
                    leader = traci.vehicle.getLeader(veh)
                    leader_lane = ''
                    if leader:
                        leader_lane = traci.vehicle.getLaneID(leader[0])
                    vehicles[veh].speeds[vehicles[veh].index].append(traci.vehicle.getSpeed(veh))
                    if traci.vehicle.getSpeed(veh) <= 1:
                        # verifico se il veicolo è in testa
                        if (leader and leader_lane != veh_current_lane) or not leader:
                            junction.tails_per_lane[vehicles[veh].startingLane][totalTime - 1] += 1
                            vehicles[veh].headTimes[vehicles[veh].index] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                            continue
                        # verifico se il veicolo è in coda
                        if leader and leader[1] <= 0.5 and leader_lane == veh_current_lane:
                            junction.tails_per_lane[vehicles[veh].startingLane][totalTime - 1] += 1
                            vehicles[veh].tailTimes[vehicles[veh].index] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                            continue
                    else:
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

                # controllo se il veicolo è in una lane uscente
                if veh_current_lane in junction.outgoingLanes:
                    if veh in junction.vehiclesEntering:
                        vehicles[veh].startingLane = ''
                        junction.vehiclesEntering.remove(veh)
                        junction.arrived[totalTime - 1] += 1

    """Salvo tutti i risultati della simulazione e li ritorno"""

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

    meanHeadTime = sum(headTimes) / len(headTimes)
    for headTime in headTimes:
        varHeadTime += (headTime - meanHeadTime) ** 2
    stDevHeadTime = sqrt(varHeadTime / len(headTimes))

    meanTailTime = sum(tailTimes) / len(tailTimes)
    for tailTime in tailTimes:
        varTailTime += (tailTime - meanTailTime) ** 2
    stDevTailTime = sqrt(varTailTime / len(tailTimes))

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
        if junction.arrived == 0 and junction.departed == 0:
            meanThroughput.append(1)
        else:
            meanThroughput.append(junction.arrived / junction.departed)
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

    traci.close()

    if output_redirection:

        sys.stdout = origin_stdout

        sys.stderr = origin_stderr

    queue.put([meanTravelTime, stDevTravelTime, max(travelTimes), meanHeadTime, stDevHeadTime, max(headTimes),
               meanTailTime, stDevTailTime, max(tailTimes), meanSpeed, stDevSpeed,
               round(sum(meanTails) / len(meanTails), 2), round(sum(stDevTails) / len(stDevTails), 2), max(maxTails),
               round(sum(meanThroughput) / len(meanThroughput), 2), meanTails, stDevTails, maxTails, meanThroughput])
