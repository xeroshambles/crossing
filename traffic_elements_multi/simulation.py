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

    def generateVehicles(self, numberOfSteps, numberOfVehicles, vehicles, instantPay, seed):
        """Genero veicoli per ogni route possibile nel caso di incrocio multiplo"""

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
            base_route = vehicles[idV].getInitialRoute()
            route = traci.simulation.findRoute(base_route[0], base_route[1])
            traci.route.add(f'route_{i}', route.edges)
            vehicles[idV].setEdgeObjective(base_route[1])
            traci.vehicle.add(idV, f'route_{i}', depart=depart)
            traci.vehicle.setLaneChangeMode(idV, 512)

        return vehicles

    def colorVehicles(self, numberOfVehicles):
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
            for lane in junction.tails_per_lane:
                junction.tails_per_lane[lane].append(0)

            # loop per tutti i veicoli della junction corrente
            for veh in vehs_in_junction:
                veh_current_lane = traci.vehicle.getLaneID(veh)

                # controllo se il veicolo è in una lane entrante
                if veh_current_lane in junction.incomingLanes:
                    vehicles[veh].startingLane = veh_current_lane
                    # registro il veicolo nella gestione dell'incrocio
                    if veh not in junction.vehiclesEntering:
                        junction.vehiclesEntering.append(veh)
                        junction.departed += 1
                        vehicles[veh].edgeIndex += 1
                        vehicles[veh].headTimes.append(0)
                        vehicles[veh].tailTimes.append(0)
                        vehicles[veh].spawnDistances.append(0)
                    # calcolo la distanza tra il veicolo e l'inizio dell'incrocio
                    spawn_distance = traci.vehicle.getDistance(veh) - sum(vehicles[veh].spawnDistances[:-1])
                    vehicles[veh].spawnDistances[-1] = spawn_distance
                    distance = self.getDistanceFromLaneEnd(spawn_distance, traci.lane.getLength(veh_current_lane),
                                                      junction.junction_shape)
                    # # se la distanza è compresa 115 e 70 provo a far cambiare la lane
                    if 70 <= distance < 115:
                        vehicles[veh].tryChangeLane()
                    # se la distanza è tra 70 e 50 e il veicolo non è riuscito ad andare nella lane corretta
                    # impedisco di cambiare lane e cambio temporaneamente la route
                    if 50 <= distance < 70:
                        vehicles[veh].checkCorrectLane(junction)
                    if distance < 15:
                        vehicles[veh].speeds.append(traci.vehicle.getSpeed(veh))
                    veh_length = traci.vehicle.getLength(veh)
                    check = veh_length / 2 + 0.2
                    leader = traci.vehicle.getLeader(veh)
                    # se il veicolo è fermo
                    if traci.vehicle.getSpeed(veh) <= 1:
                        # verifico se il veicolo è in testa e nel caso lo coloro di blu
                        if check >= distance and ((leader and leader[1] < 0) or not leader):
                            junction.tails_per_lane[veh_current_lane][time - 1] += 1
                            vehicles[veh].headTimes[vehicles[veh].edgeIndex] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (0, 0, 255))
                        # verifico se il veicolo è in coda e nel caso lo color di rosso
                        elif leader and leader[1] <= 0.5 and vehicles[leader[0]].startingLane == veh_current_lane \
                                and traci.vehicle.getColor(leader[0]) != (255, 255, 0, 255):
                            junction.tails_per_lane[veh_current_lane][time - 1] += 1
                            vehicles[veh].tailTimes[vehicles[veh].edgeIndex] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (255, 0, 0))
                    # se il veicolo non è fermo lo coloro di giallo
                    else:
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 255, 0))

                # controllo se il veicolo è all'interno della junction
                elif veh_current_lane in junction.crossingLanes:
                    spawn_distance = traci.vehicle.getDistance(veh) - \
                                     sum(vehicles[veh].spawnDistances[:-1])
                    vehicles[veh].spawnDistances[-1] = spawn_distance
                    leader = traci.vehicle.getLeader(veh)
                    leader_lane = ''
                    if leader:
                        leader_lane = traci.vehicle.getLaneID(leader[0])
                    vehicles[veh].speeds.append(traci.vehicle.getSpeed(veh))
                    # se il veicolo è fermo
                    if traci.vehicle.getSpeed(veh) <= 1:
                        # verifico se il veicolo è in testa e nel caso lo coloro di blu
                        if (leader and leader_lane != veh_current_lane) or not leader:
                            junction.tails_per_lane[vehicles[veh].startingLane][time - 1] += 1
                            vehicles[veh].headTimes[vehicles[veh].edgeIndex] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (0, 0, 255))
                        # verifico se il veicolo è in coda e nel caso lo coloro di rosso
                        elif leader and leader[1] <= 0.5:
                            junction.tails_per_lane[vehicles[veh].startingLane][time - 1] += 1
                            vehicles[veh].tailTimes[vehicles[veh].edgeIndex] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (255, 0, 0))
                    # se il veicolo non è fermo lo coloro di giallo
                    else:
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 255, 0))

                # controllo se il veicolo è in una lane uscente
                elif veh_current_lane in junction.outgoingLanes:
                    if veh in junction.vehiclesEntering:
                        junction.vehiclesEntering.remove(veh)
                        junction.arrived += 1

        return vehicles, junctions

    def saveResults(self, vehicles, simulation_vehicles, junctions):
        """Funzione che raggruppa tutte le misure effattuate"""

        travelTimes = []  # lista dei tempi di percorrenza medi per ogni veicolo
        varTravelTime = 0  # varianza rispetto al tempo di percorrenza
        meanHeadTimes = []  # lista dei tempi passati in testa medi per ogni veicolo
        varHeadTime = 0  # varianza rispetto al tempo passato in testa
        meanTailTimes = []  # lista dei tempi in coda medi per ogni veicolo
        varTailTime = 0  # varianza rispetto al tempo passato in coda
        meanSpeeds = []  # lista delle velocità medie assunte dai veicoli nei pressi dell'incrocio
        varSpeed = 0  # varianza rispetto alla velocità dei veicoli
        meanTailLength = []  # lista delle lunghezze medie delle code rilevate sulle lane entranti
        varTail = 0  # varianza rispetto alla coda
        maxTail = -1  # coda massima rilevata su tutte le lane entranti

        for veh in vehicles:
            if veh in simulation_vehicles:
                travelTimes.append(sum(vehicles[veh].travelTimes) / len(vehicles[veh].travelTimes))
                if len(vehicles[veh].headTimes) > 0:
                    meanHeadTimes.append(sum(vehicles[veh].headTimes) / len(vehicles[veh].headTimes))
                if len(vehicles[veh].tailTimes) > 0:
                    meanTailTimes.append(sum(vehicles[veh].tailTimes) / len(vehicles[veh].tailTimes))
                if len(vehicles[veh].speeds) > 0:
                    meanSpeeds.append(sum(vehicles[veh].speeds) / len(vehicles[veh].speeds))

        meanTravelTime = sum(travelTimes) / len(travelTimes)
        for travelTime in travelTimes:
            varTravelTime += (travelTime - meanTravelTime) ** 2
        stDevTravelTime = sqrt(varTravelTime / len(travelTimes))
        maxTravelTime = max(travelTimes)

        if len(meanHeadTimes) > 0:
            meanHeadTime = sum(meanHeadTimes) / len(meanHeadTimes)
            for headTime in meanHeadTimes:
                varHeadTime += (headTime - meanHeadTime) ** 2
            stDevHeadTime = sqrt(varHeadTime / len(meanHeadTimes))
            maxHeadTime = max(meanHeadTimes)
        else:
            meanHeadTime = -1
            stDevHeadTime = -1
            maxHeadTime = -1

        if len(meanTailTimes) > 0:
            meanTailTime = sum(meanTailTimes) / len(meanTailTimes)
            for tailTime in meanTailTimes:
                varTailTime += (tailTime - meanTailTime) ** 2
            stDevTailTime = sqrt(varTailTime / len(meanTailTimes))
            maxTailTime = max(meanTailTimes)
        else:
            meanTailTime = -1
            stDevTailTime = -1
            maxTailTime = -1

        if len(meanSpeeds) > 0:
            meanSpeed = sum(meanSpeeds) / len(meanSpeeds)
            for speed in meanSpeeds:
                varSpeed += (speed - meanSpeed) ** 2
            stDevSpeed = sqrt(varSpeed / len(meanSpeeds))
        else:
            meanSpeed = -1
            stDevSpeed = -1

        meanTails = []
        stDevTails = []
        maxTails = []
        meanThroughput = []

        for junction in junctions:
            if junction.departed == 0:
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

        meanTail = round(sum(meanTails) / len(meanTails), 2)
        stDevTail = round(sum(stDevTails) / len(stDevTails), 2)
        maxTail = max(maxTails)
        meanTp = round(sum(meanThroughput) / len(meanThroughput), 2)

        return meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, \
               stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, meanTails, \
               stDevTails, maxTails, meanThroughput
