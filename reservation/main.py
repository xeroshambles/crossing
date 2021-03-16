from utils import *
from config import *
from inpout import redirect_output
from reservation.utils import *

import traci
from sumolib import miscutils



def intermediateRun(numberOfVehicles, schema,
                    totalTime, departed,
                    vehicles, tails_per_lane, main_step, mean_th_per_num, arrayAuto,
                    lista_arrivo, stop, attesa, ferme, passaggio, matrice_incrocio, passaggio_cella,
                    traiettorie_matrice, x_auto_in_celle, y_auto_in_celle, limiti_celle_X, limiti_celle_Y,
                    step_incr, passaggio_precedente, n_step, sec, incrID, isTransitioning, m, steps_per_main_step, main_step_duration):

    # inserisco nell'array le auto presenti nella simulazione
    if isTransitioning != "true" or "waiting":
        arrayAuto = costruzioneArray(arrayAuto)

    for auto in arrayAuto:  # scorro l'array delle auto ancora presenti nella simulazione


        auto_in_lista = True
        # vedo se l'auto corrente è tra le auto segnate per attraversare l'incrocio
        try:
            presente = int(lista_arrivo[incrID].index(auto))

        except ValueError:
            auto_in_lista = False
        pos = traci.vehicle.getPosition(auto)
        # se l'auto non è in lista allora guardo se sta entrando nelle vicinanze dell'incrocio
        stop_temp = stop[incrID]
        if not auto_in_lista:
            #traci.vehicle.setSpeedMode(auto, 23)

            if (stop_temp[3] - 50 <= pos[0] <= stop_temp[1] + 50) and \
                    (stop_temp[2] - 50 <= pos[1] <= stop_temp[0] + 50):
                # inserisco l'auto nella lista d'arrivo di quell'incrocio
                print(auto)
                if auto == "idV42":
                    print("HALP")
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
                        if auto_ferma == "idV42":
                            print(f"presente@{totalTime}, auto_ferma\n")
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

    for auto_uscita in passaggio_precedente[incrID]:
        if auto_uscita not in passaggio[incrID]:
            if auto_uscita == "idV42":
                print(f"presente@{totalTime}, auto_uscita\n")
            traci.vehicle.setMaxSpeed(auto_uscita[0], 13.888888)
            traci.vehicle.setSpeed(auto_uscita[0], 13.888888)
            traci.vehicle.setSpeedMode(auto_uscita[0], 7)
    passaggio_precedente[incrID] = passaggio[incrID][:]
    # ogni 10 step pulisco la matrice da valori troppo vecchi
    if totalTime % round(10 * step_incr, 2) == 0:
        matrice_incrocio = pulisci_matrice(matrice_incrocio, secondi_di_sicurezza)

    if totalTime % 1 == 0:
        vehicles, tails_per_lane = checkVehiclesAdaptive(vehicles, tails_per_lane, int(totalTime), schema, main_step_duration)

    return mean_th_per_num, main_step, totalTime, departed, tails_per_lane,\
           arrayAuto, lista_arrivo, stop, attesa, ferme, passaggio, matrice_incrocio, passaggio_cella, \
           traiettorie_matrice, x_auto_in_celle, y_auto_in_celle, passaggio_precedente, n_step

def run(numberOfVehicles, schema, sumoCmd, path, index, queue, seed,
        celle_per_lato, traiettorie_matrice, secondi_di_sicurezza):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    redirect_output(path, index, True)

    traci.start(sumoCmd, port=port, numRetries=200)

    vehicles = {}  # dizionario contente gli id dei veicoli
    departed = 0  # numero di veicoli partiti nella simulazione e considerati nel calcolo delle misure
    totalTime = 0.00  # tempo totale di simulazione
    step_incr = 0.05  # incremento del numero di step della simulazione
    #sec = 1 / step_incr  # numero che indica ogni quanti sotto step devo calcolare le misure
    tails_per_lane = {}  # dizionario contenente le lunghezze delle code per ogni lane ad ogni step

    mean_th_per_num = [-1 for el in numberOfVehicles]
    intermediate_departed = 0

    for lane in lanes:
        # calcolo la lunghezza delle code e il throughput solo per le lane entranti
        if lane[4:6] == '07':
            tails_per_lane[lane] = []

    """Inizializzo i veicoli assegnadogli una route generata casualmente e, in caso di schema di colori 
    non significativo,dandogli un colore diverso per distinguerli meglio all'interno della simulazione"""

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
    x_auto_in_m = traci.vehicle.getHeight("idV0")
    y_auto_in_m = traci.vehicle.getLength("idV0")
    x_auto_in_celle = float(x_auto_in_m) / float(x_cella_in_m)
    y_auto_in_celle = float(y_auto_in_m) / float(y_cella_in_m)
    # fino a quando tutte le auto da inserire hanno terminato la corsa

    n_step = 0

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        incrID = 0
        totalTime = round(totalTime + step_incr, 2)
        n_step += 1
        # faccio avanzare la simulazione
        traci.simulationStep(totalTime)
        departed += traci.simulation.getDepartedNumber()
        intermediate_departed += traci.simulation.getDepartedNumber()
        # inserisco nell'array le auto presenti nella simulazione
        arrayAuto = costruzioneArray(arrayAuto)

        for auto in arrayAuto:  # scorro l'array delle auto ancora presenti nella simulazione

            auto_in_lista = True
            # vedo se l'auto corrente è tra le auto segnate per attraversare l'incrocio
            try:
                presente = int(lista_arrivo[incrID].index(auto))
            except ValueError:
                auto_in_lista = False
            pos = traci.vehicle.getPosition(auto)
            stop_temp = stop[incrID]
            # se l'auto non è in lista allora guardo se sta entrando nelle vicinanze dell'incrocio
            if not auto_in_lista:

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

        for auto_uscita in passaggio_precedente[incrID]:
            if auto_uscita not in passaggio[incrID]:
                if auto_uscita == "idV42":
                    print(f"presente@{totalTime}, auto_uscita\n")
                traci.vehicle.setMaxSpeed(auto_uscita[0], 13.888888)
                traci.vehicle.setSpeed(auto_uscita[0], 13.888888)
                traci.vehicle.setSpeedMode(auto_uscita[0], 7)
        passaggio_precedente[incrID] = passaggio[incrID][:]
        # ogni 10 step pulisco la matrice da valori troppo vecchi
        if totalTime % round(10 * step_incr, 2) == 0:
            matrice_incrocio = pulisci_matrice(matrice_incrocio, secondi_di_sicurezza)



        if totalTime % 1 == 0:
            vehicles, tails_per_lane = checkVehicles(vehicles, tails_per_lane, int(totalTime), schema)

            """
            Salvo i risultati intermedi se si conclude un main step
            
            mean_th_per_num, main_step, intermediate_departed = checkIfMainStep(totalTime, stepsSpawn,
                                                                                numberOfVehicles, main_step, vehicles,
                                                                                intermediate_departed, mean_th_per_num)
            """



    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime, \
    meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput = saveResults(vehicles, departed,
                                                                                                   tails_per_lane)

    traci.close()

    redirect_output(path, index, False)

    queue.put([int(totalTime), meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, stDevTailTime, maxTailTime,
               meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, stoppedVehicles, throughput, mean_th_per_num])
