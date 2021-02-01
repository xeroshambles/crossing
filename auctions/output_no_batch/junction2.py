import sys
from abc import abstractmethod, ABC
from math import ceil

import traci

from trafficElements.auction import CompetitiveAuction, CooperativeAuction
from trafficElements.competitive import CompetitiveCrossingManager
from trafficElements.cooperative import CooperativeCrossingManager


class Junction(ABC):
    """ Classe padre di tutti i tipi di incrocio possibili (a 2, 3 o 4 vie)."""

    def __init__(self, numericID, vehicles, iP, sM, bM, groupDimension=None):
        self.nID = numericID
        self.junctionID = f'n{numericID}'
        self.vehicles = vehicles
        self.edges = []
        self.lanes = []
        self.incomingLanes = []
        self.outgoingLanes = []
        # mappo le strade che arrivano sulle direzioni cardinali: N, E, S, O (senso orario)
        self.mapNESO = {}
        self.possibleRoutes = {}
        self.clashingEdges = {}
        self.payMode = iP
        self.isCompetitive = sM
        self.bufferMode = bM
        self.maxDimensionOfGroups = groupDimension
        if sM:
            self.crossingManager = CompetitiveCrossingManager(self)
        else:
            self.crossingManager = CooperativeCrossingManager(self)

    def getNumericID(self):
        """Ritorna l'id numerico dell'incrocio."""
        return self.nID

    def getID(self):
        """Ritorna l'id nel formato stringa: n<INT_ID>."""
        return f'n{self.nID}'

    def getEdges(self):
        """Ritorna l'insieme delle strade entranti e uscenti dall'incrocio."""
        return self.edges.copy()

    def getLanes(self):
        """Ritorna l'insieme delle corsie entranti e uscenti dall'incrocio."""
        return self.lanes.copy()

    def getNESOMap(self):
        """Ritorna il risultato del mapping rispetto alle coordinate NESO."""
        return self.mapNESO.copy()

    def laneCalc(self):
        """Funzione che determina le corsie a partire dall'insieme delle strade."""
        for i in self.edges:
            lanes = [f'{i}_0', f'{i}_2', f'{i}_4']
            self.lanes += lanes

    def incomingLanesCalc(self):
        """Funzione utilizzata per calcolare l'insieme delle corsie entranti nell'incrocio e per inizializzare
        informazioni relative alle winnersLane del CrossingManager competitivo."""
        self.incomingLanes = [i for i in self.lanes if int(i[1:3]) != self.nID]
        self.crossingManager.winnersLanes = {i: [] for i in self.incomingLanes}

    def outgoingLanesCalc(self):
        """Funzione utilizzata per calcolare l'insieme delle corsie uscenti dall'incrocio"""
        self.outgoingLanes = [i for i in self.lanes if int(i[1:3]) == self.nID]

    def getIncomingLanes(self):
        """Ritorna l'insieme delle corsie entranti nell'incrocio."""
        return self.incomingLanes.copy()

    def getOutgoingLanes(self):
        """Ritorna l'insieme delle corsie uscenti dall'incrocio."""
        return self.outgoingLanes.copy()

    def getCrossingManager(self):
        """Restituisce il crossing manager associato all'incrocio."""
        return self.crossingManager

    def getMaxDimension(self):
        """Restituisce la dimensione massima dei gruppi principali."""
        return self.maxDimensionOfGroups

    def isWithinMaxDimension(self, veh):
        """Funzione che restituisce True se il veicolo rientra fra i partecipanti principali, false altrimenti."""
        lane = traci.vehicle.getLaneID(veh.getID())
        listOfVehicles = traci.lane.getLastStepVehicleIDs(lane)
        maxDimension = self.maxDimensionCalc(lane)
        if veh.getID() in listOfVehicles[-maxDimension:]:
            return True
        return False

    def maxDimensionCalc(self, lane):
        """Funzione che calcola la dimensione massima del gruppo principale se questa deve essere variabile."""
        # caso di dimensione fissa
        if self.maxDimensionOfGroups != -1:
            return self.maxDimensionOfGroups
        # caso di dimensione variabile (il gruppo è composto dalla prima metà dei veicoli lungo la corsia)
        num_veh = len(traci.lane.getLastStepVehicleIDs(lane))
        return ceil(num_veh/2)

    def fromEdgesToLanes(self, vehicle):
        """Funzione utilizzabile per ottenere la route, composta di lanes, che un veicolo deve seguire per attraversare
        correttamente l'incrocio."""
        route = vehicle.getCurrentRoute()
        # prendo il numero di lane corrente su cui è il veicolo
        currentLane = traci.vehicle.getLaneID(vehicle.getID())[-1]
        # prendo i numeri dell'edge corrente su cui è il veicolo
        currentEdge = (int(route[0][1:3]), int(route[0][4:6]))
        # prendo i numeri dell'edge obiettivo del veicolo
        nextEdge = (int(route[1][1:3]), int(route[1][4:6]))
        # ritorno se la traiettoria è frontale
        if abs(currentEdge[0] - currentEdge[1]) == abs(nextEdge[0] - nextEdge[1]):
            return f'{route[0]}_{currentLane}', f'{route[1]}_{currentLane}'
        lane0 = f'{route[0]}_0'
        lane1 = f'{route[0]}_1'
        laneBase = ''
        laneObjective = ''
        # ciclo per tutte le possibili direzioni rispetto alla lane di destra
        for direction, lane in self.possibleRoutes[lane0].items():
            if lane[:-2] == route[1]:
                laneBase = lane0
                laneObjective = lane
                break
        # se non ho trovato una direzione legale rispetto alla lane di destra
        if laneBase == '':
            # ciclo per tutte le possibili direzioni rispetto alla lane di sinistra
            for direction, lane in self.possibleRoutes[lane1].items():
                if lane[:-2] == route[1]:
                    laneBase = lane1
                    laneObjective = lane
                    break
        return laneBase, laneObjective

    def isFrontalTrajectory(self, vehicle):
        """Funzione che restituisce True se il veicolo passato in argomento deve andare dritto, False altrimenti"""
        route = vehicle.getCurrentRoute()
        currentEdge = (int(route[0][1:3]), int(route[0][4:6]))
        nextEdge = (int(route[1][1:3]), int(route[1][4:6]))
        if abs(currentEdge[0] - currentEdge[1]) == abs(nextEdge[0] - nextEdge[1]):
            return True
        return False

    def findPossibleRoutes(self):
        """Metodo che trova tutte le possibili corsie obbiettivo (outgoing lanes) per ogni corsia entrante
        nell'incrocio. I calcoli effettuati da questa funzione sono specifici per una rete 5x5, ma facilmente
        generalizzabili."""
        # TODO: controlla la def bs => è refactoring

        for l in self.getLanes():
            e1 = int(l[1:3])
            e2 = int(l[4:6])
            suffix = l[-1]
            if e1 > e2:
                continue
            #solo le entranti
            #if e1 == self.nID:
            #    continue

            frontEdge = rightEdge = leftEdge = ''
            """Determino se sono presenti strade frontali (passaggio diritto all'incrocio) e ne calcolo l'id"""
            j = 5
            #e03_05_0 -> e05_01_0
            '''if (l == 'e02_05_0'):
                print('resto incriminato: ' + str((e1 + 2) % 4))
                print(f'lane generata: e0{j}_0{(e1 + 2) % 4}_{suffix}')'''
            mod = ((e1 + 1) % 4) + 1
            frontEdge = f'e0{j}_0{mod}_{suffix}'

            """Determino se sono presenti curve a destra e ne calcolo l'id"""
            if suffix == '0': #vado a dx

                mod = ((e1 + 2) % 4) + 1
                rightEdge = f'e0{j}_0{mod}_0'


            """Determino se sono presenti curve a sinistra e ne calcolo l'id"""
            if suffix == '1':
                mod = (e1 % 4) + 1
                leftEdge = f'e0{j}_0{mod}_1'


            """Salvo le traiettorie trovate."""
            self.possibleRoutes[l] = {'front': frontEdge, 'right': rightEdge, 'left': leftEdge}

    @abstractmethod
    def laneNESOMapping(self):
        """Metodo che mappa le corsie che entrano ed escono dall'incrocio secondo la rispettiva cardinalità (le strade
        nella parte superiore sono le Nord, quella nell'inferiore le Sud, ...)"""
        pass

    @abstractmethod
    def findClashingEdges(self):
        """metodo che calcola le traiettorie incidentali relative all'incrocio"""
        pass

    def isClashing(self, route1, route2):
        """funzione che prende in ingresso 2 coppie del tipo: lane attuale e lane obbiettivo, ritornando True se le
        route sono in collisione, False altrimenti"""
        if route1 in self.clashingEdges[route2[0]][route2[1]]:
            return True
        return False

    def getClashingRoutes(self, route):
        """Funzione che, data una rotta, ritorna tutte le traiettorie incidentali per essa."""
        try:
            if self.clashingEdges[route[0]][route[1]] is not None:
                return self.clashingEdges[route[0]][route[1]].copy()
            else:
                return []
        except:
            pass

    # ################################################################################################################ #
    """Il seguente blocco di funzioni (fino al prossimo gruppo di ###) è legato al caso delle simulazioni con 
    bufferizzazione, ed è in uno stato incompleto."""
    def removeWinningVehicles(self, vehiclesFound):
        """Funzione che rimuove dall'elenco di veicoli che devono partecipare all'asta quelli che ne hanno già vinta
        una"""
        for i in vehiclesFound:
            vehToBeRemoved = []
            for j in i:
                if j in self.getCrossingManager().getCurrentWinners():
                    vehToBeRemoved.append(j)
            for v in vehToBeRemoved:
                i.remove(v)
        vehiclesInCT = [i for i in vehiclesFound if i != []]
        return vehiclesInCT

    def removeVehiclesAlreadyInAuction(self, vehiclesFound):
        """Funzione che rimuove dall'elenco di veicoli che devono partecipare all'asta quelli che ne hanno già vinta
        una"""
        for i in vehiclesFound:
            vehToBeRemoved = []
            for j in i:
                if j in self.getCrossingManager().vehiclesInAuction:
                    vehToBeRemoved.append(j)
            for v in vehToBeRemoved:
                i.remove(v)
        vehiclesInCT = [i for i in vehiclesFound if i != []]
        return vehiclesInCT

    def getVehiclesInClashingTrajectories(self, idVeh, vehicles):
        """Funzione che ritorna l'elenco di veicoli con traiettorie incidentali rispetto a quello passato in argomento.
        :param idVeh: veicolo di cui vogliamo conoscere gli avversari all'asta;
        :param junction: identificatore dell'incrocio in cui si svolgerà l'asta;
        :param vehicles: dizionario che associa gli id dei veicoli agli oggetti"""
        routeI = self.fromEdgesToLanes(idVeh)
        listOfVehicleInFirstLane = [i for i in traci.lane.getLastStepVehicleIDs(self.fromEdgesToLanes(idVeh)[0])
                                    if i in vehicles]
        listOfVehicleInFirstLane = [i for i in reversed(listOfVehicleInFirstLane)
                                    if vehicles[i].distanceFromEndLane() < 40]
        clashingTrajectoriesII = []
        for i in listOfVehicleInFirstLane:
            if routeI != self.fromEdgesToLanes(vehicles[i]):
                routeII = self.fromEdgesToLanes(vehicles[i])
                clashingTrajectoriesII = self.getClashingRoutes(routeII)
                break

        routeI = self.fromEdgesToLanes(idVeh)
        clashingTrajectories = self.getClashingRoutes(routeI)
        for t in clashingTrajectoriesII:
            if t not in clashingTrajectories:
                clashingTrajectories.append(t)
        clashingTrajectories.append(routeI)
        vehiclesInCT = []
        for j in clashingTrajectories:
            vehiclesInSameLane = []
            listOfVehicleInALane = [i for i in traci.lane.getLastStepVehicleIDs(j[0]) if i in vehicles]
            listOfVehicleInALane = reversed(list(listOfVehicleInALane))  # inverto per partire dal veicolo più
            # vicino all'incrocio
            for k in listOfVehicleInALane:
                # se sono già stati trovati dei veicoli nella stessa corsia faccio il resto dei controlli a
                # prescindere, anche se non è valida la condizione di clash
                # if len(vehiclesInSameLane) > 0 or self.fromEdgesToLanes(vehicles[k].getCurrentRoute()) \
                #                                     in clashingTrajectories:
                if len(vehiclesInSameLane) > 0 or self.fromEdgesToLanes(vehicles[k]) \
                        in clashingTrajectories:
                    if vehicles[k].checkPosition(self):
                        if vehicles[k].distanceFromEndLane() < 40:
                            vehiclesInSameLane.append(vehicles[k])
            if vehiclesInSameLane and vehiclesInSameLane not in vehiclesInCT:
                vehiclesInCT.append(vehiclesInSameLane)
        if self.isCompetitive:
            vehiclesInCT = self.removeWinningVehicles(vehiclesInCT)
        else:
            vehiclesInCT = self.removeVehiclesAlreadyInAuction(vehiclesInCT)
        return vehiclesInCT
        # else:
        #     return []

    # ################################################################################################################ #

    def createAuction(self, idVeh, vehicles):
        """Funzione che permette di aggiungere un'asta all'elenco di quelle attualmente in corso nell'incrocio
           :param idVeh: ID del veicolo di cui si cercheranno i rivali.
           :param vehicles: veicoli raggruppati per corsia d'appartenenza;"""
        if self.bufferMode:
            """Incompleto, vai all'else"""
            # print(f'trying auction at {self.getID()}')
            vehiclesInCT = self.getVehiclesInClashingTrajectories(idVeh, vehicles)
            # se la lunghezza è 1 vuol dire o che non ci sono altri veicoli oltre ad idVeh (ed eventuali accodati)
            # oppure che nessuno degli altri veicoli è in una traiettoria incidentale, se è 0 vuol dire che sono
            if len(vehiclesInCT) == 1:
                return None
            else:
                # cerco i veicoli su una traiettoria incidentale rispetto ai veicoli che sono su una traiettoria
                # incidentale con idVEh
                # print('start auction with vehicle:', idVeh.getID())
                nonGroupedVehicles = [j for i in vehiclesInCT for j in i]
                newVehicles = vehiclesInCT.copy()
                for i in nonGroupedVehicles:
                    if i != idVeh and i.distanceFromEndLane() < 40:
                        nv = self.getVehiclesInClashingTrajectories(i, vehicles)
                        for k in nv:
                            if k not in newVehicles:
                                newVehicles.append(k)
                                for x in k:
                                    if x not in nonGroupedVehicles:
                                        nonGroupedVehicles.append(x)
                # nel caso alcuni sotto-gruppi di veicoli fossero presenti all'interno di altri gruppi li rimuovo
                groupOfVehiclesToBeRemoved = []
                for i in newVehicles:
                    for j in newVehicles:
                        if i != j:
                            for k in i:
                                if k in j:
                                    shorterSet = i if len(i) < len(j) else j
                                    if shorterSet not in groupOfVehiclesToBeRemoved:
                                        groupOfVehiclesToBeRemoved.append(shorterSet)
                for i in groupOfVehiclesToBeRemoved:
                    newVehicles.remove(i)
                vehiclesInCT = [i for i in newVehicles if i != []]
                if len(vehiclesInCT) > 1:
                    if self.isCompetitive:
                        auction = CompetitiveAuction(vehiclesInCT, self)
                    else:
                        auction = CooperativeAuction(vehiclesInCT, self)
                    self.getCrossingManager().addAuctionResult(auction)
                else:
                    return None
        else:
            """Ramo importante della funzione."""
            lp = []
            ls = []
            """Se è variabile otterrò una dimensione dipendente dal numero di veicoli in corsia."""
            maxLength = self.maxDimensionCalc(idVeh.getCurrentLane())
            # print('trying auction', idVeh.getID())
            """Ciclo sulla reversed del getLastStepVehicleIDs() per selezionare prima i veicoli più vicini 
            all'incrocio."""
            for veh in reversed(traci.lane.getLastStepVehicleIDs(idVeh.getCurrentLane())):
                veh = vehicles[veh]
                # print(f'conditions on {veh.getID()} ({veh.getCurrentLane()}): posizione {veh.checkPosition(self)}, '
                #       f'auction {veh not in self.crossingManager.vehiclesInAuction}, veicoli riattivati {veh not in self.crossingManager.nonStoppedVehicles}, '
                #       f'distanza {veh.distanceFromEndLane() < 40}, maxLength {len(lp) < maxLength}')
                if veh.checkPosition(self) and veh not in self.crossingManager.vehiclesInAuction \
                        and veh not in self.crossingManager.nonStoppedVehicles:
                    if veh.distanceFromEndLane() < 40 and len(lp) < maxLength:
                        lp.append(veh)
                        # print(f'adding {veh.getID()} to lp')
                    else:
                        ls.append(veh)
                        # print(f'adding {veh.getID()} to ls')

            clashingLists = [[lp, ls]]
            clashingVehicles = [idVeh]
            vehiclesInHead = [i for i in self.crossingManager.getCrossingStatus().values() if i is not None
                              and i not in self.crossingManager.getVehiclesInAuction()
                              and i not in self.crossingManager.nonStoppedVehicles
                              and i.distanceFromEndLane() < 15 and i.checkPosition(self)]

            """Cerco i veicoli in traiettoria incidentale con quelli pronti a partecipare all'asta."""
            for veh in clashingVehicles:
                # print('veh subject', veh.getID(), veh.getCurrentRoute())
                # print(f'subject {veh.getID()} ({veh.getCurrentLane()})')
                for otherVeh in vehiclesInHead:
                    # print(f'object {otherVeh.getID()} ({otherVeh.getCurrentLane()}), condizioni: diversità {otherVeh != veh}, non presenza '
                    #       f'{otherVeh not in clashingVehicles}, clashing {self.isClashing(self.fromEdgesToLanes(veh), self.fromEdgesToLanes(otherVeh))}')
                    if otherVeh != veh and otherVeh not in clashingVehicles:
                        if self.isClashing(self.fromEdgesToLanes(veh),
                                           self.fromEdgesToLanes(otherVeh)):
                            clashingVehicles.append(otherVeh)
                            vlp = []
                            vls = []
                            maxLength = self.maxDimensionCalc(otherVeh.getCurrentLane())
                            for v in reversed(traci.lane.getLastStepVehicleIDs(otherVeh.getCurrentLane())):
                                v = vehicles[v]
                                # print(
                                #     f'conditions on {v.getID()} ({v.getCurrentLane()}): posizione {v.checkPosition(self)}, '
                                #     f'auction {v not in self.crossingManager.vehiclesInAuction}, veicoli riattivati {v not in self.crossingManager.nonStoppedVehicles}, '
                                #     f'distanza {v.distanceFromEndLane() < 40}, maxLength {len(vlp) < maxLength}')
                                if v.checkPosition(self) and v not in self.crossingManager.vehiclesInAuction \
                                        and v not in self.crossingManager.nonStoppedVehicles:
                                    if v.distanceFromEndLane() < 40 and len(vlp) < maxLength:
                                        vlp.append(v)
                                        # print(f'adding {veh.getID()} to vlp')
                                    else:
                                        vls.append(v)
                                        # print(f'adding {veh.getID()} to vls')
                            if vlp:
                                clashingLists.append([vlp, vls])
            # print('number of clashing lists', len(clashingLists))
            # cLLength = len(clashingLists)
            # blockingVehicles = []

            # ######################################################################################################## #
            """Blocco di codice che impedisce ai veicoli in traiettoria incidentale con l'insieme dei bloccanti di 
            prendere parte alle aste. Tutti i veicoli dopo un veicolo che non può prendere parte ad un'asta vengono
            messi insieme ad esso nel gruppo degli sponsors."""
            if self.isCompetitive:
                # for cl in clashingLists:
                #     print('p c l v: ', end='')
                #     for v in cl[0]:
                #         print(v.getID(), v.getCurrentLane(), end=', ')
                #     print()
                """Caso competitivo. Con questo ciclo individuiamo eventuali veicoli in clash con veicoli vincitori 
                e gli impediamo di prendere parte all'asta. L'asta non viene permessa nemmeno ai veicoli che vengono 
                dopo il veicolo in clash."""
                if self.crossingManager.currentWinners:
                    blockingVehicles = self.crossingManager.currentWinners.copy()
                    # blockingVehicles.extend(i for i in self.crossingManager.nonStoppedVehicles if i not in blockingVehicles)
                    listsToBeRemoved = []
                    for cl in clashingLists:
                        vehToBeRemoved = []
                        for veh in cl[0]:
                            isInAClash = False
                            for bv in blockingVehicles:
                                # print(f'bv {bv.getID()}, ({bv.getCurrentLane()})')
                                # se trovo un veicolo in clash con un vincitore
                                if self.isClashing(self.fromEdgesToLanes(veh), self.crossingManager.partecipantsRoutes[bv]):
                                    isInAClash = True
                                    # lo rimuovo insieme a tutti i veicoli vengono dopo di lui
                                    vehToBeRemoved = cl[0][cl[0].index(veh):]
                                    break
                            if isInAClash:
                                for v in vehToBeRemoved:
                                    cl[0].remove(v)
                                if not cl[0]:
                                    # se non ci sono più veicoli rimuoviamo la lista
                                    listsToBeRemoved.append(cl)
                                else:
                                    # aggiungiamo i veicoli che non possono direttamente partecipare all'asta all'elenco
                                    # degli sponsor.
                                    cl[1].extend(vehToBeRemoved)
                                break
                    for li in listsToBeRemoved:
                        clashingLists.remove(li)
            else:
                # for cl in clashingLists:
                #     print('p c l v: ', end='')
                #     for v in cl[0]:
                #         print(v.getID(), v.getCurrentLane(), end=', ')
                #     print()
                """Caso cooperativo. Con questo ciclo individuiamo eventuali veicoli in clash con veicoli che hanno 
                preso precedentemente parte ad un'asta. L'asta non viene permessa nemmeno ai veicoli che vengono dopo
                 il veicolo in clash."""
                if self.crossingManager.orderedCooperativeList:
                    blockingVehicles = [x for j in self.crossingManager.orderedCooperativeList for i in j for x in i]
                    # print(f'bv {self.getID()} {[x.getID() for x in blockingVehicles]}')
                    # if len(blockingVehicles) > 2:
                    # blockingVehicles.extend(i for i in self.crossingManager.nonStoppedVehicles if i not in blockingVehicles)
                    listsToBeRemoved = []
                    for cl in clashingLists:
                        vehToBeRemoved = []
                        for veh in cl[0]:
                            isInAClash = False
                            for bv in blockingVehicles:
                                # print(f'bv {bv.getID()}, ({bv.getCurrentLane()})')
                                # meccanismo uguale al caso competitivo, guarda quei commenti
                                if self.isClashing(self.fromEdgesToLanes(veh), self.crossingManager.partecipantsRoutes[bv]):
                                    isInAClash = True
                                    vehToBeRemoved = cl[0][cl[0].index(veh):]
                                    break
                            if isInAClash:
                                for v in vehToBeRemoved:
                                    cl[0].remove(v)
                                if not cl[0]:
                                    listsToBeRemoved.append(cl)
                                else:
                                    # aggiungiamo i veicoli che non possono direttamente partecipare all'asta all'elenco
                                    # degli sponsor.
                                    cl[1].extend(vehToBeRemoved)
                                break
                    for li in listsToBeRemoved:
                        clashingLists.remove(li)

            # for vh in vehiclesInHead:
            #     print('veh in head', vh.getID())
            # for cl in clashingLists:
            #     print('c l v: ', end='')
            #     for v in cl[0]:
            #         print(v.getID(), end=', ')
            #     print()

            if len(clashingLists) > 1:
                # if not (len(clashingLists) != cLLength and len(blockingVehicles) < 3):
                    # print('starting the auction.')
                    # for cl in clashingLists:
                    #     print('f p c l v: ', end='')
                    #     for v in cl[0]:
                    #         print(v.getID(), v.getCurrentLane(), end=', ')
                    #     print()
                    # auction = CompetitiveAuction(clashingLists, self, True)
                    if self.isCompetitive:
                        auction = CompetitiveAuction(clashingLists, self, False, self.payMode, self.bufferMode)
                    else:
                        auction = CooperativeAuction(clashingLists, self, self.payMode, self.bufferMode)
                    self.crossingManager.saveAuctionResults(auction)

    def getVehiclesAtJunction(self):
        """Funzione che restituisce tutti i veicoli che viaggiano verso un incrocio"""
        vehiclesAtJunction = []
        for l in self.getLanes():
            print(l)
            if int(l[1:3]) != self.getNumericID():  # si lavora sui veicoli che viaggiano verso l'incrocio
                # for v in traci.lane.getLastStepVehicleIDs(l):
                # vehiclesAtJunction.append(v)
                vehiclesAtJunction += reversed(traci.lane.getLastStepVehicleIDs(l))
        return vehiclesAtJunction


class TwoWayJunction(Junction):
    """Classe inutilizzata e incompleta."""
    def __init__(self, numericID):
        super().__init__(numericID)
        self.edgeCalc()
        self.laneCalc()
        self.incomingLanesCalc()
        self.outgoingLanesCalc()
        self.laneNESOMapping()
        self.findPossibleRoutes()

    def edgeCalc(self):
        """Essendo i casi di incroci a 2 solo 4 l'assegnamento può essere diretto"""
        cases = {
            1: ['e01_02', 'e02_01', 'e01_06', 'e06_01'],
            5: ['e05_04', 'e04_05', 'e05_10', 'e10_05'],
            21: ['e21_22', 'e22_21', 'e21_16', 'e16_21'],
            25: ['e25_24', 'e24_25', 'e25_20', 'e20_25'],
        }

        try:
            self.edges = cases[self.nID]
        except KeyError:
            print("ID errato: un incrocio a 2 vie può avere ID 1, 5, 21, 25", file=sys.stderr)

    def laneNESOMapping(self):
        cases = {
            1: {'N': [], 'E': self.lanes[:4], 'S': self.lanes[4:], 'O': []},
            5: {'N': [], 'E': [], 'S': self.lanes[4:], 'O': self.lanes[:4]},
            21: {'N': self.lanes[4:], 'E': self.lanes[:4], 'S': [], 'O': []},
            25: {'N': self.lanes[4:], 'E': [], 'S': [], 'O': self.lanes[:4]},
        }
        self.mapNESO = cases[self.nID]

    def findPossibleRoutes(self):
        counter = -1
        for i in self.lanes:
            counter += 1
            if int(i[1:3]) == self.nID:
                continue
            nextEdge = self.lanes[(counter + 2) % 8]
            self.possibleRoutes[i] = [nextEdge]

    def findClashingEdges(self):
        """Nel caso dell'incrocio di 2 strade non ci sono mai interferenze, perciò non saranno indicate interferenze."""
        return {}

    def isClashing(self, route1, route2):
        """Nel caso dell'incrocio di 2 strade non ci sono mai interferenze, perciò sarà sempre ritornato False."""
        return False


class ThreeWayJunction(Junction):
    """Caso di incrocio a tre strade, non utilizzato nelle simulazioni finali ma completo."""
    def __init__(self, numericID, vehicles, iP, sM, bM, groupDimension=None):
        super().__init__(numericID, vehicles, iP, sM, bM, groupDimension)
        self.edgeCalc()
        self.laneCalc()
        self.incomingLanesCalc()
        self.outgoingLanesCalc()
        self.laneNESOMapping()
        self.findPossibleRoutes()
        self.findClashingEdges()

    def edgeCalc(self):
        """Funzione utilizzata per calcolare le strade entranti ed uscenti dall'incrocio. Funzione eseguita in fase di
        pre-processing."""
        # bs sta per 'baseString'
        bs = f'{"0" if self.nID <= 9 else ""}'  # determina se deve essere presente uno 0 prima degli id degli edge
        bsS1 = f'{"0" if self.nID - 1 <= 9 else ""}'  # come bs, ma sottrae 1
        bsA1 = f'{"0" if self.nID + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
        bsS5 = f'{"0" if self.nID - 5 <= 9 else ""}'  # come bs, ma sottrae 5
        bsA5 = f'{"0" if self.nID + 5 <= 9 else ""}'  # come bs, ma aggiunge 5

        if self.nID % 5 != 1 and self.nID % 5 != 0:
            self.edges = [f'e{bs}{self.nID}_{bsS1}{self.nID - 1}', f'e{bsS1}{self.nID - 1}_{bs}{self.nID}',
                          f'e{bs}{self.nID + 1}_{bsA1}{self.nID}', f'e{bs}{self.nID}_{bsA1}{self.nID + 1}', ]
            if self.nID in range(2, 5):
                self.edges += [f'e{bs}{self.nID + 5}_{bsA5}{self.nID}', f'e{bsA5}{self.nID}_{bs}{self.nID + 5}', ]
            if self.nID in range(22, 25):
                self.edges += [f'e{bs}{self.nID - 5}_{bsS5}{self.nID}', f'e{bsS5}{self.nID}_{bs}{self.nID - 5}', ]
        else:
            self.edges = [f'e{bs}{self.nID}_{bsS5}{self.nID - 5}', f'e{bsS5}{self.nID - 5}_{bs}{self.nID}',
                          f'e{bsA5}{self.nID + 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA5}{self.nID + 5}', ]
            if self.nID % 5 == 1:
                self.edges += [f'e{bs}{self.nID}_{bsA1}{self.nID + 1}', f'e{bsA1}{self.nID + 1}_{bs}{self.nID}', ]
            if self.nID % 5 == 0:
                self.edges += [f'e{bs}{self.nID}_{bsS1}{self.nID - 1}', f'e{bsS1}{self.nID - 1}_{bs}{self.nID}', ]

    def laneNESOMapping(self):
        """Mapping effettuato sulla base della rete utilizzata, altamente specifico per essa."""
        cases = {
            str([2, 3, 4]): {'N': [], 'E': self.lanes[4:8], 'S': self.lanes[8:], 'O': self.lanes[:4]},
            str([22, 23, 24]): {'N': self.lanes[8:], 'E': self.lanes[4:8], 'S': [], 'O': self.lanes[:4]},
            str([6, 11, 16]): {'N': self.lanes[:4], 'E': self.lanes[8:], 'S': self.lanes[4:8], 'O': []},
            str([10, 15, 20]): {'N': self.lanes[:4], 'E': [], 'S': self.lanes[4:8], 'O': self.lanes[8:]},
        }
        pos = ''
        for i in cases.keys():
            if str(self.nID) in i:
                pos = i
                break
        try:
            self.mapNESO = cases[pos]
        except KeyError:
            print("Errore nell'inserimento dell'ID, o se ne è scelto uno scorretto o l'incrocio deve essere a 1/2 vie.",
                  file=sys.stderr)

    def findCommonRoute(self, edge, turn):
        """Funzione che trova le traiettorie con corsia di partenza differente e corsia obbiettivo uguale."""
        if self.possibleRoutes[edge][turn]:
            for k in self.possibleRoutes:
                if k == edge:
                    continue
                for x in self.possibleRoutes[k]:
                    if self.possibleRoutes[k][x] == self.possibleRoutes[edge][turn]:
                        clashingEdge1 = (k, self.possibleRoutes[k][
                            x])  # il primo elemento è il clashing edge, il secondo è la strada che deve voler prendere
                        # perchè ci sia il clash
                        clashingEdge2 = (edge, self.possibleRoutes[k][x])
                        self.clashingEdges[edge][self.possibleRoutes[edge][turn]].append(clashingEdge1)
                        self.clashingEdges[k][self.possibleRoutes[k][x]].append(clashingEdge2)

    def findClashingRoutes(self, edge):
        """Funzione altamente specifica per la rete utilizzata che memorizza le traiettorie incidentali interne
        all'incrocio."""
        try:
            opEdge = list(f'e{self.possibleRoutes[edge]["front"][4:6]}_{self.possibleRoutes[edge]["front"][1:3]}_1')
            if self.possibleRoutes[''.join(opEdge)]['left']:
                opEdge = ''.join(opEdge)
                leftEdge = self.possibleRoutes[opEdge]["left"]
                clashingEdge1 = (opEdge, leftEdge)
                clashingEdge2 = (edge, self.possibleRoutes[edge]['front'])
                self.clashingEdges[edge][self.possibleRoutes[edge]['front']].append(clashingEdge1)
                self.clashingEdges[opEdge][leftEdge].append(clashingEdge2)
                opLeftEdge = f'e{leftEdge[4:6]}_{leftEdge[1:3]}_1'
                clashingEdge1 = (opLeftEdge, self.possibleRoutes[opLeftEdge]["left"])
                clashingEdge2 = (edge, self.possibleRoutes[edge]['front'])
                self.clashingEdges[edge][self.possibleRoutes[edge]['front']].append(clashingEdge1)
                self.clashingEdges[opLeftEdge][self.possibleRoutes[opLeftEdge]["left"]].append(clashingEdge2)
            else:
                opEdge[-1] = '0'
                opEdge1 = ''.join(opEdge)
                rightEdge = self.possibleRoutes[opEdge1]['right']
                opRightEdge = f'e{rightEdge[4:6]}_{rightEdge[1:3]}_1'
                clashingEdge1 = (opRightEdge, self.possibleRoutes[opRightEdge]["left"])
                try:
                    self.clashingEdges[edge][self.possibleRoutes[edge]['left']].append(clashingEdge1)
                except:
                    pass
        except:
            leftEdge = self.possibleRoutes[edge]['left']
            opLeftEdge = f'e{leftEdge[4:6]}_{leftEdge[1:3]}_1'
            frontEdge = self.possibleRoutes[opLeftEdge]['front']
            opFrontEdge = f'e{frontEdge[4:6]}_{frontEdge[1:3]}_1'
            clashingEdge2 = (opFrontEdge, self.possibleRoutes[opFrontEdge]["left"])
            self.clashingEdges[edge][self.possibleRoutes[edge]['left']].append(clashingEdge2)

    def findClashingEdges(self):
        """Funzione che avvia la ricerca delle traiettorie incidentali nell'incrocio."""
        # inizializzo le liste dei possibili clash
        for i in self.possibleRoutes:
            self.clashingEdges[i] = {self.possibleRoutes[i][j]: [] for j in self.possibleRoutes[i]
                                     if self.possibleRoutes[i][j] != ''}
        for i in self.possibleRoutes:
            booleanControl = False
            # trovo i clash nel girare a destra
            self.findCommonRoute(i, 'right')
            # trovo i clash nell'andare dritto e alcuni di quelli nell'andare a sinistra
            if self.possibleRoutes[i]['front']:
                self.findClashingRoutes(i)
                booleanControl = True
            # trovo i clash nell'andare a sinistra
            if self.possibleRoutes[i]['left']:
                self.findCommonRoute(i, 'left')
                if not booleanControl:
                    self.findClashingRoutes(i)


class FourWayJunction(Junction):
    """Caso di incrocio a quattro strade, unici utilizzati nelle simulazioni finali."""
    def __init__(self, numericID, vehicles, iP, sM, bM, groupDimension=None):
        super().__init__(numericID, vehicles, iP, sM, bM, groupDimension)
        self.edgeCalc()
        self.laneCalc()
        self.incomingLanesCalc()
        self.outgoingLanesCalc()
        self.laneNESOMapping()
        self.findPossibleRoutes()
        self.findClashingEdges()

    def edgeCalc(self):
        """Funzione utilizzata per calcolare le strade entranti ed uscenti dall'incrocio. Funzione eseguita in fase di
        pre-processing."""

        self.edges = [f'e0{self.nID}_02', f'e02_0{self.nID}',
                      f'e0{self.nID}_06', f'e06_0{self.nID}',
                      f'e0{self.nID}_08', f'e08_0{self.nID}',
                      f'e0{self.nID}_12', f'e12_0{self.nID}']

    def laneNESOMapping(self):
        """Mapping effettuato sulla base della rete utilizzata, altamente specifico per essa."""
        self.mapNESO = {'N': self.lanes[:6], 'E': self.lanes[6:12], 'S': self.lanes[18:], 'O': self.lanes[12:18]}

    def findCommonRoute(self, edge, turn):
        """Funzione che trova le traiettorie con corsia di partenza differente e corsia obbiettivo uguale."""
        for k in self.possibleRoutes:
            if k == edge:
                continue
            for x in self.possibleRoutes[k]:
                if self.possibleRoutes[k][x] == self.possibleRoutes[edge][turn]:
                    clashingEdge1 = (k, self.possibleRoutes[k][
                        x])  # il primo elemento è il clashing edge, il secondo è la strada che deve voler prendere
                    # perchè ci sia il clash
                    # clashingEdge2 = (edge, self.possibleRoutes[k][x])
                    self.clashingEdges[edge][self.possibleRoutes[edge][turn]].append(clashingEdge1)
                    # self.clashingEdges[k][self.possibleRoutes[k][x]].append(clashingEdge2)

    def findClashingRoutes(self, edge):
        """Funzione altamente specifica per la rete utilizzata che memorizza le traiettorie incidentali interne
        all'incrocio."""
        # troviamo i clash per le strade perpendicolari
        opRightEdge = f'e{self.possibleRoutes[edge]["right"][4:6]}_{self.possibleRoutes[edge]["right"][1:3]}'
        clashingEdge1 = (f'{opRightEdge}_0', self.possibleRoutes[f'{opRightEdge}_0']["front"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['front']].append(clashingEdge1)
        clashingEdge2 = (f'{opRightEdge}_1', self.possibleRoutes[f'{opRightEdge}_1']["front"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['front']].append(clashingEdge2)
        opRightOpFrontEdge = f'e{self.possibleRoutes[f"{opRightEdge}_0"]["front"][4:6]}_' \
                             f'{self.possibleRoutes[f"{opRightEdge}_0"]["front"][1:3]}'
        clashingEdge1 = (f'{opRightOpFrontEdge}_0', self.possibleRoutes[f'{opRightOpFrontEdge}_0']["front"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['front']].append(clashingEdge1)
        clashingEdge2 = (f'{opRightOpFrontEdge}_1', self.possibleRoutes[f'{opRightOpFrontEdge}_1']["front"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['front']].append(clashingEdge2)

        # troviamo i clash per le strade
        clashingEdge1 = (f'{opRightEdge}_1', self.possibleRoutes[f'{opRightEdge}_1']["left"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['front']].append(clashingEdge1)
        opFrontEdge = f'e{self.possibleRoutes[edge]["front"][4:6]}_{self.possibleRoutes[edge]["front"][1:3]}'
        clashingEdge2 = (f'{opFrontEdge}_1', self.possibleRoutes[f'{opFrontEdge}_1']["left"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['front']].append(clashingEdge2)

    def findClashingRoutesWhenTurningLeft(self, edge):
        """Funzione altamente specifica per la rete utilizzata che memorizza le traiettorie incidentali interne
        all'incrocio, in particolare quelle che si hanno nello svoltare a sinistra."""
        # troviamo i clash per le strade perpendicolari
        opLeftEdge = f'e{self.possibleRoutes[edge]["left"][4:6]}_{self.possibleRoutes[edge]["left"][1:3]}'
        clashingEdge1 = (f'{opLeftEdge}_0', self.possibleRoutes[f'{opLeftEdge}_0']["front"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['left']].append(clashingEdge1)
        clashingEdge2 = (f'{opLeftEdge}_1', self.possibleRoutes[f'{opLeftEdge}_1']["front"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['left']].append(clashingEdge2)
        opFrontEdge = f'e{self.possibleRoutes[edge]["front"][4:6]}_{self.possibleRoutes[edge]["front"][1:3]}'
        clashingEdge1 = (f'{opFrontEdge}_0', self.possibleRoutes[f'{opFrontEdge}_0']["front"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['left']].append(clashingEdge1)
        clashingEdge2 = (f'{opFrontEdge}_1', self.possibleRoutes[f'{opFrontEdge}_1']["front"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['left']].append(clashingEdge2)

        # troviamo i clash per le strade
        clashingEdge1 = (f'{opLeftEdge}_1', self.possibleRoutes[f'{opLeftEdge}_1']["left"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['left']].append(clashingEdge1)
        opLeftOpFrontEdge = f'e{self.possibleRoutes[f"{opLeftEdge}_0"]["front"][4:6]}_' \
                            f'{self.possibleRoutes[f"{opLeftEdge}_0"]["front"][1:3]}'
        clashingEdge2 = (f'{opLeftOpFrontEdge}_1', self.possibleRoutes[f'{opLeftOpFrontEdge}_1']["left"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['left']].append(clashingEdge2)
        # aggiungo l'ultimo perpendicolare, si potrebbe trovare anche con il commonRoute
        clashingEdge1 = (f'{opLeftOpFrontEdge}_1', self.possibleRoutes[f'{opLeftOpFrontEdge}_1']["front"])
        self.clashingEdges[edge][self.possibleRoutes[edge]['left']].append(clashingEdge1)

    def findClashingEdges(self):
        """Funzione che avvia la ricerca delle traiettorie incidentali nell'incrocio."""
        # inizializzo le liste dei possibili clash
        for i in self.possibleRoutes:
            self.clashingEdges[i] = {self.possibleRoutes[i][j]: [] for j in self.possibleRoutes[i]
                                     if self.possibleRoutes[i][j] != ''}
        for i in self.possibleRoutes:
            if i[-1] == '0':
                self.findClashingRoutes(i)
                self.findCommonRoute(i, 'right')
                self.findCommonRoute(i, 'front')
            if i[-1] == '1':
                parallelLane = list(i)
                parallelLane[-1] = '0'
                parallelLane = ''.join(parallelLane)
                self.clashingEdges[i][self.possibleRoutes[i]['front']] = \
                    self.clashingEdges[parallelLane][self.possibleRoutes[parallelLane]['front']].copy()
                self.clashingEdges[i][self.possibleRoutes[i]['front']].remove(
                    self.clashingEdges[parallelLane][self.possibleRoutes[parallelLane]['front']][-1])
                self.findCommonRoute(i, 'front')
                self.findClashingRoutesWhenTurningLeft(i)


if __name__ == '__main__':
    a = FourWayJunction(13, True, True, True, True)
    print(a.edges)
    print(a.lanes)
    print('NESO', a.mapNESO)
    print('PR', a.possibleRoutes)
    print(a.clashingEdges)
    # print(a.isClashing(('e17_22_1', 'e22_23_1'), ('e21_22_1', 'e22_23_1')))
