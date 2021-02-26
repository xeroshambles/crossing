import sys
import os
from math import sqrt
from utils import *
from config import *
from reservation.utils import *

import traci
from sumolib import miscutils


def run(numberOfVehicles, schema, sumoCmd, celle_per_lato, traiettorie_matrice, secondi_di_sicurezza, path, index,
        queue, seed):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    dir = os.path.join(path, 'terminals')

    if not os.path.exists(dir):
        try:
            os.mkdir(dir)
        except OSError:
            print(f"\nCreazione della cartella {dir} fallita...")
            sys.exit(-1)

    if output_redirection:

        origin_stdout = sys.stdout

        origin_stderr = sys.stderr

        sys.stdout = open(os.path.join(dir, f"{index}.txt"), "w")

        sys.stderr = open(os.path.join(dir, f"{index}.txt"), "w")

    traci.start(sumoCmd, port=port, numRetries=200)

    vehicles = {}  # dizionario contente gli id dei veicoli
    departed = 0  # numero di veicoli partiti nella simulazione e considerati nel calcolo delle misure
    totalTime = 0.000  # tempo totale di simulazione
    step_incr = 0.050  # incremento del numero di step della simulazione
    sec = 1 / step_incr
    headTimes = []  # lista dei tempi passati in testa per ogni veicolo
    varHeadTime = 0  # varianza rispetto al tempo passato in testa
    tailTimes = []  # lista dei tempi in coda per ogni veicolo
    varTailTime = 0  # varianza rispetto al tempo passato in coda
    meanSpeeds = []  # medie delle velocità assunte dai veicoli ad ogni step
    varSpeed = 0  # varianza rispetto alla velocità dei veicoli
    nStoppedVehicles = []  # lista che dice se i veicoli si sono fermati all'incrocio o no
    meanTailLength = []  # medie delle lunghezze delle code rilevate sulle lane entranti ad ogni step
    varTail = 0  # varianza rispetto alla coda
    maxTail = -1  # coda massima rilevata su tutte le lane entranti
    tails_per_lane = {}  # dizionario contenente le lunghezze delle code per ogni lane ad ogni step
    junction_shape = traci.junction.getShape("n" + str(junction_id))

    mean_th_per_num = [-1 for el in numberOfVehicles]
    main_step = 0
    intermediate_departed = 0

    for lane in lanes:
        # calcolo la lunghezza delle code e il throughput solo per le lane entranti
        if lane[4:6] == '07':
            tails_per_lane[lane] = []

    """Con il seguente ciclo inizializzo i veicoli assegnadogli una route legale generata casualmente e, in caso di 
    schema di colori non significativo,dandogli un colore diverso per distinguerli meglio all'interno della 
    simulazione"""

    vehicles = generateVehicles(stepsSpawn, numberOfVehicles, vehicles, seed, junction_id, node_ids)

    if schema in ['n', 'N']:
        colorVehicles(sum(numberOfVehicles))

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
    x_auto_in_m = traci.vehicle.getHeight("0")
    y_auto_in_m = traci.vehicle.getLength("0")
    x_auto_in_celle = float(x_auto_in_m) / float(x_cella_in_m)
    y_auto_in_celle = float(y_auto_in_m) / float(y_cella_in_m)
    # fino a quando tutte le auto da inserire hanno terminato la corsa

    n_step = 0

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        incrID = 0

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
                                                  traiettorie_matrice, stop[incrID], secondi_di_sicurezza,
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
                                                      traiettorie_matrice, stop[incrID], secondi_di_sicurezza,
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
                lane = getLaneIndexFromEdges(int(edges[0][1:3]), int(edges[1][4:6]), node_ids)
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
                                                     stop[incrID], secondi_di_sicurezza, x_auto_in_celle,
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
        # riaccelero i veicoli all'uscita dall'incrocio
        if int(totalTime / step_incr) % 10 == 0:
            for auto_uscita in passaggio_precedente[incrID]:
                if auto_uscita not in passaggio[incrID]:
                    traci.vehicle.setMaxSpeed(auto_uscita[0], 13.888888)
                    traci.vehicle.setSpeed(auto_uscita[0], 13.888888)
                    traci.vehicle.setSpeedMode(auto_uscita[0], 7)
            passaggio_precedente[incrID] = passaggio[incrID][:]
        # ogni 10 step pulisco la matrice da valori troppo vecchi
        if int(totalTime / step_incr) % 10 == 0:
            matrice_incrocio = pulisci_matrice(matrice_incrocio, secondi_di_sicurezza)

        totalTime += step_incr
        n_step += 1
        # faccio avanzare la simulazione
        traci.simulationStep(totalTime)
        departed += traci.simulation.getDepartedNumber()
        intermediate_departed += traci.simulation.getDepartedNumber()
        # inserisco nell'array le auto presenti nella simulazione
        arrayAuto = costruzioneArray(arrayAuto)

        if n_step % sec == 0:
            vehs_loaded = traci.vehicle.getIDList()
            for lane in tails_per_lane:
                tails_per_lane[lane].append(0)
            # loop per tutti i veicoli
            for veh in vehs_loaded:
                veh_current_lane = traci.vehicle.getLaneID(veh)

                # controllo se il veicolo è in una lane entrante
                if veh_current_lane[4:6] == '07':
                    vehicles[veh]['startingLane'] = veh_current_lane
                    spawn_distance = traci.vehicle.getDistance(veh)
                    distance = getDistanceFromLaneEnd(spawn_distance, traci.lane.getLength(veh_current_lane),
                                                      junction_shape)
                    if distance < 15:
                        vehicles[veh]['speeds'].append(traci.vehicle.getSpeed(veh))
                    veh_length = traci.vehicle.getLength(veh)
                    check = veh_length / 2 + 0.2
                    leader = traci.vehicle.getLeader(veh)
                    if traci.vehicle.getSpeed(veh) <= 1:
                        # verifico se il veicolo è in testa
                        if check >= distance and ((leader and leader[1] < 0) or not leader):
                            vehicles[veh]['hasStopped'] = 1
                            tails_per_lane[veh_current_lane][int(n_step / sec) - 1] += 1
                            vehicles[veh]['headTime'] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                            continue
                        # verifico se il veicolo è in coda
                        if leader and leader[1] <= 0.5 and \
                                vehicles[leader[0]]['startingLane'] == veh_current_lane:
                            vehicles[veh]['hasStopped'] = 1
                            tails_per_lane[veh_current_lane][int(n_step / sec) - 1] += 1
                            vehicles[veh]['tailTime'] += 1
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                            continue
                    else:
                        if schema in ['s', 'S']:
                            traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

                # controllo se il veicolo è all'interno della junction
                if veh_current_lane[1:3] == 'n7':
                    vehicles[veh]['speeds'].append(traci.vehicle.getSpeed(veh))
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

                # controllo se il veicolo è in una lane uscente
                if veh_current_lane[1:3] == '07':
                    if vehicles[veh]['hasPassed'] == 0:
                        vehicles[veh]['hasPassed'] = 1
                    if schema in ['s', 'S']:
                        traci.vehicle.setColor(veh, (0, 255, 0))  # verde

            """Salvo i risultati intermedi se si conclude un main step"""

            mean_th_per_num, main_step, intermediate_departed = checkIfMainStep(round(totalTime), stepsSpawn, numberOfVehicles,
                                                                                main_step, vehicles,
                                                                                intermediate_departed, mean_th_per_num)
    """Salvo tutti i risultati della simulazione e li ritorno"""

    passed = 0

    for veh in vehicles:
        if int(veh) < departed:
            headTimes.append(vehicles[veh]['headTime'])
            tailTimes.append(vehicles[veh]['tailTime'])
            if len(vehicles[veh]['speeds']) > 0:
                meanSpeeds.append(sum(vehicles[veh]['speeds']) / len(vehicles[veh]['speeds']))
            nStoppedVehicles.append(vehicles[veh]['hasStopped'])
            passed += vehicles[veh]['hasPassed']

    meanHeadTime = sum(headTimes) / len(headTimes)
    for headTime in headTimes:
        varHeadTime += (headTime - meanHeadTime) ** 2
    varHeadTime /= len(headTimes)

    meanTailTime = sum(tailTimes) / len(tailTimes)
    for tailTime in tailTimes:
        varTailTime += (tailTime - meanTailTime) ** 2
    varTailTime /= len(tailTimes)

    if len(meanSpeeds) > 0:
        meanSpeed = sum(meanSpeeds) / len(meanSpeeds)
        for speed in meanSpeeds:
            varSpeed += (speed - meanSpeed) ** 2
        varSpeed /= len(meanSpeeds)
    else:
        meanSpeed = 0
        varSpeed = 0

    for lane in tails_per_lane:
        meanTailLength.append(sum(tails_per_lane[lane]) / len(tails_per_lane[lane]))
        lane_max = max(tails_per_lane[lane])
        if lane_max > maxTail:
            maxTail = lane_max

    meanTail = sum(meanTailLength) / len(meanTailLength)
    for tail in meanTailLength:
        varTail += (tail - meanTail) ** 2
    varTail /= len(meanTailLength)

    throughput = passed / departed

    traci.close()

    if output_redirection:

        sys.stdout = origin_stdout

        sys.stderr = origin_stderr

    queue.put([int(totalTime), meanHeadTime, sqrt(varHeadTime), max(headTimes), meanTailTime, sqrt(varTailTime),
               max(tailTimes), meanSpeed, sqrt(varSpeed), meanTail, sqrt(varTail), maxTail, sum(nStoppedVehicles),
               throughput, mean_th_per_num])
