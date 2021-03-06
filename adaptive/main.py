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


def noMoreVehiclesToStop(vehicles_to_stop):
    check = [k for k in vehicles_to_stop if vehicles_to_stop[k][0] == ""]
    if not check:
        return True
    return False

def getVehiclesInNet(vehicles):
    return {k:v for (k,v) in vehicles.items() if k in traci.vehicle.getIDList()}

def getVehiclesNotCrossed(vehicles):
    vehs_in_net = getVehiclesInNet(vehicles)
    return {k: v for (k,v) in vehs_in_net.items() if traci.vehicle.getLaneID(k)[0:3] != f":n{junction_id}" and traci.vehicle.getLaneID(k)[1:3] != f"0{junction_id}"}

def getVehiclesWithHigherDistanceFromEndLaneThan(vehicles, m):
    return {k:v for (k,v) in vehicles.items() if v.distanceFromEndLane() > m}

def noVehiclesWithLesserDistanceFromEndLaneThan(vehicles, m):
    if not {k:v for (k,v) in vehicles.items() if v.distanceFromEndLane() < m}:
        return True
    return False

def getEnteringLanes():
    return [l for l in lanes if l[1:3] != f"0{junction_id}"]

def stopVehicle(obj, m=0):
    """Funzione che blocca il veicolo a una certa distanza (metri) dalla fine della corsia in cui si trova"""

    stopLane = traci.vehicle.getLaneID(obj.getID())
    pos = traci.lane.getLength(stopLane) - m
    try:
        traci.vehicle.setStop(obj.getID(), stopLane[:-2], laneIndex=int(stopLane[-1]),
                              pos=pos)
    except traci.exceptions.TraCIException as e:
        # print(f"ERROR: {e}")
        return False
    obj.isOnAStop = True
    return False


def restartVehicle(obj, m=0):
    """Funzione che sblocca il veicolo nel caso in cui questo fosse bloccato."""
    try:
        if obj.isStopped():
            stopLane = traci.vehicle.getLaneID(obj.getID())
            pos = traci.lane.getLength(stopLane) - m
            traci.vehicle.setStop(obj.getID(), stopLane[:-2], laneIndex=int(stopLane[-1]),
                                  pos=pos, duration=0)
            obj.isOnAStop = False
    except:
        return False
    return True

def tryStop(obj, tryButDontStop=False, m=0):
    """Funzione che prova a fermare un veicolo e, se ci riesce, restituisce True (fermandolo), altrimenti
    restituisce False.
    :param tryButDontStop: parametro booleano che, se diverso da False, si limita a provare a stoppare il
                     veicolo senza applicare effettivamente lo stop."""
    try:
        # provo a fermare il veicolo
        if tryButDontStop:
            # controllo che il veicolo non sia già fermo, altrimenti lo sbloccherei, se è già fermo posso restituire
            # True, essendo il veicolo già fermo o in frenata
            if not obj.isStopped():
                stopLane = traci.vehicle.getLaneID(obj.getID())
                pos = traci.lane.getLength(stopLane) - m
                traci.vehicle.setStop(obj.getID(), stopLane[:-2], laneIndex=int(stopLane[-1]),
                                      pos=pos, duration=0)
        else:
            # tentativo riuscito
            stopVehicle(obj, m)
        return True
    except:
        # tentativo fallito
        return False

def isStoppable(obj, m=0):
    """Funzione che controlla se un veicolo è fermabile in un certo momento. ATTENZIONE, il veicolo potrebbe
    comunque non essere fermabile in momenti successivi."""
    return tryStop(obj, tryButDontStop=True, m=m)


def updateStopVehicles(vehicles, vehs_to_stop, m=0):
    """Funzione che permette di settare uno stop a distanza m su ciascun veicolo per garantire che tutti gli approcci
    possano funzionare correttamente. Quando non ci sono piu veicoli nella junction i veicoli fermi vengono fatti ripartire"""
    #prendo solo i veicoli che non hanno passato l incrocio, per ogni lane identifico il veicolo in testa in base alla distanza e setto lo stop
    vehs_not_crossed = getVehiclesNotCrossed(vehicles)
    vehs_eligible_to_be_stopped = getVehiclesWithHigherDistanceFromEndLaneThan(vehs_not_crossed, 51)
    entering_lanes = getEnteringLanes()

    # prendo per ogni lane il veicolo piu prossimo agli m metri dall incrocio
    for (k,v) in vehs_eligible_to_be_stopped.items():
        stopLane = traci.vehicle.getLaneID(v.getID())
        control = vehs_to_stop[stopLane]
        distance_from_pos = v.distanceFromEndLane() - m
        if control[0] == "" and isStoppable(v, m):

            vehs_to_stop[stopLane] = (v, distance_from_pos)

    for (l, tup) in vehs_to_stop.items():

        if tup[0] != "":
            if not tup[0].isOnAStop:
                stopVehicle(tup[0], m)

    return vehs_to_stop

def stopVehicles(vehicles, m=0):
    """Funzione che permette di settare uno stop a distanza m su ciascun veicolo per garantire che tutti gli approcci
    possano funzionare correttamente. Quando non ci sono piu veicoli nella junction i veicoli fermi vengono fatti ripartire"""
    #prendo solo i veicoli che non hanno passato l incrocio, per ogni lane identifico il veicolo in testa in base alla distanza e setto lo stop
    vehs_not_crossed = getVehiclesNotCrossed(vehicles)
    vehs_eligible_to_be_stopped = getVehiclesWithHigherDistanceFromEndLaneThan(vehs_not_crossed, 51)
    entering_lanes = getEnteringLanes()
    vehs_to_stop = {k: ("", -1) for k in entering_lanes}

    # prendo per ogni lane il veicolo piu prossimo agli m metri dall incrocio
    for (k,v) in vehs_eligible_to_be_stopped.items():
        stopLane = traci.vehicle.getLaneID(v.getID())
        control = vehs_to_stop[stopLane]
        distance_from_pos = v.distanceFromEndLane() - m
        if (control[0] == "" or distance_from_pos < control[1]) and isStoppable(v, m):
            vehs_to_stop[stopLane] = (v, distance_from_pos)

    for (l, tup) in vehs_to_stop.items():
        if tup[0] != "":
            stopVehicle(tup[0], m)

    return vehs_to_stop

def restartVehicles(vehicles_to_restart_per_lane, m=0):
    for (l, tup) in vehicles_to_restart_per_lane.items():
        if tup[0] != "":
            restartVehicle(tup[0], m)

def noVehiclesInJunction(vehicles):
    vehs_in_net = [veh for veh in vehicles if veh in traci.vehicle.getIDList()]
    if not vehs_in_net:
        return True
    if not [veh for veh in vehs_in_net if traci.vehicle.getLaneID(veh)[0:3] == f":n{junction_id}"]:
        return True
    return False

def noVehiclesAtUnsafeDistance(vehicles, m):
    vehs_not_crossed = getVehiclesNotCrossed(vehicles)
    if noVehiclesInJunction(vehicles) and noVehiclesWithLesserDistanceFromEndLaneThan(vehs_not_crossed, m):
        return True
    return False


def isTransitioning(old, new):
    if old == new:
        return False
    return True

def adaptiveSimulation(numberOfVehicles, schema, sumoCmd, path, index, queue, seed, celle_per_lato, traiettorie_matrice, secondi_di_sicurezza, simulationMode, instantPay, dimensionOfGroups, train):
    """ Param1: Array of number of vehicles to be spawned for each main step
        Param2: Array of projects names to be used on each main step
        NON considero precedence with auction per il momento
    """
    main_step = 0
    main_step_old = main_step
    transitioning = "false"

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
    vehicles = generateVehicles(stepsSpawn, numberOfVehicles, vehicles, seed, junction_id, node_ids, allowLaneChange=False)

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
    m = 55
    # ////////////////////////////FOR LOOP RESPECTIVE SIM//////////////////////////////////////////
    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        # if main step

        """Lancio il progetto giusto per ogni step"""
        if transitioning == "false":
            project = train[str(main_step)]
        print(f"step: {totalTime}, main_step: {main_step}, project: {project}\n")
        #if mainStep(totalTime, stepsSpawn, numberOfVehicles) and main_step < len(numberOfVehicles):
        if transitioning == "true":
            vehs = stopVehicles(vehicles, m)
            transitioning = "waiting"
        if transitioning == "waiting":
            if not noMoreVehiclesToStop(vehs):
                vehs = updateStopVehicles(vehicles, vehs, m)
            if noVehiclesAtUnsafeDistance(vehicles, m):
                restartVehicles(vehs, m)
                transitioning = "false"



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
        if isTransitioning(main_step_old, main_step):
            transitioning = "true"
            main_step_old = main_step



    # ////////////////////////////FOR LOOP RESPECTIVE SIM//////////////////////////////////////////

    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime, \
    meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput = saveResults(vehicles, departed,
                                                                                                   tails_per_lane)

    traci.close()

    redirect_output(path, index, False)

    queue.put([int(totalTime), meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime,
               meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput, mean_th_per_num])