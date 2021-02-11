from config_no_batch import *
import random
from auction.trafficElements.vehicle import Vehicle

import traci


def getLaneFromEdges(start, end, node_ids=node_ids):
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


def generateRoutes(junction_id=junction_id, node_ids=node_ids):
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


def a(x, y, z, px, py, r):
    if r <= px:
        return x

    elif r <= (px + py):
        return y

    else:
        return z


def rand(x, y, z, px, py, numberOfVehicles, seed=seed):
    random.seed(seed)
    s = []
    for i in range(0, numberOfVehicles):
        r = random.randint(1, 100)
        index = a(x, y, z, px, py, r)
        s.append(index)

    return s


def getBalancedRoutes():
    routes = traci.route.getIDList()
    balancedRoutes = {'0': [], '1': [], '2': []}
    for route in routes:
        edges = traci.route.getEdges(route)
        index = getLaneFromEdges(int(edges[0][1:3]), int(edges[1][4:6]))
        balancedRoutes[str(index)].append(route)

    return balancedRoutes


def generateVehicles(numberOfVehicles, gen_time, vehicles, seed, object=False):
    """Genero veicoli per ogni route possibile"""

    r_depart = 0
    auto_ogni = float(gen_time) / float(numberOfVehicles)

    random.seed(seed)

    generateRoutes()
    balancedRoutes = getBalancedRoutes()
    sequence = rand(0, 1, 2, 33, 33, numberOfVehicles, seed)


    for i in range(0, numberOfVehicles):
        r_depart += auto_ogni
        if object:
            idV = f'idV{i}'
        else:
            idV = str(i)
        vehicle = {'id': idV, 'headStopTime': 0, 'followerStopTime': 0, 'speeds': [], 'hasStopped': 0, 'hasEntered': 0,
                   'isCrossing': 0, 'hasCrossed': 0, 'startingLane': ''}
        if object:
            vehicles[idV] = Vehicle(idV, vehicle, True)
        else:
            vehicles[idV] = vehicle
        r = random.choice(balancedRoutes[str(sequence[i])])
        edges = traci.route.getEdges(r)
        lane = getLaneFromEdges(int(edges[0][1:3]), int(edges[1][4:6]))
        traci.vehicle.add(idV, r, depart=r_depart, departLane=lane)

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