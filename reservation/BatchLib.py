# SEMPLIFICAZIONI:
# - incrocio a forma di "+" e strade ad angoli multipli di 90 gradi
# - ricordarsi di modificare il tipo di junction in netedit, in unregulated o l'ultimo

import os
import sys
import random
import math
import traci
import subprocess
import Traiettorie
import output

node_ids = [2, 8, 12, 6]
junction_id = 7
config_file = "intersection.sumocfg"
period = 10  # tempo di valutazione del throughput del sistema incrocio


# -------- FUNZIONI --------

def checkInput(d, def_string, ask_string, error_string):
    """Funzione che verifica se l'input dell'utente è corretto"""

    i = 0
    while i <= 0:
        t = input(def_string)
        if t == '':
            i = d  # default
            print(ask_string)
        else:
            try:
                i = int(t)
            except:
                print(error_string)
                i = 0
                continue
            if i <= 0:
                print(error_string)
    return i


def getLaneFromEdges(node_ids, start, end):
    """Prendo la lane corretta associata all'edge di partenza e di arrivo"""

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
        lane = 4
    if distance == 2:
        lane = 2
    if distance == 3:
        lane = 0
    return lane


def generateRoute(node_ids, junction_id):
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


def generaVeicoli(n_auto_t, t_gen):
    """Genero veicoli per ogni route"""

    # r_depart = 0
    # auto_ogni = float(t_gen) / float(n_auto_t)

    generateRoute(node_ids, junction_id)

    for i in range(0, n_auto_t):
        r = int(random.randint(0, 11))
        edges = traci.route.getEdges(f'route_{r}')
        lane = getLaneFromEdges(node_ids, int(edges[0][1:3]), int(edges[1][4:6]))
        # r_depart += auto_ogni
        id_veh = "veh_" + str(i)
        traci.vehicle.add(id_veh, f'route_{r}', departLane=lane)
        # depart=str(r_depart), departSpeed="13.88888"


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
               traiettorie_matrice_temp, estremi_incrocio, sec_sicurezza, x_auto_in_celle_temp, y_auto_in_celle_temp):
    """Gestisco l'arrivo dell'auto in prossimità dello stop"""

    if not get_from_matrice_incrocio(auto_temp, matrice_incrocio_temp, traiettorie_matrice_temp, estremi_incrocio,
                                     sec_sicurezza, x_auto_in_celle_temp, y_auto_in_celle_temp):
        # faccio fermare l'auto
        ferme_temp.append(auto_temp)
        traci.vehicle.setSpeed(auto_temp, 0.0)
    # l'auto può passare, la segno nella matrice e nei vettori
    else:
        traci.vehicle.setSpeedMode(auto_temp, 30)
        passaggio_temp.append([auto_temp, traci.vehicle.getRoadID(auto_temp), traci.vehicle.getAngle(auto_temp)])
        # tolgo l'auto dalla lista d'attesa e la sottoscrivo nella matrice
        attesa_temp.pop(attesa_temp.index(auto_temp))
        matrice_incrocio_temp = set_in_matrice_incrocio(auto_temp, matrice_incrocio_temp, traiettorie_matrice_temp,
                                                        estremi_incrocio, x_auto_in_celle_temp, y_auto_in_celle_temp)

        rotta = traci.vehicle.getRouteID(auto_temp)
        edges = traci.route.getEdges(rotta)
        lane = getLaneFromEdges(node_ids, int(edges[0][1:3]), int(edges[1][4:6]))
        # se l'auto non gira a destra
        if lane != 0:
            passaggio_cella_temp.append([auto_temp, None, None])
        # se l'auto gira a destra la faccio rallentare fino a dimezzarne la velocità
        else:
            traci.vehicle.setSpeed(auto_temp, traci.vehicle.getMaxSpeed(auto_temp) / float(2))

    ritorno = [passaggio_temp, attesa_temp, ferme_temp, matrice_incrocio_temp, passaggio_cella_temp]
    return ritorno


def set_in_matrice_incrocio(auto_temp, matrice_incrocio_temp, traiettorie_matrice_temp, estermi_incrocio,
                            x_auto_in_celle_temp, y_auto_in_celle_temp):
    """Segna sulla matrice_incrocio l'occupazione delle celle toccate dall'auto durante l'attraversamento"""

    rotta = traci.vehicle.getRouteID(auto_temp)

    for route in traiettorie_matrice_temp:
        if route[0] == rotta:
            for celle in route[1]:
                # calcolo timestep di arrivo su tale cella
                timestep = t_arrivo_cella(auto_temp, metri_da_incrocio(auto_temp, estermi_incrocio), celle[2])
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


def get_from_matrice_incrocio(auto_temp, matrice_incrocio_temp, traiettorie_matrice_temp, estermi_incrocio,
                              sec_sicurezza, x_auto_in_celle_temp, y_auto_in_celle_temp):
    """Data l'auto e la matrice dell'incrocio restituisce True se non sono state rilevate collisioni
    dall'attuale situazione di passaggio rilevata all'interno della matrice, False se sono rilevate collisioni"""

    rotta = traci.vehicle.getRouteID(auto_temp)

    libero = True

    for route in traiettorie_matrice_temp:
        if route[0] == rotta and libero:
            for celle in route[1]:
                timestep = t_arrivo_cella(auto_temp, metri_da_incrocio(auto_temp, estermi_incrocio), celle[2])
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
                    limiti_celle_Y_temp,
                    estremi_incrocio):
    """Controllo se è cambiata la situazione all'interno dell'incrocio"""

    passaggio_nuovo = passaggio_temp[:]
    passaggio_cella_nuovo = passaggio_cella_temp[:]

    for x in passaggio_temp:

        rotta = traci.vehicle.getRouteID(x[0])
        edges = traci.route.getEdges(rotta)
        lane = getLaneFromEdges(node_ids, int(edges[0][1:3]), int(edges[1][4:6]))
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
               traiettorie_matrice_temp, estremi_incrocio, x_auto_in_celle_temp, y_auto_in_celle_temp):
    """Faccio avanzare le auto"""

    traci.vehicle.setSpeedMode(auto_temp, 30)

    traci.vehicle.setSpeed(auto_temp, traci.vehicle.getMaxSpeed(auto_temp))  # riparte l'auto
    passaggio_temp.append([auto_temp, traci.vehicle.getRoadID(auto_temp), traci.vehicle.getAngle(auto_temp)])
    matrice_incrocio_temp = set_in_matrice_incrocio(auto_temp, matrice_incrocio_temp, traiettorie_matrice_temp,
                                                    estremi_incrocio, x_auto_in_celle_temp, y_auto_in_celle_temp)

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


def coloreAuto(arrayAuto_temp, junctIDList_temp, attesa_temp, ferme_temp):
    """Colora le auto a seconda del loro stato"""

    for auto_temp in arrayAuto_temp:
        colorata = False
        for junctID in range(0, len(junctIDList_temp)):
            if auto_temp in attesa_temp[junctID]:
                colorata = True
                if auto_temp in ferme_temp[junctID]:
                    traci.vehicle.setColor(auto_temp, (255, 0, 0))
                else:
                    traci.vehicle.setColor(auto_temp, (255, 255, 0))
        if not colorata:
            traci.vehicle.setColor(auto_temp, (0, 255, 0))


def output(arrayAuto_temp, consumo_temp):
    """Preparo i valori per scriverli nei file di output"""

    vmed = 0
    ferme_count = 0
    for auto_temp in arrayAuto_temp:
        if round(traci.vehicle.getSpeed(auto_temp), 3) == 0:
            ferme_count += 1
        vmed += traci.vehicle.getSpeed(auto_temp)

        if auto_temp not in consumo_temp:
            consumo_temp[auto_temp] = []
            consumo_temp[auto_temp].append(traci.vehicle.getElectricityConsumption(auto_temp) * 8)
        else:
            consumo_temp[auto_temp].append(traci.vehicle.getElectricityConsumption(auto_temp) * 8)

    # calcoli per scrivere i valori nel file code
    code = []
    # scorro le strade
    for viaID in traci.edge.getIDList():
        if not viaID.startswith(":"):
            # coda per ogni lane nella strada
            coda0 = 0
            coda1 = 0
            coda2 = 0
            # scorro le auto presenti nella simulazione
            for auto_temp in arrayAuto_temp:
                # controllo se l'auto è su quella via
                if traci.vehicle.getRoadID(auto_temp) == viaID:
                    # se la velocità è 0 controllo la corsia e aggiungo 1 alla relativa coda
                    if round(traci.vehicle.getSpeed(auto_temp), 3) == 0:
                        corsia = traci.vehicle.getLaneIndex(auto_temp)
                        if corsia == 0:
                            coda0 += 1
                        if corsia == 2:
                            coda1 += 1
                        if corsia == 4:
                            coda2 += 1
            # se ci sono auto nella coda di quella corsia inserisco nel vettore code
            if coda0 > 0:
                code.append(coda0)
            if coda1 > 0:
                code.append(coda1)
            if coda2 > 0:
                code.append(coda2)

    codesum = 0
    for count in range(0, len(code)):
        codesum += code[count]

    if len(arrayAuto_temp) > 0:

        # costruisco riga nel file velocità media
        vmed = float(vmed) / float(len(arrayAuto_temp))
        vmed = round(vmed, 4)

        if len(code) > 0:
            # costruisco riga nel file code
            codemed = float(codesum) / float(len(code))
            cmed = round(codemed, 4)

            codemax = max(code)
            cmax = round(codemax, 4)

        else:
            cmax = 0.0
            cmed = 0.0
    else:
        ferme_count = 0
        vmed = 0.0
        cmax = 0.0
        cmed = 0.0

    return ferme_count, vmed, cmed, cmax, consumo_temp


def output_t_in_coda(arrayAuto_temp, auto_coda_temp, step_temp, attesa_temp):
    """Scrivo in un array il tempo in coda medio rispetto al tempo totale di simulazione"""

    for auto_temp in arrayAuto_temp:
        split = str(auto_temp).rsplit("_")
        auto_temp_ID = int(split[1])
        if auto_coda_temp[auto_temp_ID][0] == 0:
            if round(traci.vehicle.getSpeed(auto_temp), 3) == 0:  # se auto ferma allora segno timestep inizio coda
                auto_coda_temp[auto_temp_ID][0] = step_temp
        if auto_coda_temp[auto_temp_ID][0] != 0 and auto_coda_temp[auto_temp_ID][1] == 0 and \
                auto_temp not in attesa_temp:  # se non e' piu' in attesa allora segno timestep di fine coda
            auto_coda_temp[auto_temp_ID][1] = step_temp
    return auto_coda_temp


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


def run(port_t, n_auto, t_generazione, gui, celle_per_lato, traiettorie_matrice, sec_sicurezza):
    # -------- import python modules from the $SUMO_HOME/tools directory --------

    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', "tools"))  # tutorial in tests
        sys.path.append(os.path.join(os.environ.get("SUMO_HOME", os.path.join(
            os.path.dirname(__file__), "..", "..", "..")), "tools"))  # tutorial in docs
        from sumolib import checkBinary
    except ImportError:
        sys.exit("please declare environment variable 'SUMO_HOME' as the root directory of your sumo installation "
                 "(it should contain folders 'bin', 'tools' and 'docs')")

    PORT = port_t
    if gui:
        sumoBinary = checkBinary('sumo-gui')
    else:
        sumoBinary = checkBinary('sumo')

    # -------- percorsi cartella e file SUMO --------

    direct = "SUMO/"
    config_sumo = "intersection.sumocfg"  # nome del file SUMO config

    # -----------------------------------------------

    sumoProcess = subprocess.Popen(
        [sumoBinary, "-c", direct + config_sumo, "--remote-port", str(PORT), "--time-to-teleport", "-1", "-S", "-Q",
         "--step-length", "0.001"],
        stdout=sys.stdout,
        stderr=sys.stderr)

    # -------- dichiarazione variabili --------

    traci.init(PORT)
    step = 0.000
    step_incr = 0.036

    auto_in_simulazione = n_auto  # auto tot generate nella simulazione da passare come parametro in batch
    generaVeicoli(auto_in_simulazione, t_generazione)  # genero veicoli

    # istanzio le matrici [nome_incrocio, variabile]
    attesa = []  # ordine di arrivo su lista, si resetta quando le auto liberano incrocio
    passaggio = []  # auto in passaggio nell'incrocio
    lista_arrivo = []  # auto entrate nelle vicinanze dell'incrocio, non si resetta
    matrice_incrocio = []  # rappresenta la suddivisione matriciale dell'incrocio (in celle)
    lista_uscita = []  # auto uscite dall'incrocio, non si resetta
    ferme = []  # lista di auto ferme allo stop
    stop = []  # lista che indica di quanto si distanzia lo stop dal centro dell'incrocio [dx, sotto, sx, sopra]
    centerJunctID = []  # coordinate (x,y) del centro di un incrocio
    arrayAuto = []  # contiene la lista di auto presenti nella simulazione
    tempo_coda = []  # usata per fare calcoli su output del tempo medio in coda
    limiti_celle_X = []  # utile per verificare l'appartenenza ad una cella all'interno della matrice dell'incrocio
    limiti_celle_Y = []  # utile per verificare l'appartenenza ad una cella all'interno della matrice dell'incrocio
    passaggio_cella = []  # salvo in che cella si trova l'auto in passaggio [incrID][ [ auto , cella_X , cella_Y ],... ]
    consumo = dict()  # lista di consumi rilevati per ogni auto
    rallentate = []  # lista di auto rallentate in prossimità dell'incrocio
    passaggio_precedente = []  # salvo l'ultima situazione di auto in passaggio per rilasciarle all'uscita

    rientro4 = [passaggio, attesa, ferme, matrice_incrocio]

    f_s = []
    vm_s = []
    cm_s = []
    cx_s = []

    # -------- trovo lista degli incroci --------

    junctIDList_temp = []  # lista degli incroci
    junctIDList_tupla = traci.junction.getIDList()  # creo lista degli incroci (creo l'array dalla tupla)
    for junct in junctIDList_tupla:
        if not junct.startswith(":"):  # elimino gli incroci che iniziano con ':'
            junctIDList_temp.append(junct)

    junctIDList = []  # lista degli incroci

    for junctID in range(0, len(junctIDList_temp)):  # elimino gli incroci di estremità, non sono degli incroci
        junct = junctIDList_temp[junctID]
        junctShape = traci.junction.getShape(junct)
        if len(junctShape) > 3:
            junctIDList.append(junct)

    # ---------- MAIN ----------

    for incrNome in junctIDList:  # scorro lista incroci
        incrID = junctIDList.index(incrNome)  # popolo vettori e matrici inserendo le righe
        attesa.append([])
        lista_arrivo.append([])
        lista_uscita.append([])
        ferme.append([])
        passaggio.append([])
        rallentate.append([])
        passaggio_cella.insert(incrID, [])
        passaggio_precedente.append([])

        centerJunctID.append(traci.junction.getPosition(incrNome))  # posizione del centro dell'incrocio

        shape = traci.junction.getShape(incrNome)  # forma dell'incrocio
        stop.append(stopXY(shape))  # estremi dell'incrocio, dove sono presenti gli stop

        # popolo i vettori limiti_celle_X e limiti_celle_Y
        limiti = limiti_celle(stopXY(shape), celle_per_lato)
        limiti_celle_X.append(limiti[0])
        limiti_celle_Y.append(limiti[1])
        # popolo il vettore per il calcolo del tempo medio in coda
        tempo_coda.insert(incrID, [])
        for i in range(0, n_auto):
            tempo_coda[incrID].insert(i, [0, 0])
        # popolo la matrice dell'incrocio
        matrice_incrocio.append([])
        for x in range(0, celle_per_lato):
            matrice_incrocio[incrID].append([])
            for y in range(0, celle_per_lato):
                # ogni cella è un'array dei tempi stimati di occupazione della medesima
                matrice_incrocio[incrID][x].append([])
    # inserisco nell'array le auto presenti nella simulazione
    arrayAuto = costruzioneArray(arrayAuto)

    # trovo lunghezza e altezza auto in celle
    x_cella_in_m = abs(limiti_celle_X[0][1] - limiti_celle_X[0][0])
    y_cella_in_m = abs(limiti_celle_Y[0][1] - limiti_celle_Y[0][0])
    x_auto_in_m = traci.vehicle.getHeight("veh_0")
    y_auto_in_m = traci.vehicle.getLength("veh_0")
    x_auto_in_celle = float(x_auto_in_m) / float(x_cella_in_m)
    y_auto_in_celle = float(y_auto_in_m) / float(y_cella_in_m)
    # fino a quando tutte le auto da inserire hanno terminato la corsa
    while traci.simulation.getMinExpectedNumber() > 0:

        for incrNome in junctIDList:  # scorro la lista incroci
            incrID = junctIDList.index(incrNome)

            for auto in arrayAuto:  # scorro l'array delle auto ancora presenti nella simulazione

                auto_in_lista = True
                # vedo se l'auto corrente è tra le auto segnate per attraversare l'incrocio
                try:
                    presente = int(lista_arrivo[incrID].index(auto))
                except ValueError:
                    auto_in_lista = False
                pos = traci.vehicle.getPosition(auto)
                # se l'auto non è in lista allora guardo se sta entrando nelle vicinanze dell'incrocio
                if not auto_in_lista:
                    stop_temp = stop[incrID]

                    if (stop_temp[3] - 50 <= pos[0] <= stop_temp[1] + 50) and \
                            (stop_temp[2] - 50 <= pos[1] <= stop_temp[0] + 50):
                        # inserisco l'auto nella lista d'arrivo di quell'incrocio
                        lista_arrivo[incrID].append(auto)
                        # inserisco l'auto nella lista d'attesa di quell'incrocio
                        attesa[incrID].append(auto)
                        traci.vehicle.setMaxSpeed(auto, 6.944444)
                # se l'auto è in attesa e non è ferma, guardo se è vicina allo stop e fermo se l'incrocio è già occupato
                if auto in attesa[incrID] and auto not in ferme[incrID]:
                    # se l'incrocio ha 4 lati
                    if len(stop_temp) > 3:
                        if (stop_temp[3] - 13.5 <= pos[0] <= stop_temp[1] + 13.5) and \
                                (stop_temp[2] - 13.5 <= pos[1] <= stop_temp[0] + 13.5):
                            traci.vehicle.setDecel(auto, 1.92901)
                            traci.vehicle.setAccel(auto, 1.92901)
                            # salvo l'auto leader di quella lane
                            leader = traci.vehicle.getLeader(auto)
                            if leader:
                                # se il leader ha già iniziato ad attraversare l'incrocio non lo conto
                                if leader[0] not in attesa[incrID]:
                                    leader = None
                            # se non c'è il leader su quella lane
                            if not leader:
                                # controllo se l'auto non ha subito rallentamenti e la fermo in 16 m
                                if round(traci.vehicle.getSpeed(auto), 2) == round(traci.vehicle.getMaxSpeed(auto), 2):
                                    info = arrivoAuto(auto, passaggio[incrID], ferme[incrID], attesa[incrID],
                                                      matrice_incrocio[incrID], passaggio_cella[incrID],
                                                      traiettorie_matrice, stop[incrID], sec_sicurezza,
                                                      x_auto_in_celle, y_auto_in_celle)
                                    passaggio[incrID] = info[0]
                                    attesa[incrID] = info[1]
                                    ferme[incrID] = info[2]
                                    matrice_incrocio[incrID] = info[3]
                                    passaggio_cella[incrID] = info[4]
                                # se l'auto ha subito rallentamenti calcolo dalla sua velocità in quanti metri
                                # dall'incrocio si fermerebbe se la facessi rallentare subito, se si va a fermare in
                                # prossimità dell'incrocio allora avvio l'arresto del veicolo altrimenti aspetto
                                # il prossimo step e ricontrollo
                                else:
                                    dist_stop = 0
                                    v_auto = traci.vehicle.getSpeed(auto)
                                    decel = traci.vehicle.getDecel(auto)

                                    ang = traci.vehicle.getAngle(auto)

                                    if ang == 90:
                                        dist_stop = abs(stop_temp[3] - pos[0])
                                    if ang == 0:
                                        dist_stop = abs(stop_temp[2] - pos[1])
                                    if ang == 270:
                                        dist_stop = abs(stop_temp[1] - pos[0])
                                    if ang == 180:
                                        dist_stop = abs(stop_temp[0] - pos[1])

                                    dist_to_stop = (v_auto * v_auto) / (2 * decel)

                                    if dist_to_stop + 2 >= dist_stop:
                                        info = arrivoAuto(auto, passaggio[incrID], ferme[incrID], attesa[incrID],
                                                          matrice_incrocio[incrID], passaggio_cella[incrID],
                                                          traiettorie_matrice, stop[incrID], sec_sicurezza,
                                                          x_auto_in_celle, y_auto_in_celle)
                                        passaggio[incrID] = info[0]
                                        attesa[incrID] = info[1]
                                        ferme[incrID] = info[2]
                                        matrice_incrocio[incrID] = info[3]
                                        passaggio_cella[incrID] = info[4]
            # se ci sono auto che stanno attraversando l'incrocio guardo se la situazione dell'incrocio è cambiata
            if passaggio[incrID] is not None:
                # se l'auto è appena entrata nell'area dell'incrocio salvo la cella in cui si trova
                for x in passaggio_cella[incrID]:
                    rotta = traci.vehicle.getRouteID(x[0])
                    edges = traci.route.getEdges(rotta)
                    lane = getLaneFromEdges(node_ids, int(edges[0][1:3]), int(edges[1][4:6]))
                    if lane != 0:
                        # se l'auto non gira a destra
                        if x[1] is None and x[2] is None:
                            pos = traci.vehicle.getPosition(x[0])
                            if in_incrocio(pos, stop[incrID]):
                                IDvett = passaggio_cella[incrID].index(x)
                                passaggio_cella[incrID][IDvett] = get_cella_from_pos_auto(x[0], limiti_celle_X[incrID],
                                                                                          limiti_celle_Y[incrID])

                info = percorso_libero(passaggio[incrID], matrice_incrocio[incrID], passaggio_cella[incrID],
                                       limiti_celle_X[incrID], limiti_celle_Y[incrID], stop[incrID])
                passaggio[incrID] = info[0]
                matrice_incrocio[incrID] = info[1]
                passaggio_cella[incrID] = info[2]
                # se ci sono auto ferme, vedo se posso farne partire qualcuna
                if len(ferme[incrID]) > 0:

                    # scorro tra tutte le auto ferme e se una è compatibile con la matrice allora la faccio partire
                    for auto_ferma in ferme[incrID]:
                        if auto_ferma in ferme[incrID]:
                            if get_from_matrice_incrocio(auto_ferma, matrice_incrocio[incrID], traiettorie_matrice,
                                                         stop[incrID], sec_sicurezza, x_auto_in_celle,
                                                         y_auto_in_celle):
                                # vedo se il suo percorso è libero e nel caso la faccio partire
                                info = avantiAuto(auto_ferma, passaggio[incrID], attesa[incrID], ferme[incrID],
                                                  matrice_incrocio[incrID], passaggio_cella[incrID],
                                                  traiettorie_matrice, stop[incrID], x_auto_in_celle,
                                                  y_auto_in_celle)

                                passaggio[incrID] = info[0]
                                attesa[incrID] = info[1]
                                ferme[incrID] = info[2]
                                matrice_incrocio[incrID] = info[3]
                                passaggio_cella[incrID] = info[4]
            if int(step / step_incr) % 4 == 0:
                tempo_coda[incrID] = output_t_in_coda(arrayAuto, tempo_coda[incrID], step, attesa[incrID])
        # riaccelero i veicoli all'uscita dall'incrocio
        if int(step / step_incr) % 10 == 0:
            for auto_uscita in passaggio_precedente[incrID]:
                if auto_uscita not in passaggio[incrID]:
                    # da guardare
                    traci.vehicle.setMaxSpeed(auto_uscita[0], 13.888888)
                    traci.vehicle.setSpeed(auto_uscita[0], 13.888888)
                    traci.vehicle.setSpeedMode(auto_uscita[0], 7)
            passaggio_precedente[incrID] = passaggio[incrID][:]
        # ogni 8 step ne calcolo i valori delle metriche attuali
        if int(step / step_incr) % 8 == 0:
            # genero la stringhe di output
            file_rit = output(arrayAuto, consumo)
            f_s.append(file_rit[0])
            vm_s.append(file_rit[1])
            cm_s.append(file_rit[2])
            cx_s.append(file_rit[3])
            consumo = file_rit[4]
        # ogni 10 step pulisco la matrice da valori troppo vecchi
        if int(step / step_incr) % 10 == 0:
            matrice_incrocio = pulisci_matrice(matrice_incrocio, sec_sicurezza)
        # assegno colori alle auto
        coloreAuto(arrayAuto, junctIDList, attesa, ferme)

        step += step_incr
        # faccio avanzare la simulazione
        traci.simulationStep(step)
        # inserisco nell'array le auto presenti nella simulazione
        arrayAuto = costruzioneArray(arrayAuto)

    # ---------- genero l'output e lo ritorno ----------
    f_ret = 0.0
    vm_ret = 0.0
    cm_ret = 0.0
    cx_ret = 0.0
    consumo_totale_per_auto = dict()

    for i in f_s:
        f_ret += i
    for i in vm_s:
        vm_ret += i
    for i in cm_s:
        cm_ret += i
    for i in cx_s:
        cx_ret += i
    for auto_temp in consumo:
        consumo_totale = 0
        lista_consumi = consumo[auto_temp]
        for x in lista_consumi:
            consumo_totale += x
        consumo_totale_per_auto[auto_temp] = consumo_totale

    # calcolo del tempo massimo in coda e del tempo medio in coda
    diff_t_med_coda_incr = 0.0
    media_t_med_coda = 0.0
    max_t_coda = 0.0
    for incr in range(0, len(tempo_coda)):
        for auto in range(0, len(tempo_coda[incr])):
            t_in_coda = tempo_coda[incr][auto][1] - tempo_coda[incr][auto][0]
            if t_in_coda > max_t_coda:
                max_t_coda = t_in_coda
            diff_t_med_coda_incr += t_in_coda
        media_t_med_coda += round(float(diff_t_med_coda_incr) / float(len(tempo_coda[incr])), 4)
    media_t_med_coda = round(float(media_t_med_coda) / float(len(tempo_coda)), 4)

    # calcolo del consumo massimo e medio
    consumo_massimo = 0.0
    consumo_medio = 0.0
    for x in consumo_totale_per_auto:
        consumo_medio += consumo_totale_per_auto.get(x)
        if consumo_totale_per_auto.get(x) > consumo_massimo:
            consumo_massimo = consumo_totale_per_auto.get(x)
    consumo_medio = round(consumo_medio / float(n_auto), 4)
    consumo_massimo = round(consumo_massimo, 4)

    f_ret = round(float(f_ret) / float(len(f_s)), 4)
    vm_ret = round(float(vm_ret) / float(len(vm_s)), 4)
    cm_ret = round(float(cm_ret) / float(len(cm_s)), 4)
    cx_ret = round(float(cx_ret) / float(len(cx_s)), 4)

    print(f"TIME (s): {step}, REAL STEPS: {step / step_incr}")

    traci.close()
    return f_ret, vm_ret, cm_ret, cx_ret, step, max_t_coda, media_t_med_coda, consumo_massimo, consumo_medio


if __name__ == "__main__":
    n_porta_base = 5000
    celle_per_lato = 20
    auto = 50
    n_sims = 1
    gui = True
    secondi_di_sicurezza = 0.6
    tempo_generazione = 43.2
    traiettorie_matrice = Traiettorie.run(n_porta_base, False, celle_per_lato)
    run(n_porta_base + auto + n_sims, auto, tempo_generazione, gui, celle_per_lato, traiettorie_matrice,
        secondi_di_sicurezza)
