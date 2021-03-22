import random
from math import sqrt
from config import *
from precedence_with_comp_auction.trafficElements.vehicle import Vehicle
from config_adaptive import *
import traci

def getVehiclesInNet(vehicles):
    return {k:v for (k, v) in vehicles.items() if v.getID() in traci.vehicle.getIDList()}

def getVehiclesNotCrossed(vehicles):
    vehs_in_net = getVehiclesInNet(vehicles)
    return {k:v for (k, v) in vehs_in_net.items() if traci.vehicle.getLaneID(v.getID())[0:3] != f":n{junction_id}" and traci.vehicle.getLaneID(v.getID())[1:3] != f"0{junction_id}"}

def cleanReservationArrays(arrayAuto_temp, lista_arrivo, vehicles, auto_per_lane_to_stop):

    """Funzione che consente di rimuovere da ArrayAuto tutte le auto che non dovranno piu essere trattate a causa del cambio di
    main_step(tutte quelle che si fermano prima dei 50 mt per consentire la pulizia dell incrocio oppure che sono dietro ad esse)"""
    for (l, tup) in auto_per_lane_to_stop.items():
        #devo rimuovere da arrayAuto_temp sia le auto che saranno fermate, sia tutte quelle dietro
        if tup[0] != "":
            if tup[0].getID() in arrayAuto_temp:
                arrayAuto_temp.pop(arrayAuto_temp.index(tup[0].getID()))
            if tup[0].getID() in lista_arrivo:
                lista_arrivo.pop(lista_arrivo.index(tup[0].getID()))
            # cleanup di tutti i veicoli che si trovano dietro al suddetto veicolo appena rimosso
            for v in arrayAuto_temp:
                if traci.vehicle.getLaneID(v) == traci.vehicle.getLaneID(tup[0].getID()):
                    if vehicles[v].distanceFromEndLane() > tup[0].distanceFromEndLane():
                        arrayAuto_temp.pop(arrayAuto_temp.index(v))
                        if v in lista_arrivo:
                            lista_arrivo.pop(lista_arrivo.index(v))

    return arrayAuto_temp, lista_arrivo

def updateReservationArray(arrayAuto_temp, clean=False):
    """Costruzione dell'array composto dal nome delle auto presenti nella simulazione"""

    loadedIDList = traci.simulation.getDepartedIDList()  # carica nell'array le auto partite
    for id_auto in loadedIDList:
        if id_auto not in arrayAuto_temp:
            arrayAuto_temp.append(id_auto)

    arrivedIDList = traci.simulation.getArrivedIDList()  # elimina nell'array le auto arrivate
    for id_auto in arrivedIDList:
        if id_auto in arrayAuto_temp:
            arrayAuto_temp.pop(arrayAuto_temp.index(id_auto))
    #if clean:
    #    arrayAuto_temp = cleanReservationArray(arrayAuto_temp)
    return arrayAuto_temp



def mainStep2(total_time, n_steps, n_vehs):

    r = round(total_time)

    mod = r % (n_steps / len(n_vehs))

    if mod == 0 and r <= n_steps and (round(total_time - r) == 0):
        return True
    else:
        return False

def mainStep(total_time, numberOfVehicles, simulation_time):


    #mod = n_steps % (steps_per_main_step )
    mod = total_time % (simulation_time / len(numberOfVehicles))
    if total_time != 0 and mod == 0 and total_time <= simulation_time:
        return True
    else:
        return False

def getVehiclesWithHigherDistanceFromEndLaneThan(vehicles, m=0):
    vehs_not_crossed = getVehiclesNotCrossed(getVehiclesInNet(vehicles))
    return {k:v for (k,v) in vehs_not_crossed.items() if v.distanceFromEndLane() > m}

def saveIntermediateResults(n_vehs, main_step, vehicles, departed, m=0, removed=None):

    passed = 0
    #floor = sum(n_vehs[0: main_step])
    #ceil = floor + n_vehs[main_step]
    #ids = {v.getID(): v for v in vehicles.values()}
    vehs_departed = {k:v for (k, v) in vehicles.items() if v.getID() in departed}
    vehs_departed_at_safe_distance = getVehiclesWithHigherDistanceFromEndLaneThan(vehs_departed, m)
    vehs_departed_not_at_safe_distance = {k: v for (k, v) in vehs_departed.items() if v not in vehs_departed_at_safe_distance.values()}
    #current_main_step_vehicles_to_consider = {k:v for (k,v) in vehs_departed_crossed.items() if floor <= int(v.getID()[3:]) < ceil}
    n = len(vehs_departed_not_at_safe_distance)
    for v in vehs_departed_not_at_safe_distance.values(): #current_main_step_vehicles_to_consider.values():
        #if v not in removed.values():
        #if int(num) <= departed:
        passed += v.hasPassed
    mean_th = passed / n #current_main_step_vehicles_to_consider)

    return mean_th, passed, n #current_main_step_vehicles_to_consider, vehs_not_crossed

def checkIfMainStep(total_time, steps_per_main_step, n_steps, spawn_duration, numberOfVehicles, main_step, vehicles, departed, mean_th_per_num, m=0):

    if total_time != 0 and mainStep(total_time, steps_per_main_step, n_steps, spawn_duration):
            mean_th_per_num[main_step] = saveIntermediateResults(numberOfVehicles, main_step, vehicles, departed, m)
            if main_step < (len(numberOfVehicles) - 1):
                main_step += 1
            departed = 0

    return mean_th_per_num, main_step, departed

def checkIfMainStep2(total_time, n_steps, n_vehs, step, vehicles, departed, mean_th_per_num):

    if mainStep(total_time, n_steps, n_vehs):
            mean_th_per_num[step] = saveIntermediateResults(n_vehs, step, vehicles, departed)
            if step < (len(n_vehs) - 1):
                step += 1
            departed = 0

    return mean_th_per_num, step, departed

def getLaneIndexFromEdges(start, end, node_ids):
    """Funzione che trova la lane corretta da far seguire al veicolo dati il nodo di partenza e quello di
    destinazione"""

    distance = -1
    i = 0
    trovato = False

    while True:
        if node_ids[i % 4] == start:
            trovato = True
        if trovato:
            distance += 1
            if node_ids[i % 4] == end:
                break
        i += 1

    lane = 0

    if distance == 1:
        lane = 2
    if distance == 2:
        lane = 1
    if distance == 3:
        lane = 0

    return lane


def getDistanceFromLaneEnd(spawn_distance, lane_length, shape):
    """Calcolo la distanza tra il veicolo e l'inizio dell'incrocio"""

    min_x = shape[0][0]
    max_x = shape[0][0]

    for point in shape:
        if point[0] < min_x:
            min_x = point[0]
        if point[0] > max_x:
            max_x = point[0]

    lane_end = lane_length - (max_x - min_x) / 2

    return lane_end - spawn_distance


def generateRoutes(junction_id, node_ids):
    """Genero tutte le route possibili per l'incrocio"""

    n = 0

    for i in node_ids:
        for j in node_ids:
            if i == j:
                continue
            start = i
            end = j
            traci.route.add(f'route_{n}', [f'e{"0" if start != 12 else ""}{start}_0{junction_id}',
                                           f'e0{junction_id}_{"0" if end != 12 else ""}{end}'])
            n += 1

    routes = traci.route.getIDList()
    routes_per_lane_start = {'0': [], '1': [], '2': []}

    for route in routes:
        edges = traci.route.getEdges(route)
        index = getLaneIndexFromEdges(int(edges[0][1:3]), int(edges[1][4:6]), node_ids)
        routes_per_lane_start[str(index)].append(route)

    return routes_per_lane_start


def generateLaneSequence(conf, numberOfVehicles, seed):
    """Genero la sequenza di lane equiprobabili"""
    px, py, pz = conf
    random.seed(seed)
    sequence = []

    for _ in range(0, numberOfVehicles):
        r = random.randint(1, 100)
        if r <= px:
            sequence.append(0)
        elif r <= (px + py):
            sequence.append(1)
        else:
            sequence.append(2)

    return sequence


def generateVehicles(numberOfSteps, numberOfVehicles, vehicles, seed, junction_id, node_ids, wallet=False, allowLaneChange=True):
    """Genero veicoli per ogni route possibile"""

    c = 0
    t = 0

    depart = 0
    auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]

    random.seed(seed)

    routes = generateRoutes(junction_id, node_ids)
    sequence = generateLaneSequence(spawn_balancing, sum(numberOfVehicles), seed)

    for i in range(0, sum(numberOfVehicles)):
        if t < numberOfVehicles[c]:
            t += 1
        else:
            t = 0
            c += 1
            auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]

        depart += auto_every
        idV = f'idV{i}'
        vehicles[idV] = Vehicle(idV, iP=instantPay)
        route = random.choice(routes[str(sequence[i])])
        edges = traci.route.getEdges(route)
        lane = getLaneIndexFromEdges(int(edges[0][1:3]), int(edges[1][4:6]), node_ids)
        traci.vehicle.add(idV, route, depart=depart, departLane=lane)
        if not allowLaneChange:
            traci.vehicle.setLaneChangeMode(idV, 512)
        if wallet:
            traci.vehicle.setParameter(idV, "wallet", str(50))


    return vehicles


def colorVehicles(numberOfVehicles):
    """Assegno un colore diverso alle auto"""

    for i in range(0, numberOfVehicles):
        if i % 8 == 1:
            traci.vehicle.setColor(f'{i}', (0, 255, 255))  # azzurro
        if i % 8 == 2:
            traci.vehicle.setColor(f'{i}', (160, 100, 100))  # rosa
        if i % 8 == 3:
            traci.vehicle.setColor(f'{i}', (255, 0, 0))  # rosso
        if i % 8 == 4:
            traci.vehicle.setColor(f'{i}', (0, 255, 0))  # verde
        if i % 8 == 5:
            traci.vehicle.setColor(f'{i}', (0, 0, 255))  # blu
        if i % 8 == 6:
            traci.vehicle.setColor(f'{i}', (255, 255, 255))  # bianco
        if i % 8 == 7:
            traci.vehicle.setColor(f'{i}', (255, 0, 255))  # viola
        if i % 8 == 8:
            traci.vehicle.setColor(f'{i}', (255, 100, 0))  # arancione

def checkVehiclesAdaptive(vehicles, tails_per_lane, time, schema, step_duration):
    """Funzione che controlla il posizionamento dei veicoli nell'incrocio e prende le misure"""
    time = int(time % step_duration)
    vehs_loaded = traci.vehicle.getIDList()
    junction_shape = traci.junction.getShape("n" + str(junction_id))

    for lane in tails_per_lane:
        tails_per_lane[lane].append(0)

    # loop per tutti i veicoli
    for veh in vehs_loaded:

        veh_current_lane = traci.vehicle.getLaneID(veh)

        # controllo se il veicolo è in una lane entrante
        if veh_current_lane[4:6] == '07':

            vehicles[veh].startingLane = veh_current_lane
            spawn_distance = traci.vehicle.getDistance(veh)
            distance = getDistanceFromLaneEnd(spawn_distance, traci.lane.getLength(veh_current_lane),
                                              junction_shape)
            if distance < 15:
                vehicles[veh].speeds.append(traci.vehicle.getSpeed(veh))
            veh_length = traci.vehicle.getLength(veh)
            check = veh_length / 2 + 0.2
            leader = traci.vehicle.getLeader(veh)
            if traci.vehicle.getSpeed(veh) <= 1:
                # verifico se il veicolo è in testa
                if check >= distance and ((leader and leader[1] < 0) or not leader):
                    vehicles[veh].hasStopped = 1
                    tails_per_lane[veh_current_lane][time - 1] += 1
                    vehicles[veh].headTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                    continue
                # verifico se il veicolo è in coda
                if leader and leader[1] <= 0.5 and vehicles[leader[0]].startingLane == veh_current_lane:
                    vehicles[veh].hasStopped = 1
                    tails_per_lane[veh_current_lane][time - 1] += 1
                    vehicles[veh].tailTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                    continue
            else:
                if schema in ['s', 'S']:
                    traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

        # controllo se il veicolo è all'interno della junction
        if veh_current_lane[1:3] == 'n7':
            vehicles[veh].speeds.append(traci.vehicle.getSpeed(veh))
            leader = traci.vehicle.getLeader(veh)
            leader_lane = ''
            if leader:
                leader_lane = traci.vehicle.getLaneID(leader[0])
            if traci.vehicle.getSpeed(veh) <= 1:
                tails_per_lane[vehicles[veh].startingLane][time - 1] += 1
                # verifico se il veicolo è in testa
                if (leader and leader_lane != veh_current_lane) or not leader:
                    vehicles[veh].headTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                    continue
                # verifico se il veicolo è in coda
                if leader and leader[1] <= 0.5 and leader_lane == veh_current_lane:
                    vehicles[veh].tailTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                    continue
            else:
                if schema in ['s', 'S']:
                    traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

        # controllo se il veicolo è in una lane uscente
        if veh_current_lane[1:3] == '07':
            if vehicles[veh].hasPassed == 0:
                vehicles[veh].hasPassed = 1
            if schema in ['s', 'S']:
                traci.vehicle.setColor(veh, (0, 255, 0))  # verde

    return vehicles, tails_per_lane

def checkVehicles(vehicles, tails_per_lane, time, schema):
    """Funzione che controlla il posizionamento dei veicoli nell'incrocio e prende le misure"""

    vehs_loaded = traci.vehicle.getIDList()
    junction_shape = traci.junction.getShape("n" + str(junction_id))

    for lane in tails_per_lane:
        tails_per_lane[lane].append(0)

    # loop per tutti i veicoli
    for veh in vehs_loaded:

        veh_current_lane = traci.vehicle.getLaneID(veh)

        # controllo se il veicolo è in una lane entrante
        if veh_current_lane[4:6] == '07':

            vehicles[veh].startingLane = veh_current_lane
            spawn_distance = traci.vehicle.getDistance(veh)
            distance = getDistanceFromLaneEnd(spawn_distance, traci.lane.getLength(veh_current_lane),
                                              junction_shape)
            if distance < 15:
                vehicles[veh].speeds.append(traci.vehicle.getSpeed(veh))
            veh_length = traci.vehicle.getLength(veh)
            check = veh_length / 2 + 0.2
            leader = traci.vehicle.getLeader(veh)
            if traci.vehicle.getSpeed(veh) <= 1:
                # verifico se il veicolo è in testa
                if check >= distance and ((leader and leader[1] < 0) or not leader):
                    vehicles[veh].hasStopped = 1
                    tails_per_lane[veh_current_lane][time - 1] += 1
                    vehicles[veh].headTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                    continue
                # verifico se il veicolo è in coda
                if leader and leader[1] <= 0.5 and vehicles[leader[0]].startingLane == veh_current_lane:
                    vehicles[veh].hasStopped = 1
                    tails_per_lane[veh_current_lane][time - 1] += 1
                    vehicles[veh].tailTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                    continue
            else:
                if schema in ['s', 'S']:
                    traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

        # controllo se il veicolo è all'interno della junction
        if veh_current_lane[1:3] == 'n7':
            vehicles[veh].speeds.append(traci.vehicle.getSpeed(veh))
            leader = traci.vehicle.getLeader(veh)
            leader_lane = ''
            if leader:
                leader_lane = traci.vehicle.getLaneID(leader[0])
            if traci.vehicle.getSpeed(veh) <= 1:
                tails_per_lane[vehicles[veh].startingLane][time - 1] += 1
                # verifico se il veicolo è in testa
                if (leader and leader_lane != veh_current_lane) or not leader:
                    vehicles[veh].headTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                    continue
                # verifico se il veicolo è in coda
                if leader and leader[1] <= 0.5 and leader_lane == veh_current_lane:
                    vehicles[veh].tailTime += 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                    continue
            else:
                if schema in ['s', 'S']:
                    traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

        # controllo se il veicolo è in una lane uscente
        if veh_current_lane[1:3] == '07':
            if vehicles[veh].hasPassed == 0:
                vehicles[veh].hasPassed = 1
            if schema in ['s', 'S']:
                traci.vehicle.setColor(veh, (0, 255, 0))  # verde

    return vehicles, tails_per_lane

def saveResultsAdaptive(vehicles, removed, numberOfVehicles, departed, tails_per_lane_per_step, passed, considered):
    """Funzione che calcola le misure adottate"""
    steps = len(numberOfVehicles)
    headTimes = []  # lista dei tempi passati in testa per ogni veicolo
    varHeadTime = []  # varianza rispetto al tempo passato in testa
    tailTimes = []  # lista dei tempi passati in coda per ogni veicolo
    varTailTime = []  # varianza rispetto al tempo passato in coda
    meanSpeeds = []  # medie delle velocità assunte dai veicoli nei pressi dell'incrocio
    varSpeed = []  # varianza rispetto alla velocità dei veicoli
    stopped = []  # lista che dice se i veicoli si sono fermati all'incrocio o no
    meanTailLength = []  # medie delle lunghezze delle code rilevate sulle lane entranti ad ogni step
    varTail = []  # varianza rispetto alla coda
    maxTail = []  # coda massima rilevata su tutte le lane entranti
    passed_per_step = []  # numero di veicoli arrivati a destinazione
    meanHeadTime = []
    stDevHeadTime = []
    maxHeadTime = []
    meanTailTime = []
    stDevTailTime = []
    maxTailTime = []
    meanSpeed = []
    stDevSpeed = []
    meanTail = []
    stoppedVehicles = []
    throughput = []
    stDevTail = []

    for s in range(0, steps):
        headTimes.append([])
        varHeadTime.append(0)
        tailTimes.append([])
        varTailTime.append(0)
        meanSpeeds.append([])
        varSpeed.append(0)
        stopped.append([])
        meanTailLength.append([])
        varTail.append(0)
        maxTail.append(-1)
        passed_per_step.append(0)
        meanHeadTime.append(0)
        stDevHeadTime.append(0)
        maxHeadTime.append(0)
        meanTailTime.append(0)
        stDevTailTime.append(0)
        maxTailTime.append(0)
        meanSpeed.append(0)
        stDevSpeed.append(0)
        meanTail.append(0)
        stoppedVehicles.append(0)
        throughput.append(0)
        stDevTail.append(0)



        #floor = sum(numberOfVehicles[0: s])
        #ceil = floor + numberOfVehicles[s]
        current_step_departed = {k:v for (k, v) in vehicles.items() if v.getID() in departed[s]}
        #vehs_to_consider_per_step = {k:v for (k, v) in vehs_departed.items() if floor <= int(v.getID()[3:]) < ceil} #and k not in removed.keys()}
        for (k, v) in current_step_departed.items():
            #if int(v.getID()[3:]) < departed_per_step[s]:
            headTimes[s].append(v.headTime)
            tailTimes[s].append(v.tailTime)
            if len(v.speeds) > 0:
                meanSpeeds[s].append(sum(v.speeds) / len(v.speeds))
            stopped[s].append(v.hasStopped)

        meanHeadTime[s] = sum(headTimes[s]) / len(headTimes[s])
        for headTime in headTimes[s]:
            varHeadTime[s] += (headTime - meanHeadTime[s]) ** 2
        stDevHeadTime[s] = sqrt(varHeadTime[s] / len(headTimes[s]))
        maxHeadTime[s] = max(headTimes[s])

        meanTailTime[s] = sum(tailTimes[s]) / len(tailTimes[s])
        for tailTime in tailTimes[s]:
            varTailTime[s] += (tailTime - meanTailTime[s]) ** 2
        stDevTailTime[s] = sqrt(varTailTime[s] / len(tailTimes[s]))
        maxTailTime[s] = max(tailTimes[s])

        if len(meanSpeeds[s]) > 0:
            meanSpeed[s] = sum(meanSpeeds[s]) / len(meanSpeeds[s])
            for speed in meanSpeeds[s]:
                varSpeed[s] += (speed - meanSpeed[s]) ** 2
            stDevSpeed[s] = sqrt(varSpeed[s] / len(meanSpeeds[s]))
        else:
            meanSpeed[s] = 0
            stDevSpeed[s] = 0

        for lane in tails_per_lane_per_step[s]:
            meanTailLength[s].append(sum(tails_per_lane_per_step[s][lane]) / len(tails_per_lane_per_step[s][lane]))
            lane_max = max(tails_per_lane_per_step[s][lane])
            if lane_max > maxTail[s]:
                maxTail[s] = lane_max

        meanTail[s] = sum(meanTailLength[s]) / len(meanTailLength[s])
        for tail in meanTailLength[s]:
            varTail[s] += (tail - meanTail[s]) ** 2
        stDevTail[s] = sqrt(varTail[s] / len(meanTailLength[s]))

        stoppedVehicles[s] = sum(stopped[s])

        throughput[s] = passed[s] / considered[s]

    return meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime, \
           meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput

def saveResults(vehicles, departed, tails_per_lane):
    """Funzione che calcola le misure adottate"""

    headTimes = []  # lista dei tempi passati in testa per ogni veicolo
    varHeadTime = 0  # varianza rispetto al tempo passato in testa
    tailTimes = []  # lista dei tempi passati in coda per ogni veicolo
    varTailTime = 0  # varianza rispetto al tempo passato in coda
    meanSpeeds = []  # medie delle velocità assunte dai veicoli nei pressi dell'incrocio
    varSpeed = 0  # varianza rispetto alla velocità dei veicoli
    stopped = []  # lista che dice se i veicoli si sono fermati all'incrocio o no
    meanTailLength = []  # medie delle lunghezze delle code rilevate sulle lane entranti ad ogni step
    varTail = 0  # varianza rispetto alla coda
    maxTail = -1  # coda massima rilevata su tutte le lane entranti
    passed = 0  # numero di veicoli arrivati a destinazione

    for veh in vehicles:
        if int(veh[-1]) < departed: #????
            headTimes.append(vehicles[veh].headTime)
            tailTimes.append(vehicles[veh].tailTime)
            if len(vehicles[veh].speeds) > 0:
                meanSpeeds.append(sum(vehicles[veh].speeds) / len(vehicles[veh].speeds))
            stopped.append(vehicles[veh].hasStopped)
            passed += vehicles[veh].hasPassed

    meanHeadTime = sum(headTimes) / len(headTimes)
    for headTime in headTimes:
        varHeadTime += (headTime - meanHeadTime) ** 2
    stDevHeadTime = sqrt(varHeadTime / len(headTimes))
    maxHeadTime = max(headTimes)

    meanTailTime = sum(tailTimes) / len(tailTimes)
    for tailTime in tailTimes:
        varTailTime += (tailTime - meanTailTime) ** 2
    stDevTailTime = sqrt(varTailTime / len(tailTimes))
    maxTailTime = max(tailTimes)

    if len(meanSpeeds) > 0:
        meanSpeed = sum(meanSpeeds) / len(meanSpeeds)
        for speed in meanSpeeds:
            varSpeed += (speed - meanSpeed) ** 2
        stDevSpeed = sqrt(varSpeed / len(meanSpeeds))
    else:
        meanSpeed = 0
        stDevSpeed = 0

    for lane in tails_per_lane:
        meanTailLength.append(sum(tails_per_lane[lane]) / len(tails_per_lane[lane]))
        lane_max = max(tails_per_lane[lane])
        if lane_max > maxTail:
            maxTail = lane_max

    meanTail = sum(meanTailLength) / len(meanTailLength)
    for tail in meanTailLength:
        varTail += (tail - meanTail) ** 2
    stDevTail = sqrt(varTail / len(meanTailLength))

    stoppedVehicles = sum(stopped)

    throughput = passed / departed

    return meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime, \
           meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput
