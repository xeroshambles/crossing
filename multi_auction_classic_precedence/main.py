from inpout_multi import redirect_output

from trafficElements_multi.junction import FourWayJunction
from trafficElements_multi.simulation import *

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
    arrived_vehicles = []  # lista dei veicoli che hanno lasciato la simulazione
    totalTime = 0  # tempo totale di simulazione

    simulation = Simulation()

    """Inizializzo i veicoli assegnadogli una route generata casualmente e, in caso di schema di colori 
    non significativo, dandogli un colore diverso per distinguerli meglio all'interno della simulazione"""

    simulation.generateVehicles(stepsSpawn, numberOfVehicles, vehicles, instantPay, seed)

    if schema in ['n', 'N']:
        simulation.colorVehicles(numberOfVehicles)

    """Inizializzo gli incroci che fanno parte della simulazione"""

    junctions = [FourWayJunction(n, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                                 groupDimension=dimensionOfGroups) for n in range(1, 26)]

    """Apro il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        totalTime += 1
        traci.simulationStep()
        departed += traci.simulation.getDepartedNumber()
        departed_vehicles += traci.simulation.getDepartedIDList()
        arrived_vehicles += traci.simulation.getArrivedIDList()

        vehicles, departed_vehicles = simulation.checkRoute(vehicles, departed_vehicles, arrived_vehicles,
                                                            numberOfVehicles)

        """Ciclo principale dell'applicazione"""

        """Prime operazioni sugli incroci"""

        for junction in junctions:

            if junction.nID in central_junctions_ids:

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
                            # se non è gia in una auction, non è stoppato
                            if objVeh.distanceFromEndLane() < 15:
                                if objVeh in crossingManager.getCrossingStatus().values() and objVeh not in \
                                        crossingManager.getVehiclesInAuction() and objVeh.checkPosition(junction) \
                                        and objVeh not in crossingManager.nonStoppedVehicles:
                                    junction.createAuction(objVeh, vehicles)

                if len(vehAtJunction) > 0:
                    crossingManager.allowCrossing()

        vehicles, junctions = simulation.checkVehicles(vehicles, departed_vehicles, junctions, totalTime, schema)

    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, \
    stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, meanTails, \
    stDevTails, maxTails, meanThroughput = simulation.saveResults(vehicles, departed, junctions)

    traci.close()

    redirect_output(path, index, False)

    queue.put([meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime,
               stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, meanTails,
               stDevTails, maxTails, meanThroughput])
