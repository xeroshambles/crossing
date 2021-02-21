from config import *
from utils import *
from multi_auction_classic_tls.trafficElements.junction import FourWayJunction
from multi_auction_classic_tls.trafficElements.vehicle import Vehicle

import traci
from sumolib import miscutils


def generateVehiclesMulti(numberOfSteps, numberOfVehicles, vehicles, routeMode, instantPay, seed):
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
        vehicles[idV] = Vehicle(idV, instantPay)
        base_route = vehicles[idV].generateRoute(static=routeMode)
        route = traci.simulation.findRoute(base_route[0], base_route[1])
        traci.route.add(f'route_{i}', route.edges)
        vehicles[idV].setEdgeObjective(base_route[1])
        traci.vehicle.add(idV, f'route_{i}', depart=depart)


def run(numberOfSteps, numberOfVehicles, schema, sumoCmd, seed):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    traci.start(sumoCmd, port=port, numRetries=100)

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    step = 0  # tempo totale di simulazione
    step_incr = 0.500  # incremento del numero di step della simulazione

    """Con il seguente ciclo inizializzo i veicoli assegnadogli una route legale generata casualmente e, in caso di 
    schema di colori non significativo,dandogli un colore diverso per distinguerli meglio all'interno della 
    simulazione"""

    generateVehiclesMulti(stepsSpawn, numberOfVehicles, vehicles, routeMode, instantPay, seed)

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
            # junctions.append(ThreeWayJunction(i, sM=simulationMode, bM=bufferMode))
            pass
        else:
            junctions.append(FourWayJunction(i, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                                             groupDimension=dimensionOfGroups))

    """Di seguito il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    while traci.simulation.getMinExpectedNumber() > 0 and step <= numberOfSteps:
        traci.simulationStep()
        step += step_incr

        # controllo se i veicoli hanno raggiunto l'obbiettivo e, nel caso, riassegno una nuova route
        for i in range(0, sum(numberOfVehicles)):
            vehicles[f'idV{i}'].changeTarget(staticRoutes=routeMode)

        for junction in junctions:

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
