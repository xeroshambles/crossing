from utils_multi import *
from inpout_multi import redirect_output

import traci
from sumolib import miscutils


def run(numberOfSteps, numberOfVehicles, schema, sumoCmd, path, index, queue, seed):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    redirect_output(path, index, True)

    traci.start(sumoCmd, port=port, numRetries=1000)

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    departed = 0  # numero di veicoli partiti entro la fine della simulazione
    departed_vehicles = []  # lista dei veicoli partiti entro la fine della simulazione
    totalTime = 0  # tempo totale di simulazione

    """Con il seguente ciclo inizializzo i veicoli assegnadogli una route legale generata casualmente e, in caso di 
    schema di colori non significativo,dandogli un colore diverso per distinguerli meglio all'interno della 
    simulazione"""

    generateVehicles(stepsSpawn, numberOfVehicles, vehicles, routeMode, instantPay, seed)

    if schema in ['n', 'N']:
        colorVehicles(numberOfVehicles)

    """Di seguito inizializzo gli incroci che fanno parte della simulazione"""

    junctions, two_way_junctions = createJunctions(vehicles)

    """Di seguito il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        traci.simulationStep()
        totalTime += 1
        departed += traci.simulation.getDepartedNumber()
        departed_vehicles += traci.simulation.getDepartedIDList()

        vehicles = checkRoute(vehicles, numberOfVehicles)

        """Ciclo principale dell'applicazione"""

        """Prime operazioni sugli incroci"""

        for junction in junctions:

            if junction.nID in four_way_junctions_ids:

                vehAtJunction = junction.getVehiclesAtJunction()
                crossingManager = junction.getCrossingManager()
                crossingManager.updateCrossingStatus(vehicles)

                """Flusso principale"""

                for idVeh in vehAtJunction:
                    if idVeh in vehicles:
                        objVeh = vehicles[idVeh]

                        if objVeh.distanceFromEndLane() < 50:
                            if objVeh not in crossingManager.getCurrentPartecipants():
                                crossingManager.updateVehicleStatus(objVeh)
                            # se non è gia in una auction, non e stoppato
                            if objVeh.distanceFromEndLane() < 25:
                                if objVeh in crossingManager.getCrossingStatus().values() and objVeh not in \
                                        crossingManager.getVehiclesInAuction() and objVeh.checkPosition(junction) \
                                        and objVeh not in crossingManager.nonStoppedVehicles:
                                    junction.createAuction(objVeh, vehicles)

                if len(vehAtJunction) > 0:
                    crossingManager.allowCrossing()

        vehicles, junctions, two_way_junctions = checkVehicles(vehicles, departed_vehicles, junctions,
                                                               two_way_junctions, totalTime, schema)

    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, \
    stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, meanTails, \
    stDevTails, maxTails, meanThroughput = saveResults(vehicles, departed, junctions)

    traci.close()

    redirect_output(path, index, False)

    queue.put([meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime,
               stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, meanTails,
               stDevTails, maxTails, meanThroughput])
