from utils import *
from config import *
from inpout import redirect_output

from precedence_with_coop_auction.trafficElements.junction import FourWayJunction

import traci
from sumolib import miscutils

def intermediateRun(numberOfVehicles, totalTime, step_incr, n_step, departed, junction, vehicles, tails_per_lane,
                    sec, schema, main_step, mean_th_per_num, arrayAuto, m, steps_per_main_step, main_step_duration):


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

    vehicles, tails_per_lane = checkVehiclesAdaptive(vehicles, tails_per_lane, int(totalTime), schema, main_step_duration)


    # NECESSARIO PER GARANTIRE COERENZA CON LE STRUTTURE DATI DELLA RESERVATION
    arrayAuto = updateReservationArray(arrayAuto)
    return totalTime, n_step, departed, junction, vehicles, tails_per_lane, main_step, \
           mean_th_per_num, arrayAuto


def run(numberOfVehicles, schema, sumoCmd, path, index, queue, seed, simulationMode, instantPay, dimensionOfGroups):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    redirect_output(path, index, True)

    traci.start(sumoCmd, port=port, numRetries=100)

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    departed = 0  # numero di veicoli partiti nella simulazione e considerati nel calcolo delle misure
    totalTime = 0  # tempo totale di simulazione
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

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:

        totalTime += 1
        traci.simulationStep(totalTime)
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
                    # se non è gia in una auction, non è stoppato
                    if objVeh.distanceFromEndLane() < 25:
                        traci.vehicle.setSpeed(idVeh, 6.945)
                        if objVeh in crossingManager.getCrossingStatus().values() and objVeh not in \
                                crossingManager.getVehiclesInAuction() and objVeh.checkPosition(junction) \
                                and objVeh not in crossingManager.nonStoppedVehicles:
                            junction.createAuction(objVeh, vehicles)
                else:
                    traci.vehicle.setSpeed(idVeh, 13.89)

        if len(vehAtJunction) > 0:
            crossingManager.allowCrossing()


        vehicles, tails_per_lane = checkVehicles(vehicles, tails_per_lane, totalTime, schema)

        """
        Salvo i risultati intermedi se si conclude un main step
        mean_th_per_num, main_step, intermediate_departed = checkIfMainStep(totalTime, stepsSpawn, numberOfVehicles,
                                                                            main_step, vehicles,
                                                                            intermediate_departed, mean_th_per_num)
        
        """





    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime, \
    meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput = saveResults(vehicles, departed,
                                                                                                   tails_per_lane)

    traci.close()

    redirect_output(path, index, False)

    queue.put([totalTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime,
               meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput, mean_th_per_num])
