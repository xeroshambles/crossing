import random
from math import sqrt
from config_multi import *

from traffic_elements_multi.vehicle import Vehicle

import traci


class Simulation:
    """Classe per gestire tutti gli aspetti della simulazione"""

    def getSimulationVehicles(self, simulation_vehicles):
        """Costruisce la lista composta dalle auto presenti nella simulazione"""

        # carico nella lista le auto partite
        loadedIDList = traci.simulation.getDepartedIDList()
        for id_vehicle in loadedIDList:
            if id_vehicle not in simulation_vehicles:
                simulation_vehicles.append(id_vehicle)
                traci.vehicle.setSpeed(id_vehicle, traci.vehicle.getMaxSpeed(id_vehicle))

        # elimino nella lista le auto arrivate
        arrivedIDList = traci.simulation.getArrivedIDList()
        for id_vehicle in arrivedIDList:
            if id_vehicle in simulation_vehicles:
                simulation_vehicles.pop(simulation_vehicles.index(id_vehicle))

        return simulation_vehicles

    def generateVehicles(self, numberOfSteps, numberOfVehicles, vehicles, seed, instantPay=instantPay):
        """Genero i veicoli a partire dagli incroci esterni della rete verso quelli interni"""

        c = 0
        t = 0
        depart = 0
        auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]

        random.seed(seed)

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
            vehicles[idV].travelTimes.append(0)
            base_route = vehicles[idV].getInitialRoute()
            route = traci.simulation.findRoute(base_route[0], base_route[1])
            traci.route.add(f'route_{i}', route.edges)
            vehicles[idV].setEdgeObjective(base_route[1])
            traci.vehicle.add(idV, f'route_{i}', depart=depart)
            traci.vehicle.setLaneChangeMode(idV, 512)

        return vehicles

    def colorVehicles(self, numberOfVehicles):
        """Assegno un colore diverso alle auto per meglio distinguerle nella simulazione"""

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

    def getDistanceFromLaneEnd(self, spawn_distance, lane_length, shape):
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

    def checkVehiclesRoute(self, vehicles, simulation_vehicles, numberOfVehicles):
        """Controllo se i veicoli hanno raggiunto l'obbiettivo e, nel caso, riassegno una nuova route"""

        for i in range(0, sum(numberOfVehicles)):
            idV = f'idV{i}'
            if idV in simulation_vehicles:
                vehicles[idV].travelTimes[vehicles[idV].travelIndex] += 1
                vehicles[idV].changeTarget(staticRoutes=routeMode)

        return vehicles

    def checkVehiclesState(self, vehicles, simulation_vehicles, junctions, time, schema):
        """Funzione che controlla il posizionamento dei veicoli e calcola le relative misure"""

        for junction in junctions:

            # per ogni junction creo dei nuovi valori per il calcolo del throughput
            vehs_in_junction = junction.getActualVehicles(simulation_vehicles)

            # per ogni junction creo dei nuovi valori per il calcolo delle code nelle lane entranti
            for lane in junction.tailsPerLane:
                junction.tailsPerLane[lane].append(0)

            # loop per tutti i veicoli della junction corrente
            for veh in vehs_in_junction:
                veh_current_lane = traci.vehicle.getLaneID(veh)

                # controllo se il veicolo è in una lane entrante
                if veh_current_lane in junction.incomingLanes:
                    vehicles[veh].startingLane = veh_current_lane
                    # registro il veicolo nella gestione dell'incrocio
                    if veh not in junction.vehiclesEntering:
                        vehicles[veh].isNextEdge = True
                        vehicles[veh].headTimes.append(0)
                        vehicles[veh].tailTimes.append(0)
                        vehicles[veh].speeds.append([])
                        vehicles[veh].spawnDistances.append(0)
                        junction.vehiclesEntering.append(veh)
                        junction.departed += 1
                    # calcolo la distanza tra il veicolo e l'inizio dell'incrocio
                    spawn_distance = traci.vehicle.getDistance(veh) - sum(vehicles[veh].spawnDistances[:-1])
                    vehicles[veh].spawnDistances[-1] = spawn_distance
                    distance = self.getDistanceFromLaneEnd(spawn_distance, traci.lane.getLength(veh_current_lane),
                                                           junction.junction_shape)
                    # # se la distanza è compresa 115 e 70 provo a far cambiare la lane
                    if 70 <= distance < 115:
                        if vehicles[veh].isNextEdge:
                            vehicles[veh].edgeIndex += 1
                            vehicles[veh].isNextEdge = False
                        vehicles[veh].tryChangeLane(junction)
                    # se la distanza è tra 70 e 50 e il veicolo non è riuscito ad andare nella lane corretta
                    # impedisco di cambiare lane e cambio temporaneamente la route
                    if 50 <= distance < 70:
                        vehicles[veh].checkCorrectLane(junction)
                    if distance < 15:
                        vehicles[veh].speeds[-1].append(traci.vehicle.getSpeed(veh))
                    veh_length = traci.vehicle.getLength(veh)
                    check = veh_length / 2 + 0.2
                    leader = traci.vehicle.getLeader(veh)
                    # se il veicolo è fermo
                    if traci.vehicle.getSpeed(veh) <= 1:
                        junction.tailsPerLane[veh_current_lane][time - 1] += 1
                        # verifico se il veicolo è in testa e nel caso lo coloro di blu
                        if check >= distance and ((leader and leader[1] < 0) or not leader):
                            vehicles[veh].headTimes[-1] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (0, 0, 255))
                            continue
                        # verifico se il veicolo è in coda e nel caso lo coloro di rosso
                        if leader and leader[1] <= 0.5 and vehicles[leader[0]].startingLane == veh_current_lane \
                                and traci.vehicle.getSpeed(leader[0]) <= 1:
                            vehicles[veh].tailTimes[-1] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (255, 0, 0))
                            continue
                    # se il veicolo non è fermo lo coloro di giallo
                    else:
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 255, 0))

                # controllo se il veicolo è all'interno della junction
                if junction.junctionID + '_' in veh_current_lane:
                    spawn_distance = traci.vehicle.getDistance(veh) - sum(vehicles[veh].spawnDistances[:-1])
                    vehicles[veh].spawnDistances[-1] = spawn_distance
                    leader = traci.vehicle.getLeader(veh)
                    leader_lane = ''
                    if leader:
                        leader_lane = traci.vehicle.getLaneID(leader[0])
                    vehicles[veh].speeds[-1].append(traci.vehicle.getSpeed(veh))
                    # se il veicolo è fermo
                    if traci.vehicle.getSpeed(veh) <= 1:
                        junction.tailsPerLane[vehicles[veh].startingLane][time - 1] += 1
                        # verifico se il veicolo è in testa e nel caso lo coloro di blu
                        if (leader and leader_lane != veh_current_lane) or not leader:
                            vehicles[veh].headTimes[-1] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (0, 0, 255))
                            continue
                        # verifico se il veicolo è in coda e nel caso lo coloro di rosso
                        if leader and leader[1] <= 0.5:
                            vehicles[veh].tailTimes[-1] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (255, 0, 0))
                            continue
                    # se il veicolo non è fermo lo coloro di giallo
                    else:
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 255, 0))

                # controllo se il veicolo è in una lane uscente
                if veh_current_lane in junction.outgoingLanes:
                    if veh in junction.vehiclesEntering:
                        junction.vehiclesEntering.remove(veh)
                        junction.arrived += 1

        return vehicles, junctions

    def saveResults(self, vehicles, simulation_vehicles, junctions):
        """Funzione che raggruppa tutte le misure effattuate"""

        meanTravelTimes = []  # lista dei tempi di percorrenza medi per ogni veicolo
        varTravelTime = 0  # varianza rispetto al tempo di percorrenza
        maxTravelTime = -1  # tempo massimo di percorrenza di un veicolo
        meanHeadTimes = []  # lista dei tempi passati in testa medi per ogni veicolo
        varHeadTime = 0  # varianza rispetto al tempo passato in testa
        maxHeadTime = -1  # tempo in testa massimp di un veicolo
        meanTailTimes = []  # lista dei tempi in coda medi per ogni veicolo
        varTailTime = 0  # varianza rispetto al tempo passato in coda
        maxTailTime = -1  # tempo in coda massimo di un veicolo
        meanSpeeds = []  # lista delle velocità medie assunte dai veicoli nei pressi dell'incrocio
        varSpeed = 0  # varianza rispetto alla velocità dei veicoli
        meanTailLength = []  # lista delle lunghezze medie delle code rilevate sulle lane entranti
        varTailLength = 0  # varianza rispetto alla coda
        maxTailLength = -1  # coda massima rilevata su tutte le lane entranti
        divertedVehicles = 0  # numero di veicoli che hanno deviato nel percorrere la propria route

        for veh in vehicles:
            if veh in simulation_vehicles:

                if vehicles[veh].hasDiverted:
                    divertedVehicles += 1

                if len(vehicles[veh].travelTimes) >= 2:
                    meanTravelTimes.append(round(sum(vehicles[veh].travelTimes[:-1]) /
                                                 len(vehicles[veh].travelTimes[:-1]), 2))
                    maxTravT = max(vehicles[veh].travelTimes[:-1])
                    if maxTravT > maxTravelTime:
                        maxTravelTime = maxTravT

                if len(vehicles[veh].headTimes) >= 2:
                    meanHeadTimes.append(round(sum(vehicles[veh].headTimes[:-1]) /
                                               len(vehicles[veh].headTimes[:-1]), 2))
                    maxHT = max(vehicles[veh].headTimes[:-1])
                    if maxHT > maxHeadTime:
                        maxHeadTime = maxHT

                if len(vehicles[veh].tailTimes) >= 2:
                    meanTailTimes.append(round(sum(vehicles[veh].tailTimes[:-1]) /
                                               len(vehicles[veh].tailTimes[:-1]), 2))
                    maxTailT = max(vehicles[veh].tailTimes[:-1])
                    if maxTailT > maxTailTime:
                        maxTailTime = maxTailT

                if len(vehicles[veh].speeds) >= 2:
                    meanSpds = []
                    for speeds in vehicles[veh].speeds[:-1]:
                        meanSpds.append(round(sum(speeds) / len(speeds), 2))
                    meanSpeeds.append(round(sum(meanSpds) / len(meanSpds), 2))

        meanTravelTime = round(sum(meanTravelTimes) / len(meanTravelTimes), 2)
        for travelTime in meanTravelTimes:
            varTravelTime += (travelTime - meanTravelTime) ** 2
        stDevTravelTime = round(sqrt(varTravelTime / len(meanTravelTimes)), 2)

        meanHeadTime = round(sum(meanHeadTimes) / len(meanHeadTimes), 2)
        for headTime in meanHeadTimes:
            varHeadTime += (headTime - meanHeadTime) ** 2
        stDevHeadTime = round(sqrt(varHeadTime / len(meanHeadTimes)), 2)

        meanTailTime = round(sum(meanTailTimes) / len(meanTailTimes), 2)
        for tailTime in meanTailTimes:
            varTailTime += (tailTime - meanTailTime) ** 2
        stDevTailTime = round(sqrt(varTailTime / len(meanTailTimes)), 2)

        meanSpeed = round(sum(meanSpeeds) / len(meanSpeeds), 2)
        for speed in meanSpeeds:
            varSpeed += (speed - meanSpeed) ** 2
        stDevSpeed = round(sqrt(varSpeed / len(meanSpeeds)), 2)

        meanTailsLength = []
        stDevTailsLength = []
        maxTailsLength = []
        meanThroughputs = []

        for junction in junctions:
            if junction.departed == 0:
                meanThroughputs.append(1)
            else:
                meanThroughputs.append(round(junction.arrived / junction.departed, 2))
            for lane in junction.tailsPerLane:
                meanTailLength.append(round(sum(junction.tailsPerLane[lane]) / len(junction.tailsPerLane[lane]), 2))
                maxTL = max(junction.tailsPerLane[lane])
                if maxTL > maxTailLength:
                    maxTailLength = maxTL
            meanTl = round(sum(meanTailLength) / len(meanTailLength), 2)
            for tail in meanTailLength:
                varTailLength += (tail - meanTl) ** 2
            meanTailsLength.append(meanTl)
            stDevTailsLength.append(round(sqrt(varTailLength / len(meanTailLength)), 2))
            maxTailsLength.append(maxTailLength)
            maxTailLength = -1

        meanTail = round(sum(meanTailsLength) / len(meanTailsLength), 2)
        stDevTail = round(sum(stDevTailsLength) / len(stDevTailsLength), 2)
        maxTail = max(maxTailsLength)
        meanThroughput = round(sum(meanThroughputs) / len(meanThroughputs), 2)

        return meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, \
               stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanThroughput, \
               divertedVehicles, meanTailsLength, stDevTailsLength, maxTailsLength, meanThroughputs
