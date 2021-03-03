import math
from utils_multi import getLaneIndexFromEdges

import traci


def getRoute(auto, node_ids):

    route = traci.vehicle.getRouteID(auto.idVehicle)
    edges = traci.route.getEdges(route)

    suffix, start, end = getLaneIndexFromEdges(edges, auto, node_ids)

    if suffix == 0:
        if start - end == -4:
            return 'route_2'
        if start - end == -6:
            return 'route_11'
        if start - end == 4:
            return 'route_7'
        if start - end == 6:
            return 'route_3'
    if suffix == 1:
        if start - end == -10:
            return 'route_1'
        if start - end == -2:
            return 'route_10'
        if start - end == 10:
            return 'route_6'
        if start - end == 2:
            return 'route_5'
    if suffix == 2:
        if start - end == -6:
            return 'route_0'
        if start - end == 4:
            return 'route_9'
        if start - end == 6:
            return 'route_8'
        if start - end == -4:
            return 'route_4'


def stopXY(shape_temp):
    """Calcolo estremi dell'incrocio, dove sono presenti gli stop"""

    stop_temp = []

    for count in range(0, len(shape_temp) - 1):
        if shape_temp[count][0] == shape_temp[count + 1][0]:
            stop_temp.append(shape_temp[count][0])
        elif shape_temp[count][1] == shape_temp[count + 1][1]:
            stop_temp.append(shape_temp[count][1])

    return stop_temp


def limiti_celle(estremi_incrocio, celle_per_lato):
    """Calcolo i metri all'interno dell'incrocio di ogni cella della matrice"""

    # definisco i vettori
    limiti_celle_X_temp = []
    limiti_celle_Y_temp = []

    # lunghezza totale incrocio nell'asse X e Y
    lunghezza_X = estremi_incrocio[1] - estremi_incrocio[3]
    lunghezza_Y = estremi_incrocio[0] - estremi_incrocio[2]

    # lunghezza di una sola cella
    lungh_cella_X = float(lunghezza_X) / float(celle_per_lato)
    lungh_cella_Y = float(lunghezza_Y) / float(celle_per_lato)

    for i in range(0, celle_per_lato + 1):  # scrivo sui vettori
        limiti_celle_X_temp.append(round((estremi_incrocio[3] + (lungh_cella_X * i)), 3))
        limiti_celle_Y_temp.append(round((estremi_incrocio[0] - (lungh_cella_Y * i)), 3))

    return [limiti_celle_X_temp, limiti_celle_Y_temp]


def get_cella_from_pos_auto(auto_temp, limiti_celle_X_temp, limiti_celle_Y_temp):
    """Ritorno le coordinate della cella nella matrice in cui si trova l'auto"""

    cella_X = 0
    cella_Y = 0
    pos = traci.vehicle.getPosition(auto_temp)

    for x in range(0, len(limiti_celle_X_temp) - 1):
        if limiti_celle_X_temp[x] <= pos[0] <= limiti_celle_X_temp[x + 1]:
            cella_X = x

    for y in range(0, len(limiti_celle_Y_temp) - 1):
        if limiti_celle_Y_temp[y] >= pos[1] >= limiti_celle_Y_temp[y + 1]:
            cella_Y = y

    return [auto_temp, cella_X, cella_Y]


def in_incrocio(pos_temp, estremi_incrocio):
    """Controllo se l'auto è all'incrocio"""

    if (estremi_incrocio[3] <= pos_temp[0] <= estremi_incrocio[1]) and \
            (estremi_incrocio[2] <= pos_temp[1] <= estremi_incrocio[0]):
        return True
    else:
        return False


def metri_da_incrocio(auto_temp, estremi_incrocio):
    """Calcolo la distanza dell'auto in metri dall'incrocio come numero negativo (l'inizio dell'incrocio è 0)"""

    pos = traci.vehicle.getPosition(auto_temp)
    ang = traci.vehicle.getAngle(auto_temp)
    dist = 0
    if ang == 0:
        dist = abs(float(estremi_incrocio[2]) - float(pos[1]))
    if ang == 180:
        dist = abs(float(estremi_incrocio[0]) - float(pos[1]))
    if ang == 90:
        dist = abs(float(estremi_incrocio[3]) - float(pos[0]))
    if ang == 270:
        dist = abs(float(estremi_incrocio[1]) - float(pos[0]))
    dist = 0 - dist
    return dist


def t_arrivo_cella(auto_temp, metri_da_incrocio_temp, metri_da_cella_temp):
    """Calcolo il timestep di arrivo sulla cella"""

    vi = traci.vehicle.getSpeed(auto_temp)
    vf = traci.vehicle.getMaxSpeed(auto_temp)
    a = traci.vehicle.getAccel(auto_temp)
    xa = (((vf * vf) - (vi * vi)) / (float(2) * a)) + metri_da_incrocio_temp
    t1 = (- vi + math.sqrt((vi * vi) + (float(2) * a) * (xa - metri_da_incrocio_temp))) / a
    t2 = (metri_da_cella_temp - xa) / vf
    t = t1 + t2
    t = round(t, 4)

    return t + traci.simulation.getTime()


def celle_occupate_data_ang(ang, x_auto_in_celle_temp, y_auto_in_celle_temp):
    """Restituisce le celle occupate data l'angolazione del veicolo, centrate in [0][0]"""

    celle_occupate = []
    ang = ang % 180
    ang = - ang
    x_auto = x_auto_in_celle_temp * 1.2
    y_auto = y_auto_in_celle_temp * 1.1

    ang = math.radians(ang)  # converto in radianti
    a1 = [- float(x_auto) / float(2), float(y_auto) / float(2)]
    a2 = [float(x_auto) / float(2), float(y_auto) / float(2)]
    b1 = [- float(x_auto) / float(2), - float(y_auto) / float(2)]
    b2 = [float(x_auto) / float(2), - float(y_auto) / float(2)]

    # coordinate degli angoli ruotati
    a1 = [round(a1[0] * math.cos(ang) - a1[1] * math.sin(ang), 4),
          round(a1[0] * math.sin(ang) + a1[1] * math.cos(ang), 4)]
    a2 = [round(a2[0] * math.cos(ang) - a2[1] * math.sin(ang), 4),
          round(a2[0] * math.sin(ang) + a2[1] * math.cos(ang), 4)]
    b1 = [round(b1[0] * math.cos(ang) - b1[1] * math.sin(ang), 4),
          round(b1[0] * math.sin(ang) + b1[1] * math.cos(ang), 4)]
    b2 = [round(b2[0] * math.cos(ang) - b2[1] * math.sin(ang), 4),
          round(b2[0] * math.sin(ang) + b2[1] * math.cos(ang), 4)]

    r1 = [a2[1] - a1[1], a1[0] - a2[0], - a1[0] * a2[1] + a2[0] * a1[1]]
    r2 = [b2[1] - a2[1], a2[0] - b2[0], - a2[0] * b2[1] + b2[0] * a2[1]]
    r3 = [b2[1] - b1[1], b1[0] - b2[0], - b1[0] * b2[1] + b2[0] * b1[1]]
    r4 = [b1[1] - a1[1], a1[0] - b1[0], - a1[0] * b1[1] + b1[0] * a1[1]]

    # per ogni cella guardo se uno dei 4 angoli e' all'interno del rettangolo
    massimo = max([x_auto, y_auto])
    for y_cella in range(-int(massimo / 2) - 3, int(massimo / 2) + 4):
        for x_cella in range(-int(massimo / 2) - 3, int(massimo / 2) + 4):
            inserito = False
            if not inserito and (r1[0] * (x_cella - 0.5) + r1[1] * (y_cella - 0.5) + r1[2] >= 0) and \
                    (r2[0] * (x_cella - 0.5) + r2[1] * (y_cella - 0.5) + r2[2] >= 0) and \
                    (r3[0] * (x_cella - 0.5) + r3[1] * (y_cella - 0.5) + r3[2] <= 0) and \
                    (r4[0] * (x_cella - 0.5) + r4[1] * (y_cella - 0.5) + r4[2] <= 0):
                celle_occupate.append([y_cella, x_cella])
                inserito = True
            if not inserito and (r1[0] * (x_cella + 0.5) + r1[1] * (y_cella - 0.5) + r1[2] >= 0) and \
                    (r2[0] * (x_cella + 0.5) + r2[1] * (y_cella - 0.5) + r2[2] >= 0) and \
                    (r3[0] * (x_cella + 0.5) + r3[1] * (y_cella - 0.5) + r3[2] <= 0) and \
                    (r4[0] * (x_cella + 0.5) + r4[1] * (y_cella - 0.5) + r4[2] <= 0):
                celle_occupate.append([y_cella, x_cella])
                inserito = True
            if not inserito and (r1[0] * (x_cella - 0.5) + r1[1] * (y_cella + 0.5) + r1[2] >= 0) and \
                    (r2[0] * (x_cella - 0.5) + r2[1] * (y_cella + 0.5) + r2[2] >= 0) and \
                    (r3[0] * (x_cella - 0.5) + r3[1] * (y_cella + 0.5) + r3[2] <= 0) and \
                    (r4[0] * (x_cella - 0.5) + r4[1] * (y_cella + 0.5) + r4[2] <= 0):
                celle_occupate.append([y_cella, x_cella])
                inserito = True
            if not inserito and (r1[0] * (x_cella + 0.5) + r1[1] * (y_cella + 0.5) + r1[2] >= 0) and \
                    (r2[0] * (x_cella + 0.5) + r2[1] * (y_cella + 0.5) + r2[2] >= 0) and \
                    (r3[0] * (x_cella + 0.5) + r3[1] * (y_cella + 0.5) + r3[2] <= 0) and \
                    (r4[0] * (x_cella + 0.5) + r4[1] * (y_cella + 0.5) + r4[2] <= 0):
                celle_occupate.append([y_cella, x_cella])
                inserito = True

    return celle_occupate


def arrivoAuto(auto_temp, passaggio_temp, ferme_temp, attesa_temp, matrice_incrocio_temp, passaggio_cella_temp,
               traiettorie_matrice_temp, estremi_incrocio, sec_sicurezza, x_auto_in_celle_temp, y_auto_in_celle_temp,
               vehicles, node_ids):
    """Gestisco l'arrivo dell'auto in prossimità dello stop"""

    if not get_from_matrice_incrocio(auto_temp, matrice_incrocio_temp, traiettorie_matrice_temp, estremi_incrocio,
                                     sec_sicurezza, x_auto_in_celle_temp, y_auto_in_celle_temp, vehicles, node_ids):
        # faccio fermare l'auto
        ferme_temp.append(auto_temp)
        traci.vehicle.setSpeed(auto_temp, 0.0)
    # l'auto può passare, la segno nella matrice e nei vettori
    else:
        # disattivo la safe speed del veicolo
        traci.vehicle.setSpeedMode(auto_temp, 30)
        passaggio_temp.append([auto_temp, traci.vehicle.getRoadID(auto_temp), traci.vehicle.getAngle(auto_temp)])
        # tolgo l'auto dalla lista d'attesa e la sottoscrivo nella matrice
        attesa_temp.pop(attesa_temp.index(auto_temp))
        matrice_incrocio_temp = set_in_matrice_incrocio(auto_temp, matrice_incrocio_temp, traiettorie_matrice_temp,
                                                        estremi_incrocio, x_auto_in_celle_temp, y_auto_in_celle_temp,
                                                        vehicles, node_ids)

        rotta = traci.vehicle.getRouteID(auto_temp)
        edges = traci.route.getEdges(rotta)
        lane = getLaneIndexFromEdges(edges, vehicles[auto_temp], node_ids)
        # se l'auto non gira a destra
        if lane != 0:
            passaggio_cella_temp.append([auto_temp, None, None])
        # se l'auto gira a destra la faccio rallentare fino a dimezzarne la velocità
        else:
            traci.vehicle.setSpeed(auto_temp, traci.vehicle.getMaxSpeed(auto_temp) / float(2))

    ritorno = [passaggio_temp, attesa_temp, ferme_temp, matrice_incrocio_temp, passaggio_cella_temp]
    return ritorno


def set_in_matrice_incrocio(auto_temp, matrice_incrocio_temp, traiettorie_matrice_temp, estremi_incrocio,
                            x_auto_in_celle_temp, y_auto_in_celle_temp, vehicles, node_ids):
    """Segna sulla matrice_incrocio l'occupazione delle celle toccate dall'auto durante l'attraversamento"""

    rotta = getRoute(vehicles[auto_temp], node_ids)

    for route in traiettorie_matrice_temp:
        if route[0] == rotta:
            for celle in route[1]:
                # calcolo timestep di arrivo su tale cella
                timestep = t_arrivo_cella(auto_temp, metri_da_incrocio(auto_temp, estremi_incrocio), celle[2])
                celle_occupate = celle_occupate_data_ang(celle[3], x_auto_in_celle_temp, y_auto_in_celle_temp)
                # controllo le celle occupate dall'auto
                for celle_circostanti in celle_occupate:
                    index_y = celle_circostanti[0]
                    index_x = celle_circostanti[1]
                    if ((celle[0] + index_y) >= 0) and ((celle[1] + index_x) >= 0) and \
                            ((celle[0] + index_y) < len(matrice_incrocio_temp)) and \
                            ((celle[1] + index_x) < len(matrice_incrocio_temp)):
                        matrice_incrocio_temp[celle[0] + index_y][celle[1] + index_x].append(round(timestep, 4))

    return matrice_incrocio_temp


def get_from_matrice_incrocio(auto_temp, matrice_incrocio_temp, traiettorie_matrice_temp, estremi_incrocio,
                              sec_sicurezza, x_auto_in_celle_temp, y_auto_in_celle_temp, vehicles, node_ids):
    """Data l'auto e la matrice dell'incrocio restituisce True se non sono state rilevate collisioni
    dall'attuale situazione di passaggio rilevata all'interno della matrice, False se sono rilevate collisioni"""

    rotta = getRoute(vehicles[auto_temp], node_ids)

    libero = True

    for route in traiettorie_matrice_temp:
        if route[0] == rotta and libero:
            for celle in route[1]:
                timestep = t_arrivo_cella(auto_temp, metri_da_incrocio(auto_temp, estremi_incrocio), celle[2])
                celle_occupate = celle_occupate_data_ang(celle[3], x_auto_in_celle_temp, y_auto_in_celle_temp)
                # controllo le celle occupate dall'auto
                for celle_circostanti in celle_occupate:
                    index_y = celle_circostanti[0]
                    index_x = celle_circostanti[1]
                    if ((celle[0] + index_y) >= 0) and ((celle[1] + index_x) >= 0) and \
                            ((celle[0] + index_y) < len(matrice_incrocio_temp)) and \
                            ((celle[1] + index_x) < len(matrice_incrocio_temp)):
                        # scorre i tempi di occupazione segnati all'interno della cella
                        for t in matrice_incrocio_temp[celle[0] + index_y][celle[1] + index_x]:
                            # controlla che il timestep di arrivo calcolato non cada in un range di sicurezza
                            # dal valore selezionato
                            if t - sec_sicurezza <= timestep <= t + sec_sicurezza:
                                libero = False
                                break

    return libero


def percorso_libero(passaggio_temp, matrice_incrocio_temp, passaggio_cella_temp, limiti_celle_X_temp,
                    limiti_celle_Y_temp, estremi_incrocio, vehicles, node_ids):
    """Controllo se è cambiata la situazione all'interno dell'incrocio"""

    passaggio_nuovo = passaggio_temp[:]
    passaggio_cella_nuovo = passaggio_cella_temp[:]

    for x in passaggio_temp:

        rotta = traci.vehicle.getRouteID(x[0])
        edges = traci.route.getEdges(rotta)
        lane = getLaneIndexFromEdges(edges, vehicles[x[0]], node_ids)
        # se l'auto non gira a destra
        if lane != 0:
            for y in passaggio_cella_temp:
                if x[0] == y[0]:

                    pos = traci.vehicle.getPosition(x[0])
                    # se l'auto è ancora nell'incrocio
                    if in_incrocio(pos, estremi_incrocio):

                        cella = get_cella_from_pos_auto(x[0], limiti_celle_X_temp, limiti_celle_Y_temp)
                        pos_attuale_X = cella[1]
                        pos_attuale_Y = cella[2]
                        # se la posizione dell'auto nelle celle cambia
                        if pos_attuale_X != y[1] or pos_attuale_Y != y[2]:
                            # aggiorno poi il vettore con la nuova posizione della cella in cui si trova l'auto
                            passaggio_cella_nuovo[passaggio_cella_nuovo.index(y)] = [y[0], pos_attuale_X, pos_attuale_Y]
                    # se l'auto è uscita dall'incrocio
                    else:
                        # se ho None allora l'auto non è ancora entrata nell'incrocio e non la tolgo
                        if y[1] is not None and y[2] is not None:
                            passaggio_nuovo.pop(passaggio_nuovo.index(x))
                            passaggio_cella_nuovo.pop(passaggio_cella_nuovo.index(y))
        # se gira a destra guardo se cambia strada e la tolgo dal vettore passaggio
        else:
            road = prossimaStrada(x)
            if traci.vehicle.getRoadID(x[0]) == road:
                passaggio_nuovo.pop(passaggio_nuovo.index(x))
                # faccio riaccelerare l'auto
                traci.vehicle.setSpeed(x[0], traci.vehicle.getMaxSpeed(x[0]) * 4)

    info = [passaggio_nuovo, matrice_incrocio_temp, passaggio_cella_nuovo]
    return info


def avantiAuto(auto_temp, passaggio_temp, attesa_temp, ferme_temp, matrice_incrocio_temp, passaggio_cella_temp,
               traiettorie_matrice_temp, estremi_incrocio, x_auto_in_celle_temp, y_auto_in_celle_temp, vehicles,
               node_ids):
    """Faccio avanzare le auto"""

    traci.vehicle.setSpeedMode(auto_temp, 30)

    traci.vehicle.setSpeed(auto_temp, traci.vehicle.getMaxSpeed(auto_temp))  # riparte l'auto
    passaggio_temp.append([auto_temp, traci.vehicle.getRoadID(auto_temp), traci.vehicle.getAngle(auto_temp)])
    matrice_incrocio_temp = set_in_matrice_incrocio(auto_temp, matrice_incrocio_temp, traiettorie_matrice_temp,
                                                    estremi_incrocio, x_auto_in_celle_temp, y_auto_in_celle_temp,
                                                    vehicles, node_ids)

    if ferme_temp:
        try:
            ferme_temp.pop(ferme_temp.index(auto_temp))  # tolgo dalla lista di auto ferme
        except ValueError:  # per le auto che faccio partire senza fermare non serve toglerle dalla lista
            pass
    attesa_temp.pop(attesa_temp.index(auto_temp))  # tolgo dalla lista l'auto
    passaggio_cella_temp.append([auto_temp, None, None])
    info = [passaggio_temp, attesa_temp, ferme_temp, matrice_incrocio_temp, passaggio_cella_temp]
    return info


def prossimaStrada(passaggio_temp):
    """Ottengo il nome della via a cui l'auto e' diretta"""

    route = traci.vehicle.getRoute(passaggio_temp[0])  # ottengo rotta dell'auto che sta attraversando
    att_road = passaggio_temp[1]  # strada attuale
    pross_roadID = route.index(att_road) + 1  # posizione nel vettore attuale via + 1 = prossima
    pross_road = route[pross_roadID]  # prossima strada
    return pross_road


def costruzioneArray(arrayAuto_temp):
    """Costruzione dell'array composto dal nome delle auto presenti nella simulazione"""

    loadedIDList = traci.simulation.getDepartedIDList()  # carica nell'array le auto partite
    for id_auto in loadedIDList:
        if id_auto not in arrayAuto_temp:
            arrayAuto_temp.append(id_auto)
            traci.vehicle.setSpeed(id_auto, traci.vehicle.getMaxSpeed(id_auto))

    arrivedIDList = traci.simulation.getArrivedIDList()  # elimina nell'array le auto arrivate
    for id_auto in arrivedIDList:
        if id_auto in arrayAuto_temp:
            arrayAuto_temp.pop(arrayAuto_temp.index(id_auto))

    return arrayAuto_temp


def pulisci_matrice(matrice_incrocio_temp, sec_sicurezza_temp):
    "Ogni 10 step pulisco la matrice da valori vecchi"

    matrice_incrocio = []
    for incr in matrice_incrocio_temp:
        index_incr = matrice_incrocio_temp.index(incr)
        matrice_incrocio.append(incr)
        for y in matrice_incrocio_temp[index_incr]:
            index_y = matrice_incrocio_temp[index_incr].index(y)
            for x in matrice_incrocio_temp[index_incr][index_y]:
                index_x = matrice_incrocio_temp[index_incr][index_y].index(x)
                for val in matrice_incrocio_temp[index_incr][index_y][index_x]:
                    index_val = matrice_incrocio_temp[index_incr][index_y][index_x].index(val)
                    if val < (traci.simulation.getTime() - sec_sicurezza_temp - 1):
                        matrice_incrocio[index_incr][index_y][index_x].pop(index_val)

    return matrice_incrocio