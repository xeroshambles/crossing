# SEMPLIFICAZIONI:
# - incrocio a forma di "+" e strade ad angoli multipli di 90 gradi
# - ricordarsi di modificare il tipo di junction in netedit, in unregulated o l'ultimo

import os
import sys
import traci

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Dichiarare la variabile d'ambiente 'SUMO_HOME'")

from sumolib import checkBinary  # noqa


def getLaneFromEdges(node_ids, start, end):
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


def generaVeicoli():
    """Genero veicoli per ogni route"""

    r_depart = -9
    auto_ogni = 10
    node_ids = [2, 8, 12, 6]
    junction_id = 7

    generateRoute(node_ids, junction_id)

    for i in range(0, 12):
        edges = traci.route.getEdges(f'route_{i}')
        lane = getLaneFromEdges(node_ids, int(edges[0][1:3]), int(edges[1][4:6]))
        r_depart += auto_ogni
        if lane == 0:
            continue
        else:
            id_veh = "veh_" + str(i)
            traci.vehicle.add(id_veh, f'route_{i}', depart=str(r_depart), departLane=lane, departSpeed="6.944444")
            traci.vehicle.setMaxSpeed(id_veh, 6.944444)
            traci.vehicle.setSpeedMode(id_veh, 0)


def stopXY(shape_temp):
    """Calcolo gli estremi dell'incrocio, dove sono presenti gli stop"""

    stop_temp = []

    for count in range(0, len(shape_temp) - 1):
        if shape_temp[count][0] == shape_temp[count + 1][0]:
            stop_temp.append(shape_temp[count][0])
        elif shape_temp[count][1] == shape_temp[count + 1][1]:
            stop_temp.append(shape_temp[count][1])

    return stop_temp


def limiti_celle(estremi_incrocio, celle_per_lato):
    """Calcolo i metri all'interno dell'incrocio di ogni cella della matrice definisco i vettori"""

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


def costruzioneArray(arrayAuto_temp):
    """Costruisco l'array composto dal nome delle auto presenti nella simulazione"""

    loadedIDList = traci.simulation.getDepartedIDList()  # carica nell'array le auto partite

    for id_auto in loadedIDList:
        if id_auto not in arrayAuto_temp:
            arrayAuto_temp.append(id_auto)
    arrivedIDList = traci.simulation.getArrivedIDList()  # elimina nell'array le auto arrivate

    for id_auto in arrivedIDList:
        if id_auto in arrayAuto_temp:
            arrayAuto_temp.pop(arrayAuto_temp.index(id_auto))

    return arrayAuto_temp


def run(gui, celle_per_lato):
    """Main che date tutte le traiettorie possibili all'interno dell'incrocio calcola la matrice di celle"""

    if gui:
        sumoBinary = checkBinary('sumo-gui')
    else:
        sumoBinary = checkBinary('sumo')

    conf = os.path.join(os.path.split(os.path.dirname(__file__))[0], "intersection.sumocfg")

    sumoCmd = [sumoBinary, "-c", conf, "--time-to-teleport", "-1", "-Q", "--step-length", "0.001"]

    traci.start(sumoCmd, numRetries=50)

    # -------- dichiarazione variabili --------

    step = 0.000
    step_incr = 0.036
    generaVeicoli()  # genero veicoli

    # istanzio le matrici [nome_incrocio, variabile]
    lista_arrivo = []  # auto entrate nelle vicinanze dell'incrocio, non si resetta
    lista_uscita = []  # auto uscite dall'incrocio, non si resetta
    stop = []  # di quanto si distanzia lo stop dal centro incrocio [dx, sotto, sx, sopra]
    centerJunctID = []  # coordinate (x,y) del centro di un incrocio
    arrayAuto = []  # contiene la lista di auto presenti nella simulazione
    limiti_celle_X = []  # utile per verificare l'appartenenza ad una cella all'interno della matrice dell'incrocio
    limiti_celle_Y = []  # utile per verificare l'appartenenza ad una cella all'interno della matrice dell'incrocio
    time_entrata_in_incrocio = []  # time step in cui un'auto di una determinata route entra nell'incrocio
    lista_occupazione_celle = []  # [["routeX", [ [Y1, X1, metri], [Y2, X2, metri], ...] ], ["routeY", [...]], ...]
    metri_to_cella = []  # tutti i metri calcolati quando l'auto e' campionata sulla stessa cella
    ang_in_cella = []  # angoli rilevati quando l'auto e' campionata sulla stessa cella

    # -------- trovo la lista degli incroci --------

    junctIDList_temp = []  # lista degli incroci
    junctIDList_tupla = traci.junction.getIDList()  # creo la lista delle junction (creo l'array dalla tupla)

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

    for incrNome in junctIDList:  # scorro la lista incroci
        # popolo vettori e matrici inserendo le righe
        lista_arrivo.append([])
        lista_uscita.append([])
        centerJunctID.append(traci.junction.getPosition(incrNome))  # posizione del centro dell'incrocio
        shape = traci.junction.getShape(incrNome)  # forma dell'incrocio
        stop.append(stopXY(shape))  # estremi dell'incrocio, dove sono presenti gli stop
        # popolo i vettori limiti_celle_X e limiti_celle_Y
        limiti = limiti_celle(stopXY(shape), celle_per_lato)
        limiti_celle_X.append(limiti[0])
        limiti_celle_Y.append(limiti[1])

    arrayAuto = costruzioneArray(arrayAuto)  # inserisco nell'array le auto presenti nella simulazione

    while traci.simulation.getMinExpectedNumber() > 0:  # fino a quando tutte le auto hanno terminato la corsa

        for incrNome in junctIDList:  # scorro la lista incroci
            incrID = junctIDList.index(incrNome)

            for auto in arrayAuto:  # scorro l'array delle auto ancora presenti nella simulazione
                # se l'auto è all'incrocio
                if in_incrocio(traci.vehicle.getPosition(auto), stop[incrID]):
                    index = -1
                    route = traci.vehicle.getRouteID(auto)
                    if len(lista_occupazione_celle):

                        for x in lista_occupazione_celle:
                            # se ho già registrato le celle per quella route
                            if x[0] == route:
                                index = lista_occupazione_celle.index(x)
                                break
                        # se non ho ancora registrato le celle per quella route
                        if index == -1:
                            vett = [route, []]
                            lista_occupazione_celle.append(vett)
                            index = lista_occupazione_celle.index(vett)
                            time_entrata_in_incrocio.append([route, step])
                    else:
                        vett = [route, []]
                        lista_occupazione_celle.append(vett)
                        index = lista_occupazione_celle.index(vett)
                        time_entrata_in_incrocio.append([route, step])

                    cella = get_cella_from_pos_auto(auto, limiti_celle_X[incrID], limiti_celle_Y[incrID])
                    pos_attuale_X = cella[1]
                    pos_attuale_Y = cella[2]
                    # calcolo il tempo tra l'entrata dell'auto all'incrocio e l'arrivo in quella cella
                    index2 = 0

                    for x in time_entrata_in_incrocio:
                        if x[0] == route:
                            index2 = time_entrata_in_incrocio.index(x)
                    time_diff = step - time_entrata_in_incrocio[index2][1]
                    # calcolo i metri tra l'entrata dell'auto all'incrocio e l'arrivo in quella cella
                    metri = float(time_diff) * traci.vehicle.getMaxSpeed(auto)
                    # rilevo l'angolo dell'auto
                    ang = traci.vehicle.getAngle(auto)
                    trovato = -1
                    m_metri = 0
                    m_ang = 0
                    # controllo se l'auto è già passata in quella cella
                    for x in lista_occupazione_celle[index][1]:
                        if x[0] == pos_attuale_Y and x[1] == pos_attuale_X:
                            trovato = lista_occupazione_celle[index][1].index(x)
                            metri_to_cella.append(metri)
                            ang_in_cella.append(ang)
                        if trovato > -1:
                            break
                    # se l'auto è già passata calcolo la distanza e l'angolo medi nella cella
                    if trovato > -1:
                        for x in metri_to_cella:
                            m_metri += x
                        for x in ang_in_cella:
                            m_ang += x
                        m_metri = float(m_metri) / float(len(metri_to_cella))
                        m_ang = float(m_ang) / float(len(ang_in_cella))
                        lista_occupazione_celle[index][1][trovato][2] = m_metri
                        lista_occupazione_celle[index][1][trovato][3] = round(m_ang, 3)
                    # l'auto non è mai passata
                    else:
                        metri_to_cella = [metri]
                        ang_in_cella = [round(ang, 3)]
                        lista_occupazione_celle[index][1].append([pos_attuale_Y, pos_attuale_X, metri, round(ang, 3)])
        step += step_incr
        traci.simulationStep(step)  # faccio avanzare la simulazione
        arrayAuto = costruzioneArray(arrayAuto)  # inserisco nell'array le auto presenti nella simulazione
    traci.close()
    return lista_occupazione_celle
