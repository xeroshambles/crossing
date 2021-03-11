from inpout_multi import redirect_output

from trafficElements_multi.junction import FourWayJunction
from trafficElements_multi.simulation import *

import traci
from sumolib import miscutils


def run(numberOfSteps, numberOfVehicles, schema, sumoCmd, cellsPerSide, matrixTrajectories, securitySecs, path,
        index, queue, seed):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    redirect_output(path, index, True)

    traci.start(sumoCmd, port=port, numRetries=1000)

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    departed = 0  # numero di veicoli partiti entro la fine della simulazione
    departed_vehicles = []  # lista dei veicoli partiti entro la fine della simulazione
    totalTime = 0  # tempo totale di simulazione
    step_incr = 0.050  # incremento del numero di step della simulazione
    sec = 1 / step_incr  # numero che indica ogni quanti sotto step devo calcolare le misure

    array_vehicles = []  # contiene la lista di auto presenti nella simulazione

    simulation = Simulation()

    """Con il seguente ciclo inizializzo i veicoli assegnadogli una route legale generata casualmente e, in caso di 
        schema di colori non significativo,dandogli un colore diverso per distinguerli meglio all'interno della 
        simulazione"""

    vehicles = simulation.generateVehicles(stepsSpawn, numberOfVehicles, vehicles, routeMode, instantPay, seed)

    if schema in ['n', 'N']:
        simulation.colorVehicles(numberOfVehicles)

    """Di seguito inizializzo gli incroci che fanno parte della simulazione"""

    junctions = [FourWayJunction(n, vehicles, cellsPerSide=cellsPerSide, matrixTrajectories=matrixTrajectories,
                                 securitySecs=securitySecs) for n in range(1, 26)]

    junctionsList = [junction for junction in junctions if junction.nID in central_junctions_ids]

    array_vehicles = simulation.costructArray(array_vehicles)

    """Di seguito il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    n_step = 0

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        totalTime += step_incr
        traci.simulationStep(totalTime)
        n_step += 1
        departed += traci.simulation.getDepartedNumber()
        departed_vehicles += traci.simulation.getDepartedIDList()

        vehicles = simulation.checkRoute(vehicles, numberOfVehicles)

        for junction in junctionsList:  # scorro la lista degli incroci
            iM = junction.intersectionManager

            for vehicle in array_vehicles:  # scorro l'array delle auto ancora presenti nella simulazione

                vehicle_in_list = True
                # vedo se l'auto corrente è tra le auto segnate per attraversare l'incrocio
                try:
                    present = int(iM.arrivalList.index(vehicle))
                except ValueError:
                    vehicle_in_list = False

                pos = traci.vehicle.getPosition(vehicle)
                # se l'auto non è in lista allora guardo se sta entrando nelle vicinanze dell'incrocio
                if not vehicle_in_list:

                    if (iM.stop[3] - 50 <= pos[0] <= iM.stop[1] + 50) and \
                            (iM.stop[2] - 50 <= pos[1] <= iM.stop[0] + 50):
                        # inserisco l'auto nella lista d'arrivo di quell'incrocio
                        iM.arrivalList.append(vehicle)
                        # inserisco l'auto nella lista d'attesa di quell'incrocio
                        iM.waitingList.append(vehicle)
                        traci.vehicle.setMaxSpeed(vehicle, 6.944444)

                # se l'auto è in attesa e non è ferma, guardo se è vicina allo stop e fermo se l'incrocio è già occupato
                if vehicle in iM.waitingList and vehicle not in iM.stoppedList:
                    # se l'incrocio ha 4 lati
                    if len(iM.stop) > 3:
                        if (iM.stop[3] - 13.5 <= pos[0] <= iM.stop[1] + 13.5) and \
                                (iM.stop[2] - 13.5 <= pos[1] <= iM.stop[0] + 13.5):
                            traci.vehicle.setDecel(vehicle, 1.92901)
                            traci.vehicle.setAccel(vehicle, 1.92901)
                            # salvo l'auto leader di quella lane
                            leader = traci.vehicle.getLeader(vehicle)
                            if leader:
                                # se il leader ha già iniziato ad attraversare l'incrocio non lo conto
                                if leader[0] not in iM.waitingList:
                                    leader = None
                            # se non c'è il leader su quella lane
                            if not leader:
                                # controllo se l'auto non ha subito rallentamenti e la fermo in 16 m
                                if round(traci.vehicle.getSpeed(vehicle), 2) == \
                                        round(traci.vehicle.getMaxSpeed(vehicle), 2):
                                    iM.arrivalVehicle(vehicles[vehicle])
                                # se l'auto ha subito rallentamenti calcolo dalla sua velocità in quanti metri
                                # dall'incrocio si fermerebbe se la facessi rallentare subito, se si va a fermare in
                                # prossimità dell'incrocio allora avvio l'arresto del veicolo altrimenti aspetto
                                # il prossimo step e ricontrollo
                                else:
                                    dist_stop = 0
                                    s_auto = traci.vehicle.getSpeed(vehicle)
                                    decel = traci.vehicle.getDecel(vehicle)

                                    ang = traci.vehicle.getAngle(vehicle)

                                    if ang == 90:
                                        dist_stop = abs(iM.stop[3] - pos[0])
                                    if ang == 0:
                                        dist_stop = abs(iM.stop[2] - pos[1])
                                    if ang == 270:
                                        dist_stop = abs(iM.stop[1] - pos[0])
                                    if ang == 180:
                                        dist_stop = abs(iM.stop[0] - pos[1])

                                    dist_to_stop = (s_auto * s_auto) / (2 * decel)

                                    if dist_to_stop + 2 >= dist_stop:
                                        iM.arrivalVehicle(vehicles[vehicle])
            # se ci sono auto che stanno attraversando l'incrocio guardo se la situazione dell'incrocio è cambiata
            if iM.passageList is not None:

                # se l'auto è appena entrata nell'area dell'incrocio salvo la cella in cui si trova
                for x in iM.cellPassage:
                    route = traci.vehicle.getRouteID(x[0])
                    edges = traci.route.getEdges(route)
                    lane = iM.getLaneIndexFromEdges(edges, vehicles[x[0]])
                    if lane != 0:
                        # se l'auto non gira a destra
                        if x[1] is None and x[2] is None:
                            pos = traci.vehicle.getPosition(x[0])
                            if iM.inCrossing(pos):
                                vect_id = iM.cellPassage.index(x)
                                iM.cellPassage[vect_id] = iM.getCellFromPosVehicle(x[0])

                iM.freePath(vehicles)
                # se ci sono auto ferme, vedo se posso farne partire qualcuna
                if len(iM.stoppedList) > 0:

                    # scorro tra tutte le auto ferme e se una è compatibile con la matrice allora la faccio partire
                    for stopped_vehicle in iM.stoppedList:
                        if stopped_vehicle in iM.stoppedList:
                            if iM.getFromCrossingMatrix(vehicles[stopped_vehicle]):
                                # vedo se il suo percorso è libero e nel caso la faccio partire
                                iM.forwardVehicle(vehicles[stopped_vehicle])
            # riaccelero i veicoli all'uscita dall'incrocio
            if int(totalTime / step_incr) % 10 == 0:
                for exit_vehicle in iM.precPassage:
                    if exit_vehicle not in iM.passageList:
                        traci.vehicle.setMaxSpeed(exit_vehicle[0], 13.888888)
                        traci.vehicle.setSpeed(exit_vehicle[0], 13.888888)
                        traci.vehicle.setSpeedMode(exit_vehicle[0], 7)
                iM.precPassage = iM.passageList[:]
            # ogni 5 step pulisco la matrice da valori troppo vecchi
            if int(totalTime / step_incr) % 5 == 0:
                iM.cleanMatrix()

        # inserisco nell'array le auto presenti nella simulazione
        array_vehicles = simulation.costructArray(array_vehicles)

        if n_step % sec == 0:
            vehicles, junctions = simulation.checkVehicles(vehicles, departed_vehicles, junctions, int(n_step / sec),
                                                           schema)

    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, \
    stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, meanTails, \
    stDevTails, maxTails, meanThroughput = simulation.saveResults(vehicles, departed, junctions)

    traci.close()

    redirect_output(path, index, False)

    queue.put([meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime,
               stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, meanTails,
               stDevTails, maxTails, meanThroughput])
