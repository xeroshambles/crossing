from utils import *
from config import *
from inpout import redirect_output

from precedence_with_auction.trafficElements.junction import FourWayJunction

import traci
from sumolib import miscutils

def intermediateRun(numberOfVehicles, totalTime, step_incr, n_step, departed, intermediate_departed, junction, vehicles, tails_per_lane,
                    sec, schema, main_step, mean_th_per_num):
    traci.simulationStep()
    totalTime += step_incr
    n_step += 1
    departed += traci.simulation.getDepartedNumber()
    intermediate_departed += traci.simulation.getDepartedNumber()

    """Ciclo principale dell'applicazione"""

    """Prime operazioni sull'incrocio"""

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
                if objVeh.distanceFromEndLane() < 15:
                    if objVeh in crossingManager.getCrossingStatus().values() and objVeh not in \
                            crossingManager.getVehiclesInAuction() and objVeh.checkPosition(junction) \
                            and objVeh not in crossingManager.nonStoppedVehicles:
                        junction.createAuction(objVeh, vehicles)

    if len(vehAtJunction) > 0:
        crossingManager.allowCrossing()

    if n_step % sec == 0:
        vehicles, tails_per_lane = checkVehicles(vehicles, tails_per_lane, int(n_step / sec), schema)

        """Salvo i risultati intermedi se si conclude un main step"""

        # step preliminare per rendere compatibili gli id dei veicoli con la funzione
        vehicles_temp = {k.replace("idV", ""): v for (k, v) in vehicles.items()}
        mean_th_per_num, main_step, intermediate_departed = checkIfMainStep(totalTime, stepsSpawn, numberOfVehicles,
                                                                            main_step, vehicles_temp,
                                                                            intermediate_departed, mean_th_per_num)

    return totalTime, n_step, departed, intermediate_departed, junction, vehicles, tails_per_lane, main_step, \
           mean_th_per_num


def run(numberOfVehicles, schema, sumoCmd, path, index, queue, seed, simulationMode, instantPay, dimensionOfGroups):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    redirect_output(path, index, True)

    traci.start(sumoCmd, port=port, numRetries=100)

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    departed = 0  # numero di veicoli partiti nella simulazione e considerati nel calcolo delle misure
    totalTime = 0.000  # tempo totale di simulazione
    step_incr = 0.250  # incremento di step della simulazione
    sec = 1 / step_incr  # numero che indica ogni quanti sotto step devo calcolare le misure
    tails_per_lane = {}  # dizionario contenente le lunghezze delle code per ogni lane ad ogni step

    mean_th_per_num = [-1 for el in numberOfVehicles]
    main_step = 0
    intermediate_departed = 0

    for lane in lanes:
        # calcolo la lunghezza delle code e il throughput solo per le lane entranti
        if lane[4:6] == '07':
            tails_per_lane[lane] = []

    """Inizializzo i veicoli assegnadogli una route generata casualmente e, in caso di schema di colori 
    non significativo,dandogli un colore diverso per distinguerli meglio all'interno della simulazione"""

    vehicles = generateVehicles(stepsSpawn, numberOfVehicles, vehicles, seed, junction_id, node_ids, True)

    if schema in ['n', 'N']:
        colorVehicles(numberOfVehicles)

    """Di seguito inizializzo l'incrocio che fa parte della simulazione, assegnandogli una classe che ne descriva
    il comportamento specifico"""

    junction = FourWayJunction(junction_id, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                               groupDimension=dimensionOfGroups)

    """Di seguito il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    n_step = 0

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        traci.simulationStep()
        totalTime += step_incr
        n_step += 1
        departed += traci.simulation.getDepartedNumber()
        intermediate_departed += traci.simulation.getDepartedNumber()

        """Ciclo principale dell'applicazione"""

        """Prime operazioni sull'incrocio"""

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
                    if objVeh.distanceFromEndLane() < 15:
                        if objVeh in crossingManager.getCrossingStatus().values() and objVeh not in \
                                crossingManager.getVehiclesInAuction() and objVeh.checkPosition(junction) \
                                and objVeh not in crossingManager.nonStoppedVehicles:
                            junction.createAuction(objVeh, vehicles)

        if len(vehAtJunction) > 0:
            crossingManager.allowCrossing()

        if n_step % sec == 0:
            vehicles, tails_per_lane = checkVehicles(vehicles, tails_per_lane, int(n_step / sec), schema)

            """Salvo i risultati intermedi se si conclude un main step"""

            # step preliminare per rendere compatibili gli id dei veicoli con la funzione
            vehicles_temp = {k.replace("idV", ""): v for (k, v) in vehicles.items()}
            mean_th_per_num, main_step, intermediate_departed = checkIfMainStep(totalTime, stepsSpawn, numberOfVehicles,
                                                                                main_step, vehicles_temp,
                                                                                intermediate_departed, mean_th_per_num)

    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime, \
    meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput = saveResults(vehicles, departed,
                                                                                                   tails_per_lane)

    traci.close()

    redirect_output(path, index, False)

    queue.put([totalTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime,
               meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput, mean_th_per_num])
