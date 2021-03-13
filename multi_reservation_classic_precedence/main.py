from inpout_multi import redirect_output

from trafficElements_multi.junction import FourWayJunction
from trafficElements_multi.simulation import *
from trafficElements_multi.reservationManager import *

import traci
from sumolib import miscutils


def run(numberOfSteps, numberOfVehicles, schema, sumoCmd, celle_per_lato, traiettorie_matrice, secondi_di_sicurezza,
        path, index, queue, seed):
    """Funzione che avvia la simulazione dato un certo numero di veicoli"""

    port = miscutils.getFreeSocketPort()

    redirect_output(path, index, True)

    traci.start(sumoCmd, port=port, numRetries=1000)

    """Inizializzazione di alcune variabili"""

    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    departed = 0  # numero di veicoli partiti entro la fine della simulazione
    departed_vehicles = []  # lista dei veicoli partiti entro la fine della simulazione
    arrived_vehicles = []  # lista dei veicoli che hanno lasciato la simulazione
    totalTime = 0.00  # tempo totale di simulazione
    step_incr = 0.05  # incremento di step

    # istanzio le matrici [nome_incrocio, variabile]
    attesa = []  # ordine di arrivo su lista, si resetta quando le auto liberano incrocio
    passaggio = []  # auto in passaggio nell'incrocio
    lista_arrivo = []  # auto entrate nelle vicinanze dell'incrocio
    matrice_incrocio = []  # rappresenta la suddivisione matriciale dell'incrocio (in celle)
    ferme = []  # lista di auto ferme allo stop
    stop = []  # lista che indica di quanto si distanzia lo stop dal centro dell'incrocio [dx, sotto, sx, sopra]
    centerJunctID = []  # coordinate (x,y) del centro di un incrocio
    arrayAuto = []  # contiene la lista di auto presenti nella simulazione
    limiti_celle_X = []  # utile per verificare l'appartenenza ad una cella all'interno della matrice dell'incrocio
    limiti_celle_Y = []  # utile per verificare l'appartenenza ad una cella all'interno della matrice dell'incrocio
    passaggio_cella = []  # salvo in che cella si trova l'auto in passaggio [incrID][ [ auto , cella_X , cella_Y ],... ]
    passaggio_precedente = []  # salvo l'ultima situazione di auto in passaggio per rilasciarle all'uscita

    simulation = Simulation()

    """Inizializzo i veicoli assegnadogli una route generata casualmente e, in caso di schema di colori 
    non significativo, dandogli un colore diverso per distinguerli meglio all'interno della simulazione"""

    vehicles = simulation.generateVehicles(stepsSpawn, numberOfVehicles, vehicles, instantPay, seed)

    if schema in ['n', 'N']:
        simulation.colorVehicles(numberOfVehicles)

    """Inizializzo gli incroci che fanno parte della simulazione"""

    junctions = [FourWayJunction(n, vehicles) for n in range(1, 26)]

    junctionsList = [junction for junction in junctions if junction.nID in central_junctions_ids]

    for junction in junctionsList:  # scorro lista incroci
        incrID = junctionsList.index(junction)  # popolo vettori e matrici inserendo le righe
        attesa.append([])
        lista_arrivo.append([])
        ferme.append([])
        passaggio.append([])
        passaggio_cella.insert(incrID, [])
        passaggio_precedente.append([])

        centerJunctID.append(traci.junction.getPosition(junction.getID()))  # posizione del centro dell'incrocio

        shape = traci.junction.getShape(junction.getID())  # forma dell'incrocio
        stop.append(stopXY(shape))  # estremi dell'incrocio, dove sono presenti gli stop

        # popolo i vettori limiti_celle_X e limiti_celle_Y
        limiti = limiti_celle(stopXY(shape), celle_per_lato)
        limiti_celle_X.append(limiti[0])
        limiti_celle_Y.append(limiti[1])
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

    """Apro il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa"""

    while traci.simulation.getMinExpectedNumber() > 0 and totalTime < numberOfSteps:
        totalTime = round(totalTime + step_incr, 2)
        traci.simulationStep()
        departed += traci.simulation.getDepartedNumber()
        departed_vehicles += traci.simulation.getDepartedIDList()
        arrived_vehicles += traci.simulation.getArrivedIDList()

        arrayAuto = costruzioneArray(arrayAuto)

        vehicles, departed_vehicles = simulation.checkRoute(vehicles, departed_vehicles, arrived_vehicles,
                                                            numberOfVehicles)

        for junction in junctionsList:  # scorro la lista incroci
            incrID = junctionsList.index(junction)

            for auto in arrayAuto:  # scorro l'array delle auto ancora presenti nella simulazione

                if auto == 'idV60':
                    print(traci.vehicle.getRoute(auto))

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
                else:
                    if not ((stop_temp[3] - 50 <= pos[0] <= stop_temp[1] + 50) and
                            (stop_temp[2] - 50 <= pos[1] <= stop_temp[0] + 50)) and auto in lista_arrivo[incrID]:
                        lista_arrivo[incrID].remove(auto)
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
                                                      x_auto_in_celle, y_auto_in_celle, vehicles[auto],
                                                      junction.node_ids)
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
                                                          x_auto_in_celle, y_auto_in_celle, vehicles[auto],
                                                          junction.node_ids)
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
                    lane = getLaneIndexFromEdges(edges, vehicles[x[0]], junction.node_ids)
                    if lane != 0:
                        # se l'auto non gira a destra
                        if x[1] is None and x[2] is None:
                            pos = traci.vehicle.getPosition(x[0])
                            if in_incrocio(pos, stop[incrID]):
                                IDvett = passaggio_cella[incrID].index(x)
                                passaggio_cella[incrID][IDvett] = get_cella_from_pos_auto(x[0], limiti_celle_X[incrID],
                                                                                          limiti_celle_Y[incrID])

                info = percorso_libero(passaggio[incrID], matrice_incrocio[incrID], passaggio_cella[incrID],
                                       limiti_celle_X[incrID], limiti_celle_Y[incrID], stop[incrID], vehicles,
                                       junction.node_ids)
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
                                                         y_auto_in_celle, vehicles[auto_ferma], junction.node_ids):
                                # vedo se il suo percorso è libero e nel caso la faccio partire
                                info = avantiAuto(auto_ferma, passaggio[incrID], attesa[incrID], ferme[incrID],
                                                  matrice_incrocio[incrID], passaggio_cella[incrID],
                                                  traiettorie_matrice, stop[incrID], x_auto_in_celle,
                                                  y_auto_in_celle, vehicles[auto_ferma], junction.node_ids)

                                passaggio[incrID] = info[0]
                                attesa[incrID] = info[1]
                                ferme[incrID] = info[2]
                                matrice_incrocio[incrID] = info[3]
                                passaggio_cella[incrID] = info[4]
            # riaccelero i veicoli all'uscita dall'incrocio
            for auto_uscita in passaggio_precedente[incrID]:
                if auto_uscita not in passaggio[incrID]:
                    traci.vehicle.setMaxSpeed(auto_uscita[0], 13.888888)
                    traci.vehicle.setSpeed(auto_uscita[0], 13.888888)
                    traci.vehicle.setSpeedMode(auto_uscita[0], 31)
            passaggio_precedente[incrID] = passaggio[incrID][:]
        # ogni 10 step pulisco la matrice da valori troppo vecchi
        if totalTime % round(10 * step_incr, 2) == 0:
            matrice_incrocio = pulisci_matrice(matrice_incrocio, secondi_di_sicurezza)

        if totalTime % 1 == 0:
            vehicles, junctions = simulation.checkVehicles(vehicles, departed_vehicles, junctions, int(totalTime),
                                                           schema)

    """Salvo tutti i risultati della simulazione e li ritorno"""

    meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime, \
    stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, meanTails, \
    stDevTails, maxTails, meanThroughput = simulation.saveResults(vehicles, departed, junctions)

    traci.close()

    redirect_output(path, index, False)

    queue.put([meanTravelTime, stDevTravelTime, maxTravelTime, meanHeadTime, stDevHeadTime, maxHeadTime, meanTailTime,
               stDevTailTime, maxTailTime, meanSpeed, stDevSpeed, meanTail, stDevTail, maxTail, meanTp, meanTails,
               stDevTails, maxTails, meanThroughput])
