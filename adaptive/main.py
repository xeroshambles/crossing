from utils import *
from config import *
from inpout import redirect_output
from reservation.main import stopXY, limiti_celle, costruzioneArray
from classic_tls.main import intermediateRun as tlsRun
from classic_precedence.main import intermediateRun as precedenceRun
from precedence_with_auction.main import intermediateRun as precedenceWithAuctionRun
from reservation.main import intermediateRun as reservationRun
from precedence_with_auction.trafficElements.junction import FourWayJunction
import traci
from sumolib import miscutils

def noVehiclesInJunction(vehicles):
    vehs_in_net = [veh for veh in vehicles if veh in traci.vehicle.getIDList()]
    if not vehs_in_net:
        return True
    if not [veh for veh in vehs_in_net if traci.vehicle.getLaneID(veh)[0:3] == f":n{junction_id}"]:
        return True
    return False

def adaptiveSimulation(numberOfVehicles, schema, sumoCmd, path, index, queue, seed, celle_per_lato, traiettorie_matrice, secondi_di_sicurezza, simulationMode, instantPay, dimensionOfGroups, train):
    """ Param1: Array of number of vehicles to be spawned for each main step
        Param2: Array of projects names to be used on each main step
        NON considero precedence with auction per il momento
    """

    main_step = 0
    port = miscutils.getFreeSocketPort()

    redirect_output(path, index, True)

    traci.start(sumoCmd, port=port, numRetries=100)

    vehicles = {}  # dizionario contente gli id dei veicoli
    departed = 0  # numero di veicoli partiti nella simulazione e considerati nel calcolo delle misure
    totalTime = 0  # tempo totale di simulazione
    tails_per_lane = {}  # dizionario contenente le lunghezze delle code per ogni lane ad ogni step

    mean_th_per_num = [-1 for el in numberOfVehicles]

    intermediate_departed = 0

    for lane in lanes:
        # calcolo la lunghezza delle code e il throughput solo per le lane entranti
        if lane[4:6] == '07':
            tails_per_lane[lane] = []

    """Inizializzo i veicoli assegnadogli una route generata casualmente e, in caso di schema di colori 
    non significativo, dandogli un colore diverso per distinguerli meglio all'interno della simulazione"""

    """ATTENZIONE: OCCORRE FARLA ANCHE PER PRECEDENCE WITH AUCTION"""
    vehicles = generateVehicles(stepsSpawn, numberOfVehicles, vehicles, seed, junction_id, node_ids)

    if schema in ['n', 'N']:
        colorVehicles(numberOfVehicles)



    #params di precedence_with_auction

    """Di seguito inizializzo l'incrocio che fa parte della simulazione, assegnandogli una classe che ne descriva
        il comportamento specifico"""

    junction = FourWayJunction(junction_id, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                               groupDimension=dimensionOfGroups)
    #params di reservation
    step_incr = 0.050  # incremento di step della simulazione
    sec = 1 / step_incr  # numero che indica ogni quanti sotto step devo calcolare le misure
    # istanzio le matrici [nome_incrocio, variabile]
    attesa = []  # ordine di arrivo su lista, si resetta quando le auto liberano incrocio
    passaggio = []  # auto in passaggio nell'incrocio
    lista_arrivo = []  # auto entrate nelle vicinanze dell'incrocio, non si resetta
    matrice_incrocio = []  # rappresenta la suddivisione matriciale dell'incrocio (in celle)
    lista_uscita = []  # auto uscite dall'incrocio, non si resetta
    ferme = []  # lista di auto ferme allo stop
    stop = []  # lista che indica le coordinate degli stop dal centro dell'incrocio [destra, sotto, sinistra,
    # sopra]
    centerJunctID = []  # coordinate (x,y) del centro di un incrocio
    arrayAuto = []  # contiene la lista di auto presenti nella simulazione
    limiti_celle_X = []  # utile per verificare l'appartenenza ad una cella all'interno della matrice dell'incrocio
    limiti_celle_Y = []  # utile per verificare l'appartenenza ad una cella all'interno della matrice dell'incrocio
    passaggio_cella = []  # salvo in che cella si trova l'auto in passaggio [incrID][ [ auto , cella_X , cella_Y ],... ]
    rallentate = []  # lista di auto rallentate in prossimità dell'incrocio
    passaggio_precedente = []  # salvo l'ultima situazione di auto in passaggio per rilasciarle all'uscita

    attesa.append([])
    lista_arrivo.append([])
    lista_uscita.append([])
    ferme.append([])
    passaggio.append([])
    rallentate.append([])
    passaggio_cella.append([])
    passaggio_precedente.append([])

    centerJunctID.append(traci.junction.getPosition('n' + str(junction_id)))  # posizione del centro dell'incrocio

    shape = traci.junction.getShape('n' + str(junction_id))  # forma dell'incrocio
    stop.append(stopXY(shape))  # estremi dell'incrocio, dove sono presenti gli stop

    # popolo i vettori limiti_celle_X e limiti_celle_Y
    limiti = limiti_celle(stopXY(shape), celle_per_lato)  # calcolo i limiti delle celle
    limiti_celle_X.append(limiti[0])
    limiti_celle_Y.append(limiti[1])
    # popolo la matrice dell'incrocio
    matrice_incrocio.append([])
    for x in range(0, celle_per_lato):
        matrice_incrocio[0].append([])
        for y in range(0, celle_per_lato):
            # ogni cella è un'array dei tempi stimati di occupazione della medesima
            matrice_incrocio[0][x].append([])
    # inserisco nell'array le auto presenti nella simulazione
    arrayAuto = costruzioneArray(arrayAuto)

    # trovo lunghezza e altezza auto in celle
    x_cella_in_m = abs(limiti_celle_X[0][1] - limiti_celle_X[0][0])
    y_cella_in_m = abs(limiti_celle_Y[0][1] - limiti_celle_Y[0][0])
    x_auto_in_m = traci.vehicle.getHeight("idV0")
    y_auto_in_m = traci.vehicle.getLength("idV0")
    x_auto_in_celle = float(x_auto_in_m) / float(x_cella_in_m)
    y_auto_in_celle = float(y_auto_in_m) / float(y_cella_in_m)
    # fino a quando tutte le auto da inserire hanno terminato la corsa

    n_step = 0
    incrID = 0

    # ////////////////////////////FOR LOOP RESPECTIVE SIM//////////////////////////////////////////
    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        # if main step
        """Lancio il progetto giusto per ogni step"""
        if mainStep(totalTime, stepsSpawn, numberOfVehicles) and main_step < len(numberOfVehicles):
            project = train[str(main_step)]
        print(f"step: {totalTime}, main_step: {main_step}, project: {project}\n")

        #if mainStep(totalTime, stepsSpawn, numberOfVehicles):
            #traci.trafficlight.setProgram("n7", "all_red") #all red
            #if project == "reservation":
                #arrayAuto = costruzioneArray(arrayAuto)

        '''
        if project == "classic_tls":
            #if noVehiclesInJunction(vehicles):
                #if totalTime != 0 and noVehiclesInJunction(vehicles):
                #resetProject(vehicles)
                #traci.trafficlight.setProgram("n7", "tls") # tls
            mean_th_per_num, main_step, intermediate_departed, totalTime, departed, tails_per_lane, n_step = tlsRun(numberOfVehicles,
                                                                                                                    schema, totalTime,
                                                                                                                    departed, intermediate_departed,
                                                                                                                    vehicles, tails_per_lane, main_step,
                                                                                                                    mean_th_per_num, step_incr, n_step, sec)
        '''
        if project == "classic_precedence":
            #if noVehiclesInJunction(vehicles):
                #if totalTime != 0 and noVehiclesInJunction(vehicles):
                #resetProject(vehicles)
                #traci.trafficlight.setProgram("n7", "all_green")

            mean_th_per_num, main_step, intermediate_departed, totalTime, departed, tails_per_lane, n_step = precedenceRun(numberOfVehicles,
                                                                                                                    schema, totalTime,
                                                                                                                    departed, intermediate_departed,
                                                                                                                    vehicles, tails_per_lane, main_step,
                                                                                                                    mean_th_per_num, step_incr, n_step, sec)
        if project == "precedence_with_auction":
            totalTime, n_step, departed, intermediate_departed, junction, vehicles, tails_per_lane, main_step, \
            mean_th_per_num = precedenceWithAuctionRun(numberOfVehicles, totalTime, step_incr, n_step, departed, intermediate_departed, junction, vehicles, tails_per_lane,
                    sec, schema, main_step, mean_th_per_num)

        if project == "reservation":
            #if noVehiclesInJunction(vehicles):
                #if totalTime != 0 and noVehiclesInJunction(vehicles):
                #resetProject(vehicles)


                #traci.trafficlight.setProgram("n7", "all_green")

            mean_th_per_num, main_step, intermediate_departed, totalTime,\
            departed, tails_per_lane, arrayAuto, lista_arrivo, stop, attesa,\
            ferme, passaggio, matrice_incrocio, passaggio_cella, traiettorie_matrice,\
            x_auto_in_celle, y_auto_in_celle, passaggio_precedente, n_step = reservationRun(numberOfVehicles, schema,
                                                                                            totalTime, departed, intermediate_departed,
                                                                                            vehicles, tails_per_lane, main_step, mean_th_per_num, arrayAuto,
                                                                                            lista_arrivo, stop, attesa, ferme, passaggio, matrice_incrocio, passaggio_cella,
                                                                                            traiettorie_matrice, x_auto_in_celle, y_auto_in_celle, limiti_celle_X, limiti_celle_Y,
                                                                                            step_incr, passaggio_precedente, n_step, sec, incrID)




    # ////////////////////////////FOR LOOP RESPECTIVE SIM//////////////////////////////////////////

    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime, \
    meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput = saveResults(vehicles, departed,
                                                                                                   tails_per_lane)

    traci.close()

    redirect_output(path, index, False)

    queue.put([int(totalTime), meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime,
               meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput, mean_th_per_num])