from utils import *
from config import *
from inpout import redirect_output

import traci
from sumolib import miscutils


def intermediateRun(numberOfVehicles, schema, totalTime, departed, intermediate_departed, vehicles, tails_per_lane, main_step, mean_th_per_num, step_incr, n_step, sec, arrayAuto, m, steps_per_main_step):

    #if n_step % sec == 0:
    vehicles, tails_per_lane = checkVehicles(vehicles, tails_per_lane, int(n_step / sec), schema)

    # NECESSARIO PER GARANTIRE COERENZA CON LE STRUTTURE DATI DELLA RESERVATION
    arrayAuto = updateReservationArray(arrayAuto)

    return mean_th_per_num, main_step, intermediate_departed, totalTime, departed, tails_per_lane, n_step, arrayAuto

def run(numberOfVehicles, schema, sumoCmd, path, index, queue, seed):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    redirect_output(path, index, True)

    traci.start(sumoCmd, port=port, numRetries=100)

    vehicles = {}  # dizionario contente gli id dei veicoli
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
    non significativo, dandogli un colore diverso per distinguerli meglio all'interno della simulazione"""

    vehicles = generateVehicles(stepsSpawn, numberOfVehicles, vehicles, seed, junction_id, node_ids)

    if schema in ['n', 'N']:
        colorVehicles(numberOfVehicles)

    """Di seguito il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        traci.simulationStep()
        totalTime += 1
        departed += traci.simulation.getDepartedNumber()
        intermediate_departed += traci.simulation.getDepartedNumber()

        vehicles, tails_per_lane = checkVehicles(vehicles, tails_per_lane, totalTime, schema)


        """
        #Salvo i risultati intermedi se si conclude un main step
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
