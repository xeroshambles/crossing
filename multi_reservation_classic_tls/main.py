import os
import sys
from math import sqrt
from config_multi import *
from utils import *
from multi_reservation_classic_tls.utils import *
from multi_reservation_classic_tls.trafficElements.junction import ThreeWayJunction, FourWayJunction
from multi_reservation_classic_tls.trafficElements.vehicle import Vehicle

import traci
from sumolib import miscutils


def generateVehicles(numberOfSteps, numberOfVehicles, vehicles, routeMode, instantPay, seed):
    """Genero veicoli per ogni route possibile nel caso di incrocio multiplo"""

    c = 0
    t = 0
    depart = 0
    auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]

    for i in range(0, sum(numberOfVehicles)):
        if t < numberOfVehicles[c]:
            t += 1
        else:
            t = 0
            c += 1
            auto_every = (numberOfSteps / len(numberOfVehicles)) / numberOfVehicles[c]
        depart += auto_every
        idV = f'idV{i}'
        vehicles[idV] = Vehicle(idV, seed, iP=instantPay)
        base_route = vehicles[idV].generateRoute(static=routeMode)
        route = traci.simulation.findRoute(base_route[0], base_route[1])
        traci.route.add(f'route_{i}', route.edges)
        vehicles[idV].setEdgeObjective(base_route[1])
        traci.vehicle.add(idV, f'route_{i}', depart=depart)
        traci.vehicle.setMaxSpeed(idV, 9.72)


def run(numberOfSteps, numberOfVehicles, schema, sumoCmd, celle_per_lato, traiettorie_matrice, secondi_di_sicurezza,
        path, index, queue, seed):
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

    traci.start(sumoCmd, port=port, numRetries=1000)

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    departed = 0
    departed_vehicles = []
    step = 0  # tempo totale di simulazione
    step_incr = 0.050
    sec = 1 / step_incr
    travelTimes = []  # lista dei tempi di percorrenza medi per ogni veicolo
    varTravelTime = 0  # varianza rispetto al tempo di percorrenza
    headTimes = []  # lista dei tempi passati in testa medi per ogni veicolo
    varHeadTime = 0  # varianza rispetto al tempo passato in testa
    tailTimes = []  # lista dei tempi in coda medi per ogni veicolo
    varTailTime = 0  # varianza rispetto al tempo passato in coda
    meanSpeeds = []  # lista delle velocità medie assunte dai veicoli nei pressi dell'incrocio
    varSpeed = 0  # varianza rispetto alla velocità dei veicoli
    meanTailLength = []  # lista delle lunghezze medie delle code rilevate sulle lane entranti
    varTail = 0  # varianza rispetto alla coda
    maxTail = -1  # coda massima rilevata su tutte le lane entranti

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
    rallentate = []  # lista di auto rallentate in prossimità dell'incrocio
    passaggio_precedente = []  # salvo l'ultima situazione di auto in passaggio per rilasciarle all'uscita

    """Con il seguente ciclo inizializzo i veicoli assegnadogli una route legale generata casualmente e, in caso di 
        schema di colori non significativo,dandogli un colore diverso per distinguerli meglio all'interno della 
        simulazione"""

    generateVehicles(stepsSpawn, numberOfVehicles, vehicles, routeMode, instantPay, seed)

    if schema in ['n', 'N']:
        colorVehicles(numberOfVehicles)

    # -------- trovo lista degli incroci --------

    junctions = []  # dovrà contenere tutti gli incroci
    for i in range(1, 26):
        if i in two_way_junctions_ids:
            # junctions.append(TwoWayJunction(i))
            pass
        elif i in three_way_junctions_ids:
            junctions.append(ThreeWayJunction(i, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                                              groupDimension=dimensionOfGroups))
            pass
        else:
            junctions.append(FourWayJunction(i, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                                             groupDimension=dimensionOfGroups))

    junctIDList = [junction for junction in junctions if junction.nID in four_way_junctions_ids]

    for junction in junctIDList:  # scorro lista incroci
        incrID = junctIDList.index(junction)  # popolo vettori e matrici inserendo le righe
        attesa.append([])
        lista_arrivo.append([])
        lista_uscita.append([])
        ferme.append([])
        passaggio.append([])
        rallentate.append([])
        passaggio_cella.insert(incrID, [])
        passaggio_precedente.append([])

        centerJunctID.append(traci.junction.getPosition('n' + str(junction.nID)))  # posizione del centro dell'incrocio

        shape = traci.junction.getShape('n' + str(junction.nID))  # forma dell'incrocio
        stop.append(stopXY(shape))  # estremi dell'incrocio, dove sono presenti gli stop

        # popolo i vettori limiti_celle_X e limiti_celle_Y
        limiti = limiti_celle(stopXY(shape), celle_per_lato)
        limiti_celle_X.append(limiti[0])
        limiti_celle_Y.append(limiti[1])
        # popolo il vettore per il calcolo del tempo medio in coda
        tempo_coda.insert(incrID, [])
        for i in range(0, sum(numberOfVehicles)):
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
    x_auto_in_m = traci.vehicle.getHeight("idV0")
    y_auto_in_m = traci.vehicle.getLength("idV0")
    x_auto_in_celle = float(x_auto_in_m) / float(x_cella_in_m)
    y_auto_in_celle = float(y_auto_in_m) / float(y_cella_in_m)

    """Di seguito il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    n_step = 0

    while traci.simulation.getMinExpectedNumber() > 0 and step < numberOfSteps:
        departed += traci.simulation.getDepartedNumber()
        departed_vehicles += traci.simulation.getDepartedIDList()

        # controllo se i veicoli hanno raggiunto l'obbiettivo e, nel caso, riassegno una nuova route
        for i in range(0, sum(numberOfVehicles)):
            vehicles[f'idV{i}'].travelTimes[vehicles[f'idV{i}'].index] += 1
            vehicles[f'idV{i}'].changeTarget(staticRoutes=routeMode)

        for junction in junctIDList:  # scorro la lista incroci
            incrID = junctIDList.index(junction)

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
                    if rotta != "route_2" and rotta != "route_4" and rotta != "route_6" and rotta != "route_11":
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
        if int(step / step_incr) % 10 == 0:
            for auto_uscita in passaggio_precedente[incrID]:
                if auto_uscita not in passaggio[incrID]:
                    traci.vehicle.setMaxSpeed(auto_uscita[0], 13.888888)
                    traci.vehicle.setSpeed(auto_uscita[0], 13.888888)
                    traci.vehicle.setSpeedMode(auto_uscita[0], 7)
            passaggio_precedente[incrID] = passaggio[incrID][:]
        # ogni 10 step pulisco la matrice da valori troppo vecchi
        if int(step / step_incr) % 10 == 0:
            matrice_incrocio = pulisci_matrice(matrice_incrocio, secondi_di_sicurezza)

        # inserisco nell'array le auto presenti nella simulazione
        arrayAuto = costruzioneArray(arrayAuto)

        step += step_incr
        # faccio avanzare la simulazione
        traci.simulationStep(step)

        n_step += 1

        if n_step % sec == 0:

            for junction in junctions:

                junction.departed.append(0)
                junction.arrived.append(0)

                vehs_in_junction = junction.getActualVehicles(departed_vehicles)
                for lane in junction.tails_per_lane:
                    junction.tails_per_lane[lane].append(0)
                # loop per tutti i veicoli
                for veh in vehs_in_junction:
                    veh_current_lane = traci.vehicle.getLaneID(veh)

                    # controllo se il veicolo è in una lane entrante
                    if veh_current_lane in junction.incomingLanes:
                        vehicles[veh].startingLane = veh_current_lane
                        if veh not in junction.vehiclesEntering:
                            junction.vehiclesEntering.append(veh)
                            junction.departed[int(n_step / sec) - 1] += 1
                        spawn_distance = traci.vehicle.getDistance(veh)
                        distance = getDistanceFromLaneEnd(spawn_distance, traci.lane.getLength(veh_current_lane),
                                                          junction.junction_shape)
                        if distance < 15:
                            vehicles[veh].speeds[vehicles[veh].index].append(traci.vehicle.getSpeed(veh))
                        veh_length = traci.vehicle.getLength(veh)
                        check = veh_length / 2 + 0.2
                        leader = traci.vehicle.getLeader(veh)
                        if traci.vehicle.getSpeed(veh) <= 1:
                            # verifico se il veicolo è in testa
                            if check >= distance and ((leader and leader[1] < 0) or not leader):
                                junction.tails_per_lane[veh_current_lane][int(n_step / sec) - 1] += 1
                                vehicles[veh].headTimes[vehicles[veh].index] += 1
                                if schema in ['s', 'S']:
                                    traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                                continue
                            # verifico se il veicolo è in coda
                            if leader and leader[1] <= 0.5 and vehicles[leader[0]].startingLane == veh_current_lane:
                                junction.tails_per_lane[veh_current_lane][int(n_step / sec) - 1] += 1
                                vehicles[veh].tailTimes[vehicles[veh].index] += 1
                                if schema in ['s', 'S']:
                                    traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                                continue
                        else:
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

                    # controllo se il veicolo è all'interno della junction
                    if veh_current_lane in junction.crossingLanes:
                        leader = traci.vehicle.getLeader(veh)
                        leader_lane = ''
                        if leader:
                            leader_lane = traci.vehicle.getLaneID(leader[0])
                        vehicles[veh].speeds[vehicles[veh].index].append(traci.vehicle.getSpeed(veh))
                        if traci.vehicle.getSpeed(veh) <= 1:
                            # verifico se il veicolo è in testa
                            if (leader and leader_lane != veh_current_lane) or not leader:
                                junction.tails_per_lane[vehicles[veh].startingLane][int(n_step / sec) - 1] += 1
                                vehicles[veh].headTimes[vehicles[veh].index] += 1
                                if schema in ['s', 'S']:
                                    traci.vehicle.setColor(veh, (0, 0, 255))  # blu
                                continue
                            # verifico se il veicolo è in coda
                            if leader and leader[1] <= 0.5 and leader_lane == veh_current_lane:
                                junction.tails_per_lane[vehicles[veh].startingLane][int(n_step / sec) - 1] += 1
                                vehicles[veh].tailTimes[vehicles[veh].index] += 1
                                if schema in ['s', 'S']:
                                    traci.vehicle.setColor(veh, (255, 0, 0))  # rosso
                                continue
                        else:
                            if schema in ['s', 'S']:
                                traci.vehicle.setColor(veh, (255, 255, 0))  # giallo

                    # controllo se il veicolo è in una lane uscente
                    if veh_current_lane in junction.outgoingLanes:
                        if veh in junction.vehiclesEntering:
                            vehicles[veh].startingLane = ''
                            junction.vehiclesEntering.remove(veh)
                            junction.arrived[int(n_step / sec) - 1] += 1

    """Salvo tutti i risultati della simulazione e li ritorno"""

    for veh in vehicles:
        if int(veh[-1]) < departed:
            travelTimes.append(sum(vehicles[veh].travelTimes) / len(vehicles[veh].travelTimes))
            headTimes.append(sum(vehicles[veh].headTimes) / len(vehicles[veh].headTimes))
            tailTimes.append(sum(vehicles[veh].tailTimes) / len(vehicles[veh].tailTimes))
            sps = []
            for speeds in vehicles[veh].speeds:
                if len(speeds) > 0:
                    sps.append(sum(speeds) / len(speeds))
            if len(sps) > 0:
                meanSpeeds.append(sum(sps) / len(sps))

    meanTravelTime = sum(travelTimes) / len(travelTimes)
    for travelTime in travelTimes:
        varTravelTime += (travelTime - meanTravelTime) ** 2
    stDevTravelTime = sqrt(varTravelTime / len(travelTimes))

    meanHeadTime = sum(headTimes) / len(headTimes)
    for headTime in headTimes:
        varHeadTime += (headTime - meanHeadTime) ** 2
    stDevHeadTime = sqrt(varHeadTime / len(headTimes))

    meanTailTime = sum(tailTimes) / len(tailTimes)
    for tailTime in tailTimes:
        varTailTime += (tailTime - meanTailTime) ** 2
    stDevTailTime = sqrt(varTailTime / len(tailTimes))

    if len(meanSpeeds) > 0:
        meanSpeed = sum(meanSpeeds) / len(meanSpeeds)
        for speed in meanSpeeds:
            varSpeed += (speed - meanSpeed) ** 2
        stDevSpeed = sqrt(varSpeed / len(meanSpeeds))
    else:
        meanSpeed = 0
        stDevSpeed = 0

    meanTails = []
    stDevTails = []
    maxTails = []
    meanThroughput = []

    for junction in junctions:
        if junction.arrived == 0 and junction.departed == 0:
            meanThroughput.append(1)
        else:
            meanThroughput.append(junction.arrived / junction.departed)
        for lane in junction.tails_per_lane:
            meanTailLength.append(sum(junction.tails_per_lane[lane]) / len(junction.tails_per_lane[lane]))
            lane_max = max(junction.tails_per_lane[lane])
            if lane_max > maxTail:
                maxTail = lane_max
        meanTail = sum(meanTailLength) / len(meanTailLength)
        for tail in meanTailLength:
            varTail += (tail - meanTail) ** 2
        meanTails.append(meanTail)
        stDevTails.append(sqrt(varTail / len(meanTailLength)))
        maxTails.append(maxTail)
        maxTail = -1

    traci.close()

    if output_redirection:

        sys.stdout = origin_stdout

        sys.stderr = origin_stderr

    queue.put([meanTravelTime, stDevTravelTime, max(travelTimes), meanHeadTime, stDevHeadTime, max(headTimes),
               meanTailTime, stDevTailTime, max(tailTimes), meanSpeed, stDevSpeed,
               round(sum(meanTails) / len(meanTails), 2), round(sum(stDevTails) / len(stDevTails), 2), max(maxTails),
               round(sum(meanThroughput) / len(meanThroughput), 2), meanTails, stDevTails, maxTails, meanThroughput])
