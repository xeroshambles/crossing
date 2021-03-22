from config_multi import *
from abc import abstractmethod, ABC

from .auction import CompetitiveAuction, CooperativeAuction
from .competitive import CompetitiveCrossingManager
from .cooperative import CooperativeCrossingManager
from .reservationManager import ReservationManager

import traci


class Junction(ABC):
    """ Classe padre di tutti i tipi di incrocio possibili (a 2, 3 o 4 vie)."""

    def __init__(self, numericID, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                 groupDimension=dimensionOfGroups, cellsPerSide=cellsPerSide, matrixTrajectories=None,
                 securitySecs=securitySecs):
        self.nID = numericID
        # self.networdDimension = netDim  # forma: X x Y, la rete sarà rettangolare o quadrata. Default: 5x5
        self.junctionID = f'n{numericID}'
        self.vehicles = vehicles
        self.node_ids = []
        self.edges = []
        self.lanes = []
        self.incomingLanes = []
        self.outgoingLanes = []
        self.mapNESO = {}  # mappo le strade che arrivano sulle direzioni cardinali: N, E, S, O (senso orario)
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
        self.reservationManager = ReservationManager(self, cellsPerSide, matrixTrajectories, securitySecs)

        self.departed = 0
        self.arrived = 0
        self.junction_shape = traci.junction.getShape("n" + str(self.nID))
        self.vehiclesEntering = []

    def getNumericID(self):
        """Ritorna l'id numerico dell'incrocio."""
        return self.nID

    def getID(self):
        """Ritorna l'id nel formato stringa: n<INT_ID>."""
        return f'n{self.nID}'

    def getEdges(self):
        """Ritorna l'elenco delle strade entranti e uscenti dall'incrocio."""
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
            lanes = [f'{i}_0', f'{i}_1', f'{i}_2']
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
        # if maxDimension == -1:
        #     from math import ceil
        #     maxDimension = ceil(len(listOfVehicles)/2)
        #     assert maxDimension != 0, 'Errore sulla dimensione nel caso proporzionale: è a 0'
        # print('DDD', listOfVehicles[self.getMaxDimension()-1:], listOfVehicles)
        if veh.getID() in listOfVehicles[-maxDimension:]:
            return True
        return False

    # fissa se non si da un parametro = -1
    def maxDimensionCalc(self, lane):
        """Funzione che calcola la dimensione massima del gruppo principale se questa deve essere variabile."""
        if self.maxDimensionOfGroups != -1:
            return self.maxDimensionOfGroups
        num_veh = len(traci.lane.getLastStepVehicleIDs(lane))
        from math import ceil
        # print(f'AAA {lane} {num_veh} {ceil(num_veh / 2)}')
        return ceil(num_veh / 2)

    def fromEdgesToLanes(self, vehicle):
        """Funzione utilizzabile per ottenere la route, composta di lanes, che un veicolo deve seguire per attraversare
        correttamente l'incrocio."""
        route = vehicle.getCurrentRoute()
        # print('route', route, vehicle.getID())
        # print(traci.vehicle.getRoute(vehicle.getID()))
        currentLane = traci.vehicle.getLaneID(vehicle.getID())[-1]
        currentEdge = (int(route[0][1:3]), int(route[0][4:6]))
        nextEdge = (int(route[1][1:3]), int(route[1][4:6]))
        if abs(currentEdge[0] - currentEdge[1]) == abs(nextEdge[0] - nextEdge[1]):  # front
            return f'{route[0]}_{currentLane}', f'{route[1]}_{currentLane}'
        lane0 = f'{route[0]}_0'
        lane4 = f'{route[0]}_2'
        laneBase = ''
        laneObjective = ''
        for direction, lane in self.possibleRoutes[lane0].items():
            if lane[:-2] == route[1]:
                laneBase = lane0
                laneObjective = lane
                break
        if laneBase == '':
            for direction, lane in self.possibleRoutes[lane4].items():
                if lane[:-2] == route[1]:
                    laneBase = lane4
                    laneObjective = lane
                    break
        return laneBase, laneObjective

    def isFrontalTrajectory(self, vehicle):
        """Funzione che restituisce True se il veicolo passato in argomento deve andare dritto, False altrimenti"""
        route = traci.vehicle.getRoute(vehicle.getID())  # vehicle.getCurrentRoute()
        # print(f'for vehicle {vehicle.getID()}, current route is: {route}')
        # print(traci.vehicle.getRoute(vehicle.getID()))
        # currentLane = traci.vehicle.getLaneID(vehicle.getID())[-1]
        currentEdge = (int(route[0][1:3]), int(route[0][4:6]))
        nextEdge = (int(route[1][1:3]), int(route[1][4:6]))
        if abs(currentEdge[0] - currentEdge[1]) == abs(nextEdge[0] - nextEdge[1]):
            return True
        return False

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

        """Ramo importante della funzione."""
        lp = []
        ls = []
        """Se è variabile otterrò una dimensione dipendente dal numero di veicoli in corsia."""
        maxLength = self.maxDimensionCalc(idVeh.getCurrentLane())  # non importante, ritorna maxNumberOfVehicles
        # print('trying auction given vehicle', idVeh.getID()[3:])
        """Ciclo sulla reversed del getLastStepVehicleIDs() per selezionare prima i veicoli più vicini 
        all'incrocio."""
        for veh in reversed(traci.lane.getLastStepVehicleIDs(idVeh.getCurrentLane())):
            veh = vehicles[veh]
            # print(f'conditions on {veh.getID()} ({veh.getCurrentLane()}): posizione {veh.checkPosition(self)}, '
            # f'auction {veh not in self.crossingManager.vehiclesInAuction}, veicoli riattivati {veh not in self.crossingManager.nonStoppedVehicles}, '
            # f'distanza {veh.distanceFromEndLane() < 40}, maxLength {len(lp) < maxLength}')
            # se veicolo non e tra quelli in auction ed è stoppato
            if veh.checkPosition(self) and veh not in self.crossingManager.vehiclesInAuction \
                    and veh not in self.crossingManager.nonStoppedVehicles:
                if veh.distanceFromEndLane() < 40 and len(lp) < maxLength:
                    lp.append(veh)
                    # print(f'adding {veh.getID()} to lp')
                else:
                    ls.append(veh)
                    # print(f'adding {veh.getID()} to ls')

        clashingLists = [[lp, ls]]
        vv = [[[[x.getID()] for x in l] for l in group] for group in clashingLists]

        # print(f'clashingLists: {vv}')
        clashingVehicles = [idVeh]
        vv = [v.getID() for v in clashingVehicles]
        # print(f'clashingVehicles: {vv}')
        vehiclesInHead = [i for i in self.crossingManager.getCrossingStatus().values() if i is not None
                          and i not in self.crossingManager.getVehiclesInAuction()
                          and i not in self.crossingManager.nonStoppedVehicles
                          and i.distanceFromEndLane() < 15 and i.checkPosition(self)]
        vv = [v.getID() for v in vehiclesInHead]
        # print(f'vehiclesInHead: {vv}')

        """Cerco i veicoli in traiettoria incidentale con quelli pronti a partecipare all'asta."""
        for veh in clashingVehicles:
            # print('veh subject', veh.getID(), veh.getCurrentRoute())
            # print(f'subject {veh.getID()} ({veh.getCurrentLane()})')
            for otherVeh in vehiclesInHead:
                # print(f'object {otherVeh.getID()} ({otherVeh.getCurrentLane()}), condizioni: diversità {otherVeh !=
                # veh}, non presenza ' f'{otherVeh not in clashingVehicles}, clashing {self.isClashing(
                # self.fromEdgesToLanes(veh), self.fromEdgesToLanes(otherVeh))}')
                if otherVeh != veh and otherVeh not in clashingVehicles:
                    if self.isClashing(self.fromEdgesToLanes(veh),
                                       self.fromEdgesToLanes(otherVeh)):
                        clashingVehicles.append(otherVeh)
                        vlp = []
                        vls = []
                        maxLength = self.maxDimensionCalc(otherVeh.getCurrentLane())
                        for v in reversed(traci.lane.getLastStepVehicleIDs(otherVeh.getCurrentLane())):
                            v = vehicles[v]
                            # print( f'conditions on {v.getID()} ({v.getCurrentLane()}): posizione {v.checkPosition(
                            # self)}, ' f'auction {v not in self.crossingManager.vehiclesInAuction},
                            # veicoli riattivati {v not in self.crossingManager.nonStoppedVehicles}, ' f'distanza {
                            # v.distanceFromEndLane() < 40}, maxLength {len(vlp) < maxLength}')
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
            """Caso competitivo. Con questo ciclo individuiamo eventuali veicoli in clash con veicoli vincitori 
            e gli impediamo di prendere parte all'asta. L'asta non viene permessa nemmeno ai veicoli che vengono 
            dopo il veicolo in clash."""
            if self.crossingManager.currentWinners:
                blockingVehicles = self.crossingManager.currentWinners.copy()
                # blockingVehicles.extend(i for i in self.crossingManager.nonStoppedVehicles if i not in
                # blockingVehicles)
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
            """Caso cooperativo. Con questo ciclo individuiamo eventuali veicoli in clash con veicoli che hanno 
            preso precedentemente parte ad un'asta. L'asta non viene permessa nemmeno ai veicoli che vengono dopo
             il veicolo in clash."""
            if self.crossingManager.orderedCooperativeList:
                blockingVehicles = [x for j in self.crossingManager.orderedCooperativeList for i in j for x in i]
                # print(f'bv {self.getID()} {[x.getID() for x in blockingVehicles]}') if len(blockingVehicles) > 2:
                # blockingVehicles.extend(i for i in self.crossingManager.nonStoppedVehicles if i not in
                # blockingVehicles)
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

        for lane in self.getIncomingLanes():
            # print("current junction lanes: " + f'{self.getLanes()}')
            # print("l is: " + f'{l}')
            if int(lane[1:3]) != self.getNumericID():  # si lavora sui veicoli che viaggiano verso l'incrocio
                # for v in traci.lane.getLastStepVehicleIDs(l):
                # vehiclesAtJunction.append(v)
                vehiclesAtJunction += reversed(traci.lane.getLastStepVehicleIDs(lane))
        return vehiclesAtJunction

    def getActualVehicles(self, departed_vehicles):
        """Funzione che ritorna tutti i veicoli che sono nell'incrocio"""

        vehicles = []

        for veh in departed_vehicles:
            veh_lane = traci.vehicle.getLaneID(veh)
            if veh_lane in self.lanes or (str(self.junctionID) + '_' in veh_lane):
                vehicles.append(veh)

        return vehicles


class FourWayJunction(Junction):
    """Caso di incrocio a quattro strade, unici utilizzati nelle simulazioni finali."""

    def __init__(self, numericID, vehicles, iP=instantPay, sM=simulationMode, bM=False,
                 groupDimension=dimensionOfGroups, cellsPerSide=cellsPerSide, matrixTrajectories=None,
                 securitySecs=securitySecs):
        super().__init__(numericID, vehicles, iP, sM, bM, groupDimension, cellsPerSide, matrixTrajectories,
                         securitySecs)

        if self.nID in vertex_junctions_ids:
            self.edgeCalcVertex()
        elif self.nID in lateral_junctions_ids:
            self.edgeCalcLateral()
        else:
            self.edgeCalcCentral()

        self.laneCalc()
        self.incomingLanesCalc()
        self.outgoingLanesCalc()
        self.laneNESOMapping()

        if self.nID in vertex_junctions_ids:
            self.findPossibleRoutesVertex()
        elif self.nID in lateral_junctions_ids:
            self.findPossibleRoutesLateral()
        else:
            self.findPossibleRoutesCentral()

        self.findClashingEdges()

        self.tailsPerLane = {lane: [] for lane in self.incomingLanes}

    def edgeCalcVertex(self):
        """Funzione utilizzata per calcolare le strade entranti ed uscenti dagli incroci ai vertici.
        Funzione eseguita in fase di pre-processing."""

        bs = f'{"0" if self.nID <= 9 else ""}'  # determina se deve essere presente uno 0 prima degli id degli edge
        bsS1 = f'{"0" if self.nID - 1 <= 9 else ""}'  # come bs, ma sottrae 1
        bsA1 = f'{"0" if self.nID + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
        bsS5 = f'{"0" if self.nID - 5 <= 9 else ""}'  # come bs, ma sottrae 5
        bsA5 = f'{"0" if self.nID + 5 <= 9 else ""}'  # come bs, ma aggiunge 5

        if self.nID == 1:
            self.node_ids = [self.nID + 25, self.nID + 1, self.nID + 5, self.nID + 50]
            self.edges = [f'e{self.nID + 25}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 25}',
                          f'e{bsA1}{self.nID + 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA1}{self.nID + 1}',
                          f'e{bsA5}{self.nID + 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA5}{self.nID + 5}',
                          f'e{self.nID + 50}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 50}']
        elif self.nID == 5:
            self.node_ids = [self.nID + 25, self.nID + 50, self.nID + 5, self.nID - 1]
            self.edges = [f'e{self.nID + 25}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 25}',
                          f'e{self.nID + 50}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 50}',
                          f'e{bsA5}{self.nID + 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA5}{self.nID + 5}',
                          f'e{bsS1}{self.nID - 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS1}{self.nID - 1}']
        elif self.nID == 21:
            self.node_ids = [self.nID - 5, self.nID + 1, self.nID + 25, self.nID + 50]
            self.edges = [f'e{bsS5}{self.nID - 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS5}{self.nID - 5}',
                          f'e{bsA1}{self.nID + 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA1}{self.nID + 1}',
                          f'e{self.nID + 25}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 25}',
                          f'e{self.nID + 50}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 50}']
        elif self.nID == 25:
            self.node_ids = [self.nID - 5, self.nID + 50, self.nID + 25, self.nID - 1]
            self.edges = [f'e{bsS5}{self.nID - 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS5}{self.nID - 5}',
                          f'e{self.nID + 50}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 50}',
                          f'e{self.nID + 25}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 25}',
                          f'e{bsS1}{self.nID - 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS1}{self.nID - 1}']

    def edgeCalcLateral(self):
        """Funzione utilizzata per calcolare le strade entranti ed uscenti dagli incroci laterali.
        Funzione eseguita in fase di pre-processing."""

        bs = f'{"0" if self.nID <= 9 else ""}'  # determina se deve essere presente uno 0 prima degli id degli edge
        bsS1 = f'{"0" if self.nID - 1 <= 9 else ""}'  # come bs, ma sottrae 1
        bsA1 = f'{"0" if self.nID + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
        bsS5 = f'{"0" if self.nID - 5 <= 9 else ""}'  # come bs, ma sottrae 5
        bsA5 = f'{"0" if self.nID + 5 <= 9 else ""}'  # come bs, ma aggiunge 5

        if self.nID in range(2, 5):
            self.node_ids = [self.nID + 25, self.nID + 1, self.nID + 5, self.nID - 1]
            self.edges = [f'e{self.nID + 25}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 25}',
                          f'e{bsA1}{self.nID + 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA1}{self.nID + 1}',
                          f'e{bsA5}{self.nID + 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA5}{self.nID + 5}',
                          f'e{bsS1}{self.nID - 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS1}{self.nID - 1}']
        elif self.nID in [10, 15, 20]:
            self.node_ids = [self.nID - 5, self.nID + 50, self.nID + 5, self.nID - 1]
            self.edges = [f'e{bsS5}{self.nID - 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS5}{self.nID - 5}',
                          f'e{self.nID + 50}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 50}',
                          f'e{bsA5}{self.nID + 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA5}{self.nID + 5}',
                          f'e{bsS1}{self.nID - 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS1}{self.nID - 1}']
        elif self.nID in range(22, 25):
            self.node_ids = [self.nID - 5, self.nID + 1, self.nID + 25, self.nID - 1]
            self.edges = [f'e{bsS5}{self.nID - 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS5}{self.nID - 5}',
                          f'e{bsA1}{self.nID + 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA1}{self.nID + 1}',
                          f'e{self.nID + 25}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 25}',
                          f'e{bsS1}{self.nID - 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS1}{self.nID - 1}']
        elif self.nID in [6, 11, 16]:
            self.node_ids = [self.nID - 5, self.nID + 1, self.nID + 5, self.nID + 50]
            self.edges = [f'e{bsS5}{self.nID - 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS5}{self.nID - 5}',
                          f'e{bsA1}{self.nID + 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA1}{self.nID + 1}',
                          f'e{bsA5}{self.nID + 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA5}{self.nID + 5}',
                          f'e{self.nID + 50}_{bs}{self.nID}', f'e{bs}{self.nID}_{self.nID + 50}']

    def edgeCalcCentral(self):
        """Funzione utilizzata per calcolare le strade entranti ed uscenti dagli incroci interni.
        Funzione eseguita in fase di pre-processing."""

        bs = f'{"0" if self.nID <= 9 else ""}'  # determina se deve essere presente uno 0 prima degli id degli edge
        bsS1 = f'{"0" if self.nID - 1 <= 9 else ""}'  # come bs, ma sottrae 1
        bsA1 = f'{"0" if self.nID + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
        bsS5 = f'{"0" if self.nID - 5 <= 9 else ""}'  # come bs, ma sottrae 5
        bsA5 = f'{"0" if self.nID + 5 <= 9 else ""}'  # come bs, ma aggiunge 5

        self.node_ids = [self.nID - 5, self.nID + 1, self.nID + 5, self.nID - 1]

        self.edges = [f'e{bsS5}{self.nID - 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS5}{self.nID - 5}',
                      f'e{bsA1}{self.nID + 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA1}{self.nID + 1}',
                      f'e{bsA5}{self.nID + 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA5}{self.nID + 5}',
                      f'e{bsS1}{self.nID - 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsS1}{self.nID - 1}']

    def laneNESOMapping(self):
        """Mapping effettuato sulla base della rete utilizzata, altamente specifico per essa."""
        self.mapNESO = {'N': self.lanes[:6], 'E': self.lanes[6:12], 'S': self.lanes[12:18], 'O': self.lanes[18:]}

    def getArrivalEdgesFromEdge(self, start):
        """Funzione che trova il posizionamento degli edge (left, front, right) da far seguire al veicolo dato l'edge
        di partenza."""

        distance = -1
        i = 0
        edges = []
        trovato = False

        while True:
            if self.node_ids[i % 4] == start:
                trovato = True
            if trovato:
                distance += 1
                edges.append(self.node_ids[(i + 1) % 4])
                if distance == 3:
                    break
            i += 1

        return edges[0], edges[1], edges[2]

    def findPossibleRoutesVertex(self):
        """Metodo che trova tutte le possibili corsie obbiettivo (outgoing lanes) per ogni corsia entrante
        negli incroci ai vertici. I calcoli effettuati da questa funzione sono specifici per una rete 5x5, ma
        facilmente generalizzabili."""
        neso = {0: 'N', 1: 'E', 2: 'S', 3: 'O'}

        for c in neso:
            for lane in self.mapNESO[neso[c]]:
                e1 = int(lane[1:3])
                if e1 == self.nID:
                    continue
                e2 = int(lane[4:6])
                suffix = lane[-1]

                bsE1S1 = f'{"0" if e1 - 1 <= 9 else ""}'  # come bs, ma sottrae 1
                bsE2S1 = f'{"0" if e2 - 1 <= 9 else ""}'  # come bs, ma sottrae 1
                bsE1A1 = f'{"0" if e1 + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
                bsE2A1 = f'{"0" if e2 + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
                bsE1S5 = f'{"0" if e1 - 5 <= 9 else ""}'  # come bs, ma sottrae 5
                bsE2S5 = f'{"0" if e2 - 5 <= 9 else ""}'  # come bs, ma sottrae 5
                bsE1A5 = f'{"0" if e1 + 5 <= 9 else ""}'  # come bs, ma aggiunge 5
                bsE2A5 = f'{"0" if e2 + 5 <= 9 else ""}'  # come bs, ma aggiunge 5
                bsE1S25 = f'{"0" if e1 - 25 <= 9 else ""}'  # come bs, ma sottrae 25
                bsE1S50 = f'{"0" if e1 - 50 <= 9 else ""}'  # come bs, ma sottrae 25

                frontEdge = rightEdge = leftEdge = ''

                if self.nID == 1:
                    """Determino se sono presenti curve a destra e ne calcolo l'id"""
                    if suffix == '0':
                        if self.mapNESO[neso[(c - 1) % 4]]:
                            if e1 - e2 == 1:
                                rightEdge = f'e{bsE1A5}{e1 - 1}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 5:
                                rightEdge = f'e{bsE1S5}{e1 - 5}_{bsE2A1}{e2 + 1}_{suffix}'
                            if e1 - e2 == 25:
                                rightEdge = f'e{bsE1S25}{e1 - 25}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 50:
                                rightEdge = f'e{bsE1S50}{e1 - 50}_{bsE2A5}{e2 + 5}_{suffix}'

                    """Determino se sono presenti strade frontali e ne calcolo l'id"""
                    if suffix == '1':
                        if self.mapNESO[neso[(c + 2) % 4]]:
                            if e1 - e2 == 1:
                                frontEdge = f'e{bsE1S1}{e1 - 1}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 5:
                                frontEdge = f'e{bsE1S5}{e1 - 5}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 25:
                                frontEdge = f'e{bsE1S25}{e1 - 25}_{bsE2A5}{e2 + 5}_{suffix}'
                            if e1 - e2 == 50:
                                frontEdge = f'e{bsE1S50}{e1 - 50}_{bsE2A1}{e2 + 1}_{suffix}'

                    """Determino se sono presenti curve a sinistra e ne calcolo l'id"""
                    if suffix == '2':
                        if self.mapNESO[neso[(c + 1) % 4]]:
                            if e1 - e2 == 1:
                                leftEdge = f'e{bsE1S1}{e1 - 1}_{bsE2A5}{e2 + 5}_{suffix}'
                            if e1 - e2 == 5:
                                leftEdge = f'e{bsE1S5}{e1 - 5}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 25:
                                leftEdge = f'e{bsE1S25}{e1 - 25}_{bsE2A1}{e2 + 1}_{suffix}'
                            if e1 - e2 == 50:
                                leftEdge = f'e{bsE1S50}{e1 - 50}_{e2 + 25}_{suffix}'

                elif self.nID == 5:
                    """Determino se sono presenti curve a destra e ne calcolo l'id"""
                    if suffix == '0':
                        if self.mapNESO[neso[(c - 1) % 4]]:
                            if e1 - e2 == -1:
                                rightEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A5}{e2 + 5}_{suffix}'
                            if e1 - e2 == 5:
                                rightEdge = f'e{bsE1S5}{e1 - 5}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 25:
                                rightEdge = f'e{bsE1S25}{e1 - 25}_{bsE2S1}{e2 - 1}_{suffix}'
                            if e1 - e2 == 50:
                                rightEdge = f'e{bsE1S50}{e1 - 50}_{e2 + 25}_{suffix}'

                    """Determino se sono presenti strade frontali e ne calcolo l'id"""
                    if suffix == '1':
                        if self.mapNESO[neso[(c + 2) % 4]]:
                            if e1 - e2 == -1:
                                frontEdge = f'e{bsE1A1}{e1 + 1}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 5:
                                frontEdge = f'e{bsE1S5}{e1 - 5}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 25:
                                frontEdge = f'e{bsE1S25}{e1 - 25}_{bsE2A5}{e2 + 5}_{suffix}'
                            if e1 - e2 == 50:
                                frontEdge = f'e{bsE1S50}{e1 - 50}_{bsE2S1}{e2 - 1}_{suffix}'

                    """Determino se sono presenti curve a sinistra e ne calcolo l'id"""
                    if suffix == '2':
                        if self.mapNESO[neso[(c + 1) % 4]]:
                            if e1 - e2 == -1:
                                leftEdge = f'e{bsE1A1}{e1 + 1}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 5:
                                leftEdge = f'e{bsE1S5}{e1 - 5}_{bsE2S1}{e2 - 1}_{suffix}'
                            if e1 - e2 == 25:
                                leftEdge = f'e{bsE1S25}{e1 - 25}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 50:
                                leftEdge = f'e{bsE1S50}{e1 - 50}_{bsE2A5}{e2 + 5}_{suffix}'

                elif self.nID == 21:
                    """Determino se sono presenti curve a destra e ne calcolo l'id"""
                    if suffix == '0':
                        if self.mapNESO[neso[(c - 1) % 4]]:
                            if e1 - e2 == -5:
                                rightEdge = f'e{bsE1A5}{e1 + 5}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 1:
                                rightEdge = f'e{bsE1S1}{e1 - 1}_{bsE2S5}{e2 - 5}_{suffix}'
                            if e1 - e2 == 25:
                                rightEdge = f'e{bsE1S25}{e1 - 25}_{bsE2A1}{e2 + 1}_{suffix}'
                            if e1 - e2 == 50:
                                rightEdge = f'e{bsE1S50}{e1 - 50}_{e2 + 25}_{suffix}'

                    """Determino se sono presenti strade frontali e ne calcolo l'id"""
                    if suffix == '1':
                        if self.mapNESO[neso[(c + 2) % 4]]:
                            if e1 - e2 == -5:
                                frontEdge = f'e{bsE1A5}{e1 + 5}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 1:
                                frontEdge = f'e{bsE1S1}{e1 - 1}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 25:
                                frontEdge = f'e{bsE1S25}{e1 - 25}_{bsE2S5}{e2 - 5}_{suffix}'
                            if e1 - e2 == 50:
                                frontEdge = f'e{bsE1S50}{e1 - 50}_{bsE2A1}{e2 + 1}_{suffix}'

                    """Determino se sono presenti curve a sinistra e ne calcolo l'id"""
                    if suffix == '2':
                        if self.mapNESO[neso[(c + 1) % 4]]:
                            if e1 - e2 == -5:
                                leftEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A1}{e2 + 1}_{suffix}'
                            if e1 - e2 == 1:
                                leftEdge = f'e{bsE1S1}{e1 - 1}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 25:
                                leftEdge = f'e{bsE1S25}{e1 - 25}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 50:
                                leftEdge = f'e{bsE1S50}{e1 - 50}_{bsE2S5}{e2 - 5}_{suffix}'

                elif self.nID == 25:
                    """Determino se sono presenti curve a destra e ne calcolo l'id"""
                    if suffix == '0':
                        if self.mapNESO[neso[(c - 1) % 4]]:
                            if e1 - e2 == -5:
                                rightEdge = f'e{bsE1A5}{e1 + 5}_{bsE2S1}{e2 - 1}_{suffix}'
                            if e1 - e2 == -1:
                                rightEdge = f'e{bsE1A1}{e1 + 1}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 25:
                                rightEdge = f'e{bsE1S25}{e1 - 25}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 50:
                                rightEdge = f'e{bsE1S50}{e1 - 50}_{bsE2S5}{e2 - 5}_{suffix}'

                    """Determino se sono presenti strade frontali e ne calcolo l'id"""
                    if suffix == '1':
                        if self.mapNESO[neso[(c + 2) % 4]]:
                            if e1 - e2 == -5:
                                frontEdge = f'e{bsE1A5}{e1 + 5}_{e2 + 25}_{suffix}'
                            if e1 - e2 == -1:
                                frontEdge = f'e{bsE1A1}{e1 + 1}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 25:
                                frontEdge = f'e{bsE1S25}{e1 - 25}_{bsE2S5}{e2 - 5}_{suffix}'
                            if e1 - e2 == 50:
                                frontEdge = f'e{bsE1S50}{e1 - 50}_{bsE2S1}{e2 - 1}_{suffix}'

                    """Determino se sono presenti curve a sinistra e ne calcolo l'id"""
                    if suffix == '2':
                        if self.mapNESO[neso[(c + 1) % 4]]:
                            if e1 - e2 == -5:
                                leftEdge = f'e{bsE1A5}{e1 + 5}_{e2 + 50}_{suffix}'
                            if e1 - e2 == -1:
                                leftEdge = f'e{bsE1A1}{e1 + 1}_{bsE2S5}{e2 - 5}_{suffix}'
                            if e1 - e2 == 25:
                                leftEdge = f'e{bsE1S25}{e1 - 25}_{bsE2S1}{e2 - 1}_{suffix}'
                            if e1 - e2 == 50:
                                leftEdge = f'e{bsE1S50}{e1 - 50}_{e2 + 25}_{suffix}'

                """Salvo le traiettorie trovate."""
                self.possibleRoutes[lane] = {'front': frontEdge, 'right': rightEdge, 'left': leftEdge}

    def findPossibleRoutesLateral(self):
        """Metodo che trova tutte le possibili corsie obbiettivo (outgoing lanes) per ogni corsia entrante
        negli incroci laterali. I calcoli effettuati da questa funzione sono specifici per una rete 5x5, ma
        facilmente generalizzabili."""
        neso = {0: 'N', 1: 'E', 2: 'S', 3: 'O'}

        for c in neso:
            for lane in self.mapNESO[neso[c]]:
                e1 = int(lane[1:3])
                if e1 == self.nID:
                    continue
                e2 = int(lane[4:6])
                suffix = lane[-1]

                bsE1S1 = f'{"0" if e1 - 1 <= 9 else ""}'  # come bs, ma sottrae 1
                bsE2S1 = f'{"0" if e2 - 1 <= 9 else ""}'  # come bs, ma sottrae 1
                bsE1A1 = f'{"0" if e1 + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
                bsE2A1 = f'{"0" if e2 + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
                bsE1S5 = f'{"0" if e1 - 5 <= 9 else ""}'  # come bs, ma sottrae 5
                bsE2S5 = f'{"0" if e2 - 5 <= 9 else ""}'  # come bs, ma sottrae 5
                bsE1A5 = f'{"0" if e1 + 5 <= 9 else ""}'  # come bs, ma aggiunge 5
                bsE2A5 = f'{"0" if e2 + 5 <= 9 else ""}'  # come bs, ma aggiunge 5
                bsE1S25 = f'{"0" if e1 - 25 <= 9 else ""}'  # come bs, ma sottrae 25
                bsE1S50 = f'{"0" if e1 - 50 <= 9 else ""}'  # come bs, ma sottrae 50

                frontEdge = rightEdge = leftEdge = ''

                if self.nID in range(2, 5):
                    """Determino se sono presenti curve a destra e ne calcolo l'id"""
                    if suffix == '0':
                        if self.mapNESO[neso[(c - 1) % 4]]:
                            if e1 - e2 == -1:
                                rightEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A5}{e2 + 5}_{suffix}'
                            if e1 - e2 == 1:
                                rightEdge = f'e{bsE1S1}{e1 - 1}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 5:
                                rightEdge = f'e{bsE1S5}{e1 - 5}_{bsE2A1}{e2 + 1}_{suffix}'
                            if e1 - e2 == 25:
                                rightEdge = f'e{bsE1S25}{e1 - 25}_{bsE2S1}{e2 - 1}_{suffix}'

                    """Determino se sono presenti strade frontali e ne calcolo l'id"""
                    if suffix == '1':
                        if self.mapNESO[neso[(c + 2) % 4]]:
                            if e1 - e2 == -1:
                                frontEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A1}{e2 + 1}_{suffix}'
                            if e1 - e2 == 1:
                                frontEdge = f'e{bsE1S1}{e1 - 1}_{bsE2S1}{e2 - 1}_{suffix}'
                            if e1 - e2 == 5:
                                frontEdge = f'e{bsE1S5}{e1 - 5}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 25:
                                frontEdge = f'e{bsE1S25}{e1 - 25}_{bsE2A5}{e2 + 5}_{suffix}'

                    """Determino se sono presenti curve a sinistra e ne calcolo l'id"""
                    if suffix == '2':
                        if self.mapNESO[neso[(c + 1) % 4]]:
                            if e1 - e2 == -1:
                                leftEdge = f'e{bsE1A1}{e1 + 1}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 1:
                                leftEdge = f'e{bsE1S1}{e1 - 1}_{bsE2A5}{e2 + 5}_{suffix}'
                            if e1 - e2 == 5:
                                leftEdge = f'e{bsE1S5}{e1 - 5}_{bsE2S1}{e2 - 1}_{suffix}'
                            if e1 - e2 == 25:
                                leftEdge = f'e{bsE1S25}{e1 - 25}_{bsE2A1}{e2 + 1}_{suffix}'

                elif self.nID in [10, 15, 20]:
                    """Determino se sono presenti curve a destra e ne calcolo l'id"""
                    if suffix == '0':
                        if self.mapNESO[neso[(c - 1) % 4]]:
                            if e1 - e2 == -5:
                                rightEdge = f'e{bsE1A5}{e1 + 5}_{bsE2S1}{e2 - 1}_{suffix}'
                            if e1 - e2 == -1:
                                rightEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A5}{e2 + 5}_{suffix}'
                            if e1 - e2 == 5:
                                rightEdge = f'e{bsE1S5}{e1 - 5}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 50:
                                rightEdge = f'e{bsE1S50}{e1 - 50}_{bsE2S5}{e2 - 5}_{suffix}'

                    """Determino se sono presenti strade frontali e ne calcolo l'id"""
                    if suffix == '1':
                        if self.mapNESO[neso[(c + 2) % 4]]:
                            if e1 - e2 == -5:
                                frontEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A5}{e2 + 5}_{suffix}'
                            if e1 - e2 == -1:
                                frontEdge = f'e{bsE1A1}{e1 + 1}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 5:
                                frontEdge = f'e{bsE1S5}{e1 - 5}_{bsE2S5}{e2 - 5}_{suffix}'
                            if e1 - e2 == 50:
                                frontEdge = f'e{bsE1S50}{e1 - 50}_{bsE2S1}{e2 - 1}_{suffix}'

                    """Determino se sono presenti curve a sinistra e ne calcolo l'id"""
                    if suffix == '2':
                        if self.mapNESO[neso[(c + 1) % 4]]:
                            if e1 - e2 == -5:
                                leftEdge = f'e{bsE1A5}{e1 + 5}_{e2 + 50}_{suffix}'
                            if e1 - e2 == -1:
                                leftEdge = f'e{bsE1A1}{e1 + 1}_{bsE2S5}{e2 - 5}_{suffix}'
                            if e1 - e2 == 5:
                                leftEdge = f'e{bsE1S5}{e1 - 5}_{bsE2S1}{e2 - 1}_{suffix}'
                            if e1 - e2 == 50:
                                leftEdge = f'e{bsE1S50}{e1 - 50}_{bsE2A5}{e2 + 5}_{suffix}'

                elif self.nID in range(22, 25):
                    """Determino se sono presenti curve a destra e ne calcolo l'id"""
                    if suffix == '0':
                        if self.mapNESO[neso[(c - 1) % 4]]:
                            if e1 - e2 == -5:
                                rightEdge = f'e{bsE1A5}{e1 + 5}_{bsE2S1}{e2 - 1}_{suffix}'
                            if e1 - e2 == -1:
                                rightEdge = f'e{bsE1A1}{e1 + 1}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 1:
                                rightEdge = f'e{bsE1S1}{e1 - 1}_{bsE2S5}{e2 - 5}_{suffix}'
                            if e1 - e2 == 25:
                                rightEdge = f'e{bsE1S25}{e1 - 25}_{bsE2A1}{e2 + 1}_{suffix}'

                    """Determino se sono presenti strade frontali e ne calcolo l'id"""
                    if suffix == '1':
                        if self.mapNESO[neso[(c + 2) % 4]]:
                            if e1 - e2 == -5:
                                frontEdge = f'e{bsE1A5}{e1 + 5}_{e2 + 25}_{suffix}'
                            if e1 - e2 == -1:
                                frontEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A1}{e2 + 1}_{suffix}'
                            if e1 - e2 == 1:
                                frontEdge = f'e{bsE1S1}{e1 - 1}_{bsE2S1}{e2 - 1}_{suffix}'
                            if e1 - e2 == 25:
                                frontEdge = f'e{bsE1S25}{e1 - 25}_{bsE2S5}{e2 - 5}_{suffix}'

                    """Determino se sono presenti curve a sinistra e ne calcolo l'id"""
                    if suffix == '2':
                        if self.mapNESO[neso[(c + 1) % 4]]:
                            if e1 - e2 == -5:
                                leftEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A1}{e2 + 1}_{suffix}'
                            if e1 - e2 == -1:
                                leftEdge = f'e{bsE1A1}{e1 + 1}_{bsE2S5}{e2 - 5}_{suffix}'
                            if e1 - e2 == 1:
                                leftEdge = f'e{bsE1S1}{e1 - 1}_{e2 + 25}_{suffix}'
                            if e1 - e2 == 25:
                                leftEdge = f'e{bsE1S25}{e1 - 25}_{bsE2S1}{e2 - 1}_{suffix}'

                elif self.nID in [6, 11, 16]:
                    """Determino se sono presenti curve a destra e ne calcolo l'id"""
                    if suffix == '0':
                        if self.mapNESO[neso[(c - 1) % 4]]:
                            if e1 - e2 == -5:
                                rightEdge = f'e{bsE1A5}{e1 + 5}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 1:
                                rightEdge = f'e{bsE1S1}{e1 - 1}_{bsE2S5}{e2 - 5}_{suffix}'
                            if e1 - e2 == 5:
                                rightEdge = f'e{bsE1S5}{e1 - 5}_{bsE2A1}{e2 + 1}_{suffix}'
                            if e1 - e2 == 50:
                                rightEdge = f'e{bsE1S50}{e1 - 50}_{bsE2A5}{e2 + 5}_{suffix}'

                    """Determino se sono presenti strade frontali e ne calcolo l'id"""
                    if suffix == '1':
                        if self.mapNESO[neso[(c + 2) % 4]]:
                            if e1 - e2 == -5:
                                frontEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A5}{e2 + 5}_{suffix}'
                            if e1 - e2 == 1:
                                frontEdge = f'e{bsE1S1}{e1 - 1}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 5:
                                frontEdge = f'e{bsE1S5}{e1 - 5}_{bsE2S5}{e2 - 5}_{suffix}'
                            if e1 - e2 == 50:
                                frontEdge = f'e{bsE1S50}{e1 - 50}_{bsE2A1}{e2 + 1}_{suffix}'

                    """Determino se sono presenti curve a sinistra e ne calcolo l'id"""
                    if suffix == '2':
                        if self.mapNESO[neso[(c + 1) % 4]]:
                            if e1 - e2 == -5:
                                leftEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A1}{e2 + 1}_{suffix}'
                            if e1 - e2 == 1:
                                leftEdge = f'e{bsE1S1}{e1 - 1}_{bsE2A5}{e2 + 5}_{suffix}'
                            if e1 - e2 == 5:
                                leftEdge = f'e{bsE1S5}{e1 - 5}_{e2 + 50}_{suffix}'
                            if e1 - e2 == 50:
                                leftEdge = f'e{bsE1S50}{e1 - 50}_{bsE2S5}{e2 - 5}_{suffix}'

                """Salvo le traiettorie trovate."""
                self.possibleRoutes[lane] = {'front': frontEdge, 'right': rightEdge, 'left': leftEdge}

    def findPossibleRoutesCentral(self):
        """Metodo che trova tutte le possibili corsie obbiettivo (outgoing lanes) per ogni corsia entrante
        nell'incrocio. I calcoli effettuati da questa funzione sono specifici per una rete 5x5, ma facilmente
        generalizzabili."""
        neso = {0: 'N', 1: 'E', 2: 'S', 3: 'O'}

        for c in neso:
            for lane in self.mapNESO[neso[c]]:
                e1 = int(lane[1:3])
                if e1 == self.nID:
                    continue
                e2 = int(lane[4:6])
                suffix = lane[-1]

                bsE1S1 = f'{"0" if e1 - 1 <= 9 else ""}'  # come bs, ma sottrae 1
                bsE2S1 = f'{"0" if e2 - 1 <= 9 else ""}'  # come bs, ma sottrae 1
                bsE1A1 = f'{"0" if e1 + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
                bsE2A1 = f'{"0" if e2 + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
                bsE1S5 = f'{"0" if e1 - 5 <= 9 else ""}'  # come bs, ma sottrae 5
                bsE2S5 = f'{"0" if e2 - 5 <= 9 else ""}'  # come bs, ma sottrae 5
                bsE1A5 = f'{"0" if e1 + 5 <= 9 else ""}'  # come bs, ma aggiunge 5
                bsE2A5 = f'{"0" if e2 + 5 <= 9 else ""}'  # come bs, ma aggiunge 5

                frontEdge = rightEdge = leftEdge = ''

                """Determino se sono presenti curve a destra e ne calcolo l'id"""
                if suffix == '0':
                    if self.mapNESO[neso[(c - 1) % 4]]:
                        if abs(e1 - e2) == 5:
                            rightEdge = f'e{bsE1A5}{e1 + 5}_{bsE2S1}{e2 - 1}_{suffix}' if e1 < e2 \
                                else f'e{bsE1S5}{e1 - 5}_{bsE2A1}{e2 + 1}_{suffix}'
                        if abs(e1 - e2) == 1:
                            rightEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A5}{e2 + 5}_{suffix}' if e1 < e2 \
                                else f'e{bsE1S1}{e1 - 1}_{bsE2S5}{e2 - 5}_{suffix}'

                """Determino se sono presenti strade frontali e ne calcolo l'id"""
                if suffix == '1':
                    if self.mapNESO[neso[(c + 2) % 4]]:
                        if abs(e1 - e2) == 1:
                            frontEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A1}{e2 + 1}_{suffix}' if e1 < e2 \
                                else f'e{bsE1S1}{e1 - 1}_{bsE2S1}{e2 - 1}_{suffix}'
                        if abs(e1 - e2) == 5:
                            frontEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A5}{e2 + 5}_{suffix}' if e1 < e2 \
                                else f'e{bsE1S5}{e1 - 5}_{bsE2S5}{e2 - 5}_{suffix}'

                """Determino se sono presenti curve a sinistra e ne calcolo l'id"""
                if suffix == '2':
                    if self.mapNESO[neso[(c + 1) % 4]]:
                        if abs(e1 - e2) == 5:
                            leftEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A1}{e2 + 1}_{suffix}' if e1 < e2 \
                                else f'e{bsE1S5}{e1 - 5}_{bsE2S1}{e2 - 1}_{suffix}'
                        if abs(e1 - e2) == 1:
                            leftEdge = f'e{bsE1A1}{e1 + 1}_{bsE2S5}{e2 - 5}_{suffix}' if e1 < e2 \
                                else f'e{bsE1S1}{e1 - 1}_{bsE2A5}{e2 + 5}_{suffix}'

                """Salvo le traiettorie trovate."""
                self.possibleRoutes[lane] = {'front': frontEdge, 'right': rightEdge, 'left': leftEdge}

    def findClashingRoutesForCentralLanes(self, left, front, right, base, obj):
        """Funzione altamente specifica per la rete utilizzata che memorizza le traiettorie incidentali interne
        all'incrocio, in particolare quelle che si hanno nell'andare diritto."""

        clashingEdge1 = (f'e{"0" if right < 10 else ""}{right}_{"0" if self.nID < 10 else ""}{self.nID}_1',
                         f'e{"0" if self.nID < 10 else ""}{self.nID}_{"0" if left < 10 else ""}{left}_1')
        self.clashingEdges[base][obj].append(clashingEdge1)
        clashingEdge2 = (f'e{"0" if right < 10 else ""}{right}_{"0" if self.nID < 10 else ""}{self.nID}_2',
                         f'e{"0" if self.nID < 10 else ""}{self.nID}_{base[1:3]}_2')
        self.clashingEdges[base][obj].append(clashingEdge2)
        clashingEdge3 = (f'e{"0" if left < 10 else ""}{left}_{"0" if self.nID < 10 else ""}{self.nID}_1',
                         f'e{"0" if self.nID < 10 else ""}{self.nID}_{"0" if right < 10 else ""}{right}_1')
        self.clashingEdges[base][obj].append(clashingEdge3)
        clashingEdge4 = (f'e{"0" if front < 10 else ""}{front}_{"0" if self.nID < 10 else ""}{self.nID}_2',
                         f'e{"0" if self.nID < 10 else ""}{self.nID}_{"0" if right < 10 else ""}{right}_2')
        self.clashingEdges[base][obj].append(clashingEdge4)

    def findClashingRoutesForLeftLanes(self, left, front, right, base, obj):
        """Funzione altamente specifica per la rete utilizzata che memorizza le traiettorie incidentali interne
        all'incrocio, in particolare quelle che si hanno nello svoltare a sinistra."""

        clashingEdge1 = (f'e{"0" if right < 10 else ""}{right}_{"0" if self.nID < 10 else ""}{self.nID}_2',
                         f'e{"0" if self.nID < 10 else ""}{self.nID}_{base[1:3]}_2')
        self.clashingEdges[base][obj].append(clashingEdge1)
        clashingEdge2 = (f'e{"0" if left < 10 else ""}{left}_{"0" if self.nID < 10 else ""}{self.nID}_1',
                         f'e{"0" if self.nID < 10 else ""}{self.nID}_{"0" if right < 10 else ""}{right}_1')
        self.clashingEdges[base][obj].append(clashingEdge2)
        clashingEdge3 = (f'e{"0" if left < 10 else ""}{left}_{"0" if self.nID < 10 else ""}{self.nID}_2',
                         f'e{"0" if self.nID < 10 else ""}{self.nID}_{"0" if front < 10 else ""}{front}_2')
        self.clashingEdges[base][obj].append(clashingEdge3)
        clashingEdge4 = (f'e{"0" if front < 10 else ""}{front}_{"0" if self.nID < 10 else ""}{self.nID}_1',
                         f'e{"0" if self.nID < 10 else ""}{self.nID}_{base[1:3]}_1')
        self.clashingEdges[base][obj].append(clashingEdge4)

    def findClashingEdges(self):
        """Funzione che avvia la ricerca delle traiettorie incidentali nell'incrocio."""
        # inizializzo le liste dei possibili clash
        # print(f'possible routes are: {self.possibleRoutes}')
        for i in self.possibleRoutes:
            self.clashingEdges[i] = {self.possibleRoutes[i][j]: [] for j in self.possibleRoutes[i]
                                     if self.possibleRoutes[i][j] != ''}
        # print(f'found possible clashing edges: {self.clashingEdges}')
        for i in self.possibleRoutes:
            for j in self.possibleRoutes[i]:
                if self.possibleRoutes[i][j] == '':
                    continue
                k = self.possibleRoutes[i][j]
                left, front, right = self.getArrivalEdgesFromEdge(int(i[1:3]))
                if i[-1] == '1':  # front
                    self.findClashingRoutesForCentralLanes(left, front, right, i, k)
                if i[-1] == '2':  # left
                    self.findClashingRoutesForLeftLanes(left, front, right, i, k)
