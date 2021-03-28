from inpout_multi import redirectOutput

from traffic_elements_multi.junction import FourWayJunction
from traffic_elements_multi.simulation import *

import traci
from sumolib import miscutils


def run(numberOfSteps, numberOfVehicles, schema, sumoCmd, cellsPerSide, matrixTrajectories, securitySecs, path,
        index, queue, seed):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    redirectOutput(path, index, True)

    traci.start(sumoCmd, port=port, numRetries=2000)

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    total_time = 0.00  # tempo totale di simulazione
    step_incr = 0.05  # incremento di step
    simulation_vehicles = []  # contiene la lista di auto presenti nella simulazione

    simulation = Simulation()

    """Inizializzo i veicoli assegnadogli una route generata casualmente e, in caso di schema di colori 
    non significativo, dandogli un colore diverso per distinguerli meglio all'interno della simulazione"""

    vehicles = simulation.generateVehicles(stepsSpawn, numberOfVehicles, vehicles, seed)

    if schema in ['n', 'N']:
        simulation.colorVehicles(numberOfVehicles)

    """Inizializzo gli incroci che fanno parte della simulazione"""

    junctions = [FourWayJunction(n, vehicles, cellsPerSide=cellsPerSide, matrixTrajectories=matrixTrajectories,
                                 securitySecs=securitySecs) for n in range(1, 26)]

    junctions_list = [junction for junction in junctions if junction.nID in vertex_junctions_ids +
                      lateral_junctions_ids]

    """Inizializzo le auto che fanno parte della simulazione"""

    simulation_vehicles = simulation.getSimulationVehicles(simulation_vehicles)

    """Apro il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    while traci.simulation.getMinExpectedNumber() > 0 and total_time < numberOfSteps:
        total_time = round(total_time + step_incr, 2)
        traci.simulationStep()

        simulation_vehicles = simulation.getSimulationVehicles(simulation_vehicles)

        if total_time % 1 == 0:
            vehicles = simulation.checkVehiclesRoute(vehicles, simulation_vehicles, numberOfVehicles)

        for junction in junctions_list:  # scorro la lista incroci
            rM = junction.reservationManager

            for vehicle in simulation_vehicles:  # scorro l'array delle auto ancora presenti nella simulazione

                vehicle_in_list = True
                # vedo se l'auto corrente è tra le auto segnate per attraversare l'incrocio
                try:
                    present = int(rM.arrivalList.index(vehicle))
                except ValueError:
                    vehicle_in_list = False

                pos = traci.vehicle.getPosition(vehicle)
                # se l'auto non è in lista allora guardo se sta entrando nelle vicinanze dell'incrocio
                if not vehicle_in_list:

                    if (rM.stop[3] - 50 <= pos[0] <= rM.stop[1] + 50) and \
                            (rM.stop[2] - 50 <= pos[1] <= rM.stop[0] + 50):
                        # inserisco l'auto nella lista d'arrivo di quell'incrocio
                        rM.arrivalList.append(vehicle)
                        # inserisco l'auto nella lista d'attesa di quell'incrocio
                        rM.waitingList.append(vehicle)
                        traci.vehicle.setMaxSpeed(vehicle, 6.944444)
                else:
                    if not ((rM.stop[3] - 50 <= pos[0] <= rM.stop[1] + 50) and
                            (rM.stop[2] - 50 <= pos[1] <= rM.stop[0] + 50)) and vehicle in rM.arrivalList:
                        rM.arrivalList.remove(vehicle)
                # se l'auto è in attesa e non è ferma, guardo se è vicina allo stop e fermo se l'incrocio è già occupato
                if vehicle in rM.waitingList and vehicle not in rM.stoppedList:
                    # se l'incrocio ha 4 lati
                    if len(rM.stop) > 3:
                        if (rM.stop[3] - 13.5 <= pos[0] <= rM.stop[1] + 13.5) and \
                                (rM.stop[2] - 13.5 <= pos[1] <= rM.stop[0] + 13.5):

                            traci.vehicle.setDecel(vehicle, 1.92901)
                            traci.vehicle.setAccel(vehicle, 1.92901)
                            # salvo l'auto leader di quella lane
                            leader = traci.vehicle.getLeader(vehicle)
                            if leader:
                                # se il leader ha già iniziato ad attraversare l'incrocio non lo conto
                                if leader[0] not in rM.waitingList:
                                    leader = None
                            # se non c'è il leader su quella lane
                            if not leader:
                                # controllo se l'auto non ha subito rallentamenti e la fermo in 16 m
                                if round(traci.vehicle.getSpeed(vehicle), 2) == \
                                        round(traci.vehicle.getMaxSpeed(vehicle), 2):
                                    rM.arrivalVehicle(vehicles[vehicle])

                                # se l'auto ha subito rallentamenti calcolo dalla sua velocità in quanti metri
                                # dall'incrocio si fermerebbe se la facessi rallentare subito, se si va a fermare in
                                # prossimità dell'incrocio allora avvio l'arresto del veicolo altrimenti aspetto
                                # il prossimo step e ricontrollo
                                else:
                                    dist_stop = 0
                                    speed = traci.vehicle.getSpeed(vehicle)
                                    decel = traci.vehicle.getDecel(vehicle)

                                    ang = traci.vehicle.getAngle(vehicle)

                                    if ang == 90:
                                        dist_stop = abs(rM.stop[3] - pos[0])
                                    if ang == 0:
                                        dist_stop = abs(rM.stop[2] - pos[1])
                                    if ang == 270:
                                        dist_stop = abs(rM.stop[1] - pos[0])
                                    if ang == 180:
                                        dist_stop = abs(rM.stop[0] - pos[1])

                                    dist_to_stop = (speed * speed) / (2 * decel)

                                    if dist_to_stop + 2 >= dist_stop:
                                        rM.arrivalVehicle(vehicles[vehicle])
            # se ci sono auto che stanno attraversando l'incrocio guardo se la situazione dell'incrocio è cambiata
            if rM.passageList is not None:

                # se l'auto è appena entrata nell'area dell'incrocio salvo la cella in cui si trova
                for x in rM.cellPassageList:
                    route = traci.vehicle.getRouteID(x[0])
                    edges = traci.route.getEdges(route)
                    lane = vehicles[x[0]].getLaneIndexFromEdges(edges, junction)
                    if lane != 0:
                        # se l'auto non gira a destra
                        if x[1] is None and x[2] is None:
                            pos = traci.vehicle.getPosition(x[0])
                            if rM.inCrossing(pos):
                                vett_id = rM.cellPassageList.index(x)
                                rM.cellPassageList[vett_id] = rM.getCellFromPosVehicle(x[0])

                rM.freePath(vehicles)
                # se ci sono auto ferme, vedo se posso farne partire qualcuna
                if len(rM.stoppedList) > 0:

                    # scorro tra tutte le auto ferme e se una è compatibile con la matrice allora la faccio partire
                    for stopped_vehicle in rM.stoppedList:
                        if stopped_vehicle in rM.stoppedList:
                            if rM.getFromCrossingMatrix(vehicles[stopped_vehicle]):
                                # vedo se il suo percorso è libero e nel caso la faccio partire
                                rM.restartVehicle(vehicles[stopped_vehicle])

            # riaccelero i veicoli all'uscita dall'incrocio
            for exit_vehicle in rM.precedentPassageList:
                if exit_vehicle not in rM.passageList:
                    traci.vehicle.setMaxSpeed(exit_vehicle[0], 13.888888)
                    traci.vehicle.setSpeed(exit_vehicle[0], 13.888888)
                    traci.vehicle.setSpeedMode(exit_vehicle[0], 31)
            rM.precedentPassageList = rM.passageList[:]
            # ogni 10 step pulisco la matrice da valori troppo vecchi
            if total_time % round(10 * step_incr, 2) == 0:
                rM.cleanMatrix()

        if total_time % 1 == 0:
            vehicles, junctions = simulation.checkVehiclesState(vehicles, simulation_vehicles, junctions,
                                                                int(total_time), schema)

    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, \
    stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, divertedVehicles, \
    meanTails, stDevTails, maxTails, meanThroughput = simulation.saveResults(vehicles, simulation_vehicles, junctions)

    traci.close()

    redirectOutput(path, index, False)

    queue.put([meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime,
               stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp,
               divertedVehicles, meanTails, stDevTails, maxTails, meanThroughput])
