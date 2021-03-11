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
    totalTime = 0  # tempo totale di simulazione

    simulation = Simulation()

    """Inizializzo i veicoli assegnadogli una route generata casualmente e, in caso di schema di colori 
    non significativo, dandogli un colore diverso per distinguerli meglio all'interno della simulazione"""

    vehicles = simulation.generateVehicles(stepsSpawn, numberOfVehicles, vehicles, routeMode, instantPay, seed)

    if schema in ['n', 'N']:
        simulation.colorVehicles(numberOfVehicles)

    """Di seguito inizializzo gli incroci che fanno parte della simulazione"""

    junctions = [FourWayJunction(n, vehicles) for n in range(1, 26)]

    """Di seguito il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        totalTime += 1
        traci.simulationStep()
        departed += traci.simulation.getDepartedNumber()
        departed_vehicles += traci.simulation.getDepartedIDList()

        vehicles = simulation.checkRoute(vehicles, numberOfVehicles)

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
