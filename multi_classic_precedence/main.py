from inpout_multi import redirectOutput

from traffic_elements_multi.junction import FourWayJunction
from traffic_elements_multi.simulation import *

import traci
from sumolib import miscutils


def run(numberOfSteps, numberOfVehicles, schema, sumoCmd, path, index, queue, seed):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    redirectOutput(path, index, True)

    traci.start(sumoCmd, port=port, numRetries=1000)

    print(f"Partito: {index}")

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    total_time = 0  # tempo totale di simulazione
    simulation_vehicles = []  # contiene la lista di auto presenti nella simulazione

    simulation = Simulation()

    """Inizializzo i veicoli assegnadogli una route generata casualmente e, in caso di schema di colori 
    non significativo, dandogli un colore diverso per distinguerli meglio all'interno della simulazione"""

    vehicles = simulation.generateVehicles(stepsSpawn, numberOfVehicles, vehicles, seed)

    if schema in ['n', 'N']:
        simulation.colorVehicles(numberOfVehicles)

    """Inizializzo gli incroci che fanno parte della simulazione"""

    junctions = [FourWayJunction(n, vehicles) for n in range(1, 26)]

    """Inizializzo le auto che fanno parte della simulazione"""

    simulation_vehicles = simulation.getSimulationVehicles(simulation_vehicles)

    """Apro il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    while traci.simulation.getMinExpectedNumber() > 0 and total_time < numberOfSteps:
        total_time += 1
        traci.simulationStep()

        simulation_vehicles = simulation.getSimulationVehicles(simulation_vehicles)

        vehicles = simulation.checkVehiclesRoute(vehicles, simulation_vehicles, numberOfVehicles)

        vehicles, junctions = simulation.checkVehiclesState(vehicles, simulation_vehicles, junctions, total_time,
                                                            schema)

    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, \
    stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, divertedVehicles, \
    meanTails, stDevTails, maxTails, meanThroughput = simulation.saveResults(vehicles, simulation_vehicles, junctions)

    traci.close()

    print(f"Terminato: {index}")

    redirectOutput(path, index, False)

    queue.put([meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime,
               stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp,
               divertedVehicles, meanTails, stDevTails, maxTails, meanThroughput])
