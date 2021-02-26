import random
from precedence_with_auction.trafficElements.vehicle import Vehicle

import traci

def checkIfMainStep(total_time, n_steps, n_vehs, step, vehicles, departed, mean_th_per_num, is_vehicle_object=False):

    check, temp = saveIntermediateResults(total_time, n_steps, n_vehs, step, vehicles, departed, is_vehicle_object)
    if check:
        mean_th_per_num[step] = temp
        step += 1
        departed = 0

    return mean_th_per_num, step, departed

def saveIntermediateResults(total_time, n_steps, n_vehs, step, vehicles, departed, is_vehicle_object=False):

    mean_th = -1
    mod = total_time % (n_steps / len(n_vehs))
    if mod == 0 and total_time <= n_steps:
        passed = 0
        floor = sum(n_vehs[0: step])
        ceil = floor + n_vehs[step]
        ids = [k for k in vehicles]
        ids_c = ids[floor: ceil]
        dummy = {k: vehicles[k] for k in vehicles if k in ids_c}
        for veh in dummy:
            if int(veh) < departed:
                if is_vehicle_object:
                    passed += vehicles[veh].measures['hasPassed']
                else:
                    passed += vehicles[veh]['hasPassed']
        mean_th = passed / departed

    if mean_th == -1:
        return False, mean_th
    else:
        return True, mean_th

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


def generateLaneSequence(px, py, numberOfVehicles, seed):
    """Genero la sequenza di lane equiprobabili"""

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


def generateVehicles(numberOfSteps, numberOfVehicles, vehicles, seed, junction_id, node_ids, object=False,
                     wallet=False):
    """Genero veicoli per ogni route possibile"""

    c = 0
    t = 0

    depart = 0
    auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]

    random.seed(seed)

    routes = generateRoutes(junction_id, node_ids)
    sequence = generateLaneSequence(33, 33, sum(numberOfVehicles), seed)

    for i in range(0, sum(numberOfVehicles)):
        if t < numberOfVehicles[c]:
            t += 1
        else:
            t = 0
            c += 1
            auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]
        depart += auto_every
        if object:
            idV = f'idV{i}'
        else:
            idV = str(i)
        vehicle = {'id': idV, 'headTime': 0, 'tailTime': 0, 'speeds': [], 'hasStopped': 0, 'hasPassed': 0,
                   'startingLane': ''}
        if object:
            vehicles[idV] = Vehicle(idV, vehicle, True)
        else:
            vehicles[idV] = vehicle
        route = random.choice(routes[str(sequence[i])])
        edges = traci.route.getEdges(route)
        lane = getLaneIndexFromEdges(int(edges[0][1:3]), int(edges[1][4:6]), node_ids)
        traci.vehicle.add(idV, route, depart=depart, departLane=lane)
        traci.vehicle.setMaxSpeed(idV, 9.72)
        if wallet:
            traci.vehicle.setParameter(idV, "wallet", str(50))

    return vehicles


def colorVehicles(numberOfVehicles):
    "Assegno un colore diverso alle auto"

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
