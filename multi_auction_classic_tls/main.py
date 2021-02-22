import os
import sys
from math import sqrt
from config import *
from utils import *
from multi_auction_classic_tls.trafficElements.junction import ThreeWayJunction, FourWayJunction
from multi_auction_classic_tls.trafficElements.vehicle import Vehicle

import traci
from sumolib import miscutils


def generateVehiclesMulti(numberOfSteps, numberOfVehicles, vehicles, routeMode, instantPay):
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
        vehicles[idV] = Vehicle(idV, instantPay)
        base_route = vehicles[idV].generateRoute(static=routeMode)
        route = traci.simulation.findRoute(base_route[0], base_route[1])
        traci.route.add(f'route_{i}', route.edges)
        vehicles[idV].setEdgeObjective(base_route[1])
        traci.vehicle.add(idV, f'route_{i}', depart=depart)


def run(numberOfSteps, numberOfVehicles, schema, sumoCmd, path, index, queue):
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

    traci.start(sumoCmd, port=port, numRetries=100)

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    departed = 0
    departed_vehicles = []
    totalTime = 0  # tempo totale di simulazione
    step_incr = 0.500  # incremento del numero di step della simulazione
    sec = 1 / step_incr
    headTimes = []  # lista dei tempi passati in testa per ogni veicolo
    varHeadTime = 0  # varianza rispetto al tempo passato in testa
    tailTimes = []  # lista dei tempi in coda per ogni veicolo
    varTailTime = 0  # varianza rispetto al tempo passato in coda
    meanSpeeds = []  # medie delle velocità assunte dai veicoli ad ogni step
    varSpeed = 0  # varianza rispetto alla velocità dei veicoli
    meanTailLength = []  # medie delle lunghezze delle code rilevate sulle lane entranti ad ogni step
    varTail = 0  # varianza rispetto alla coda
    maxTail = -1  # coda massima rilevata su tutte le lane entranti

    """Con il seguente ciclo inizializzo i veicoli assegnadogli una route legale generata casualmente e, in caso di 
    schema di colori non significativo,dandogli un colore diverso per distinguerli meglio all'interno della 
    simulazione"""

    generateVehiclesMulti(stepsSpawn, numberOfVehicles, vehicles, routeMode, instantPay)

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

    n_step = 0

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        traci.simulationStep()
        totalTime += step_incr
        n_step += 1
        departed += traci.simulation.getDepartedNumber()
        departed_vehicles += traci.simulation.getDepartedIDList()

        # controllo se i veicoli hanno raggiunto l'obbiettivo e, nel caso, riassegno una nuova route
        for i in range(0, sum(numberOfVehicles)):
            vehicles[f'idV{i}'].changeTarget(staticRoutes=routeMode)

        # controllo i veicoli all'interno degli incroci
        for veh in departed_vehicles:
            lane = traci.vehicle.getLaneID(veh)
            if lane[1] == 'n':
                vehicles[veh].speeds[vehicles[veh].index].append(traci.vehicle.getSpeed(veh))
                if schema in ['s', 'S']:
                    traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

        for junction in junctions:

            bs = f"{'0' if junction.nID <= 9 else ''}"

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

            if n_step % sec == 0:
                vehs_in_junction = junction.getActualVehicles()
                for lane in junction.tails_per_lane:
                    junction.tails_per_lane[lane].append(0)
                # loop per tutti i veicoli nell'incrocio
                for veh in vehs_in_junction:
                    veh_current_lane = traci.vehicle.getLaneID(veh)
                    # controllo se il veicolo è in una lane uscente
                    if veh_current_lane[1:3] == bs + str(junction.nID):
                        if vehicles[veh].isEntered == 1 and veh in junction.vehiclesEntering:
                            vehicles[veh].isEntered = 0
                            junction.vehiclesEntering.remove(veh)
                            junction.arrived += 1
                    # controllo se il veicolo è in una lane entrante
                    if veh_current_lane[4:6] == bs + str(junction.nID):
                        if vehicles[veh].isEntered == 0:
                            vehicles[veh].isEntered = 1
                            junction.vehiclesEntering.append(veh)
                            junction.departed += 1
                        spawn_distance = traci.vehicle.getDistance(veh)
                        distance = getDistanceFromLaneEnd(spawn_distance, traci.lane.getLength(veh_current_lane),
                                                          junction.junction_shape)
                        if distance < 15:
                            vehicles[veh].speeds[vehicles[veh].index].append(traci.vehicle.getSpeed(veh))
                        veh_length = traci.vehicle.getLength(veh)
                        check = veh_length / 2 + 0.2
                        leader = traci.vehicle.getLeader(veh)
                        if traci.vehicle.getSpeed(veh) <= 1:
                            # verifico se il veicolo si è fermato al di fuori del punto di spawn
                            if spawn_distance > 0:
                                junction.tails_per_lane[veh_current_lane][int(n_step / sec) - 1] += 1
                            # verifico se il veicolo è in testa
                            if check >= distance and ((leader and leader[1] > 0.5) or not leader):
                                vehicles[veh].headTimes[vehicles[veh].index] += 1
                                if schema in ['s', 'S']:
                                    traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                                continue
                            # verifico se il veicolo è in coda
                            if leader and leader[1] <= 0.5:
                                vehicles[veh].tailTimes[vehicles[veh].index] += 1
                                if schema in ['s', 'S']:
                                    traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                                continue
                        else:
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

    for veh in vehicles:
        if int(veh[-1]) < departed:
            headTimes.append(sum(vehicles[veh].headTimes) / len(vehicles[veh].headTimes))
            tailTimes.append(sum(vehicles[veh].tailTimes) / len(vehicles[veh].tailTimes))
            for speeds in vehicles[veh].speeds:
                if len(speeds) > 0:
                    meanSpeeds.append(sum(speeds) / len(speeds))

    meanHeadTime = sum(headTimes) / len(headTimes)
    for headTime in headTimes:
        varHeadTime += (headTime - meanHeadTime) ** 2
    varHeadTime /= len(headTimes)

    meanTailTime = sum(tailTimes) / len(tailTimes)
    for tailTime in tailTimes:
        varTailTime += (tailTime - meanTailTime) ** 2
    varTailTime /= len(tailTimes)

    if len(meanSpeeds) > 0:
        meanSpeed = sum(meanSpeeds) / len(meanSpeeds)
        for speed in meanSpeeds:
            varSpeed += (speed - meanSpeed) ** 2
        varSpeed /= len(meanSpeeds)
    else:
        meanSpeed = 0
        varSpeed = 0

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
        stDevTails.append(sqrt(varTail))
        maxTails.append(maxTail)

    traci.close()

    if output_redirection:

        sys.stdout = origin_stdout

        sys.stderr = origin_stderr

    queue.put([departed, meanHeadTime, sqrt(varHeadTime), max(headTimes), meanTailTime, sqrt(varTailTime),
               max(tailTimes), meanSpeed, sqrt(varSpeed), round(sum(meanTails) / len(meanTails), 2),
               round(sum(stDevTails) / len(stDevTails), 2), max(maxTails),
               round(sum(meanThroughput) / len(meanThroughput), 2)])
