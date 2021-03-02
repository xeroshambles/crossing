import sys
from abc import abstractmethod, ABC

import traci


class Junction(ABC):
    """ Classe padre di tutti i tipi di incrocio possibili (a 2, 3 o 4 vie)."""

    def __init__(self, numericID, vehicles, iP, sM, bM, groupDimension=None):
        self.nID = numericID
        # self.networdDimension = netDim  # forma: X x Y, la rete sarà rettangolare o quadrata. Default: 5x5
        self.junctionID = f'n{numericID}'
        self.vehicles = vehicles
        self.node_ids = []
        self.edges = []
        self.lanes = []
        self.incomingLanes = []
        self.outgoingLanes = []
        self.crossingLanes = []
        self.mapNESO = {}  # mappo le strade che arrivano sulle direzioni cardinali: N, E, S, O (senso orario)
        self.possibleRoutes = {}
        self.clashingEdges = {}
        self.payMode = iP
        self.isCompetitive = sM
        self.bufferMode = bM
        self.maxDimensionOfGroups = groupDimension

        self.departed = []
        self.arrived = []
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

    def outgoingLanesCalc(self):
        """Funzione utilizzata per calcolare l'insieme delle corsie uscenti dall'incrocio"""
        self.outgoingLanes = [i for i in self.lanes if int(i[1:3]) == self.nID]

    def crossingLanesCalc(self):
        """Funzione utilizzata per calcolare l'insieme delle corsie entranti nell'incrocio"""
        for i in range(0, len(self.lanes)):
            self.crossingLanes += [f":n{self.nID}_{i}_0", f":n{self.nID}_{i}_1"]

    def getIncomingLanes(self):
        """Ritorna l'insieme delle corsie entranti nell'incrocio."""
        return self.incomingLanes.copy()

    def getOutgoingLanes(self):
        """Ritorna l'insieme delle corsie uscenti dall'incrocio."""
        return self.outgoingLanes.copy()

    def getCrossingLanes(self):
        """Ritorna l'insieme delle corsie uscenti dall'incrocio."""
        return self.crossingLanes.copy()

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

    # fissa se non si da un parametro = -1
    def maxDimensionCalc(self, lane):
        """Funzione che calcola la dimensione massima del gruppo principale se questa deve essere variabile."""
        if self.maxDimensionOfGroups != -1:
            return self.maxDimensionOfGroups
        num_veh = len(traci.lane.getLastStepVehicleIDs(lane))
        from math import ceil
        return ceil(num_veh / 2)

    def fromEdgesToLanes(self, vehicle):
        """Funzione utilizzabile per ottenere la route, composta di lanes, che un veicolo deve seguire per attraversare
        correttamente l'incrocio."""
        route = vehicle.getCurrentRoute()
        currentLane = traci.vehicle.getLaneID(vehicle.getID())[-1]
        currentEdge = (int(route[0][1:3]), int(route[0][4:6]))
        nextEdge = (int(route[1][1:3]), int(route[1][4:6]))
        if abs(currentEdge[0] - currentEdge[1]) == abs(nextEdge[0] - nextEdge[1]):  # diritto
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
        route = traci.vehicle.getRoute(vehicle.getID())
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

    def getVehiclesAtJunction(self):
        """Funzione che restituisce tutti i veicoli che viaggiano verso un incrocio"""
        vehiclesAtJunction = []

        for lane in self.getIncomingLanes():
            if int(lane[1:3]) != self.getNumericID():  # si lavora sui veicoli che viaggiano verso l'incrocio
                vehiclesAtJunction += reversed(traci.lane.getLastStepVehicleIDs(lane))
        return vehiclesAtJunction

    def getActualVehicles(self, departed_vehicles):
        """Funzione che ritorna tutti i veicoli che sono nell'incrocio"""

        vehicles = []

        for veh in departed_vehicles:
            veh_lane = traci.vehicle.getLaneID(veh)
            if veh_lane in self.lanes or ('n' + str(self.nID) in veh_lane):
                vehicles.append(veh)

        return vehicles


class ThreeWayJunction(Junction):
    """Caso di incrocio a tre strade, non utilizzato nelle simulazioni finali ma completo."""

    def __init__(self, numericID, vehicles, iP, sM, bM, groupDimension=None):
        super().__init__(numericID, vehicles, iP, sM, bM, groupDimension)
        self.edgeCalc()
        self.laneCalc()
        self.incomingLanesCalc()
        self.outgoingLanesCalc()
        self.crossingLanesCalc()
        self.laneNESOMapping()
        self.findPossibleRoutes()
        self.findClashingEdges()

        self.tails_per_lane = {lane: [] for lane in self.incomingLanes}

    def edgeCalc(self):
        """Funzione utilizzata per calcolare le strade entranti ed uscenti dall'incrocio. Funzione eseguita in fase di
        pre-processing."""
        # bs sta per 'baseString'
        bs = f'{"0" if self.nID <= 9 else ""}'  # determina se deve essere presente uno 0 prima degli id degli edge
        bsS1 = f'{"0" if self.nID - 1 <= 9 else ""}'  # come bs, ma sottrae 1
        bsA1 = f'{"0" if self.nID + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
        bsS5 = f'{"0" if self.nID - 5 <= 9 else ""}'  # come bs, ma sottrae 5
        bsA5 = f'{"0" if self.nID + 5 <= 9 else ""}'  # come bs, ma aggiunge 5

        if self.nID in range(2, 5):
            self.node_ids = [self.nID + 1, self.nID + 5, self.nID - 1]
        if self.nID in [10, 15, 20]:
            self.node_ids = [self.nID - 5, self.nID + 5, self.nID - 1]
        if self.nID in range(22, 25):
            self.node_ids = [self.nID - 5, self.nID + 1, self.nID - 1]
        if self.nID in [6, 11, 16]:
            self.node_ids = [self.nID - 5, self.nID + 1, self.nID + 5]

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
            str([2, 3, 4]): {'N': [], 'E': self.lanes[6:12], 'S': self.lanes[12:], 'O': self.lanes[:6]},
            str([22, 23, 24]): {'N': self.lanes[12:], 'E': self.lanes[6:12], 'S': [], 'O': self.lanes[:6]},
            str([6, 11, 16]): {'N': self.lanes[:6], 'E': self.lanes[12:], 'S': self.lanes[6:12], 'O': []},
            str([10, 15, 20]): {'N': self.lanes[:6], 'E': [], 'S': self.lanes[6:12], 'O': self.lanes[12:]},
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

    def findPossibleRoutes(self):
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

                """Determino se sono presenti strade a destra e ne calcolo l'id"""
                if suffix == '0':
                    if self.nID in [2, 3, 4]:
                        if e1 - e2 == 1:
                            frontEdge = f'e{bsE1S1}{e1 - 1}_{bsE2S1}{e2 - 1}_{suffix}'
                        if e1 - e2 == 5:
                            rightEdge = f'e{bsE1S5}{e1 - 5}_{bsE2A1}{e2 + 1}_{suffix}'
                        if e1 - e2 == -1:
                            rightEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A5}{e2 + 5}_{suffix}'
                    if self.nID in [10, 15, 20]:
                        if e1 - e2 == -5:
                            rightEdge = f'e{bsE1A5}{e1 + 5}_{bsE2S1}{e2 - 1}_{suffix}'
                        if e1 - e2 == 5:
                            frontEdge = f'e{bsE1S5}{e1 - 5}_{bsE2S5}{e2 - 5}_{suffix}'
                        if e1 - e2 == -1:
                            rightEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A5}{e2 + 5}_{suffix}'
                    if self.nID in [22, 23, 24]:
                        if e1 - e2 == -5:
                            rightEdge = f'e{bsE1A5}{e1 + 5}_{bsE2S1}{e2 - 1}_{suffix}'
                        if e1 - e2 == 1:
                            rightEdge = f'e{bsE1S1}{e1 - 1}_{bsE2S5}{e2 - 5}_{suffix}'
                        if e1 - e2 == -1:
                            frontEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A1}{e2 + 1}_{suffix}'
                    if self.nID in [6, 11, 16]:
                        if e1 - e2 == -5:
                            frontEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A5}{e2 + 5}_{suffix}'
                        if e1 - e2 == 1:
                            rightEdge = f'e{bsE1S1}{e1 - 1}_{bsE2S5}{e2 - 5}_{suffix}'
                        if e1 - e2 == 5:
                            rightEdge = f'e{bsE1A5}{e1 - 5}_{bsE2A5}{e2 + 1}_{suffix}'

                """Determino se sono presenti strade frontali (passaggio diritto all'incrocio) e ne calcolo l'id"""
                if suffix == '1':
                    if self.nID in [2, 3, 4]:
                        if abs(e1 - e2) == 1:
                            frontEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A1}{e2 + 1}_{suffix}' if e1 < e2 \
                                else f'e{bsE1S1}{e1 - 1}_{bsE2S1}{e2 - 1}_{suffix}'
                        if e1 - e2 == 5:
                            rightEdge = f'e{bsE1S5}{e1 - 5}_{bsE2A1}{e2 + 1}_{suffix}'
                            leftEdge = f'e{bsE1S5}{e1 - 5}_{bsE2S1}{e2 - 1}_{suffix}'
                    if self.nID in [10, 15, 20]:
                        if abs(e1 - e2) == 5:
                            frontEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A5}{e2 + 5}_{suffix}' if e1 < e2 \
                                else f'e{bsE1S5}{e1 - 5}_{bsE2S5}{e2 - 5}_{suffix}'
                        if e1 - e2 == -1:
                            rightEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A5}{e2 + 5}_{suffix}'
                            leftEdge = f'e{bsE1A1}{e1 + 1}_{bsE2S5}{e2 - 5}_{suffix}'
                    if self.nID in [22, 23, 24]:
                        if e1 - e2 == -5:
                            rightEdge = f'e{bsE1A5}{e1 + 5}_{bsE2S1}{e2 - 1}_{suffix}'
                            leftEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A1}{e2 + 1}_{suffix}'
                        if abs(e1 - e2) == 1:
                            frontEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A1}{e2 + 1}_{suffix}' if e1 < e2 \
                                else f'e{bsE1S1}{e1 - 1}_{bsE2S1}{e2 - 1}_{suffix}'
                    if self.nID in [6, 11, 16]:
                        if abs(e1 - e2) == 5:
                            frontEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A5}{e2 + 5}_{suffix}' if e1 < e2 \
                                else f'e{bsE1S5}{e1 - 5}_{bsE2S5}{e2 - 5}_{suffix}'
                        if e1 - e2 == 1:
                            rightEdge = f'e{bsE1S1}{e1 - 1}_{bsE2S5}{e2 - 5}_{suffix}'
                            leftEdge = f'e{bsE1S1}{e1 - 1}_{bsE2A5}{e2 + 5}_{suffix}'

                """Determino se sono presenti strade a sinistra e ne calcolo l'id"""
                if suffix == '2':
                    if self.nID in [2, 3, 4]:
                        if e1 - e2 == 1:
                            leftEdge = f'e{bsE1S1}{e1 - 1}_{bsE2A5}{e2 + 5}_{suffix}'
                        if e1 - e2 == 5:
                            leftEdge = f'e{bsE1S5}{e1 - 5}_{bsE2S1}{e2 - 1}_{suffix}'
                        if e1 - e2 == -1:
                            frontEdge = f'e{bsE1A1}{e1 + 1}_{bsE2A1}{e2 + 1}_{suffix}'
                    if self.nID in [10, 15, 20]:
                        if e1 - e2 == -5:
                            frontEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A5}{e2 + 5}_{suffix}'
                        if e1 - e2 == 5:
                            leftEdge = f'e{bsE1S5}{e1 - 5}_{bsE2S1}{e2 - 1}_{suffix}'
                        if e1 - e2 == -1:
                            leftEdge = f'e{bsE1A1}{e1 + 1}_{bsE2S5}{e2 - 5}_{suffix}'
                    if self.nID in [22, 23, 24]:
                        if e1 - e2 == -5:
                            leftEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A1}{e2 + 1}_{suffix}'
                        if e1 - e2 == 1:
                            frontEdge = f'e{bsE1S1}{e1 - 1}_{bsE2S1}{e2 - 1}_{suffix}'
                        if e1 - e2 == -1:
                            leftEdge = f'e{bsE1A1}{e1 + 1}_{bsE2S5}{e2 - 5}_{suffix}'
                    if self.nID in [6, 11, 16]:
                        if e1 - e2 == -5:
                            leftEdge = f'e{bsE1A5}{e1 + 5}_{bsE2A1}{e2 + 1}_{suffix}'
                        if e1 - e2 == 1:
                            leftEdge = f'e{bsE1S1}{e1 - 1}_{bsE2A5}{e2 + 5}_{suffix}'
                        if e1 - e2 == 5:
                            frontEdge = f'e{bsE1S5}{e1 - 5}_{bsE2S5}{e2 - 5}_{suffix}'

                """Salvo le traiettorie trovate."""
                self.possibleRoutes[lane] = {'front': frontEdge, 'right': rightEdge, 'left': leftEdge}

    def findClashingRoutesForCentralStreets(self, base, obj):
        """Funzione altamente specifica per la rete utilizzata che memorizza le traiettorie incidentali interne
        all'incrocio, in particolare quelle che si hanno nell'andare diritto."""

        e1 = int(base[1:3])
        e2 = int(base[4:6])
        e3 = int(obj[1:3])
        e4 = int(obj[4:6])

        bs = f'{"0" if self.nID <= 9 else ""}'
        bsS1 = f'{"0" if self.nID - 1 <= 9 else ""}'  # come bs, ma sottrae 1
        bsA1 = f'{"0" if self.nID + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
        bsS5 = f'{"0" if self.nID - 5 <= 9 else ""}'  # come bs, ma aggiunge 5
        bsA5 = f'{"0" if self.nID + 5 <= 9 else ""}'  # come bs, ma sottrae 5

        if self.nID in [2, 3, 4]:
            if e1 - e2 == 1:
                clashingEdge1 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
            if e1 - e2 == 5:
                if e3 - e4 == -1:
                    clashingEdge1 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_1')
                    self.clashingEdges[base][obj].append(clashingEdge1)
                if e3 - e4 == 1:
                    clashingEdge1 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_1')
                    self.clashingEdges[base][obj].append(clashingEdge1)
                    clashingEdge2 = (f'e{bsS1}{self.nID + 1}_{bs}{self.nID}_2',
                                     f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_2')
                    self.clashingEdges[base][obj].append(clashingEdge2)
                    clashingEdge3 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_1')
                    self.clashingEdges[base][obj].append(clashingEdge3)
                    clashingEdge4 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_2',
                                     f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_2')
                    self.clashingEdges[base][obj].append(clashingEdge4)
            if e1 - e2 == -1:
                clashingEdge1 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)
        if self.nID in [10, 15, 20]:
            if e1 - e2 == -5:
                clashingEdge1 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)
            if e1 - e2 == 5:
                clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
            if e1 - e2 == -1:
                if e3 - e4 == 5:
                    clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_1')
                    self.clashingEdges[base][obj].append(clashingEdge1)
                    clashingEdge2 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_2',
                                     f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_2')
                    self.clashingEdges[base][obj].append(clashingEdge2)
                    clashingEdge3 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_1')
                    self.clashingEdges[base][obj].append(clashingEdge3)
                    clashingEdge4 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_2',
                                     f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_2')
                    self.clashingEdges[base][obj].append(clashingEdge4)
                if e3 - e4 == -5:
                    clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_1')
                    self.clashingEdges[base][obj].append(clashingEdge1)
        if self.nID in [22, 23, 24]:
            if e1 - e2 == -5:
                if e3 - e4 == -1:
                    clashingEdge1 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_1')
                    self.clashingEdges[base][obj].append(clashingEdge1)
                    clashingEdge2 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_2',
                                     f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_2')
                    self.clashingEdges[base][obj].append(clashingEdge2)
                    clashingEdge3 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_1')
                    self.clashingEdges[base][obj].append(clashingEdge3)
                    clashingEdge4 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_2',
                                     f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_2')
                    self.clashingEdges[base][obj].append(clashingEdge4)
                if e3 - e4 == 1:
                    clashingEdge1 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_1')
                    self.clashingEdges[base][obj].append(clashingEdge1)
            if e1 - e2 == 1:
                clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)
            if e1 - e2 == -1:
                clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
        if self.nID in [6, 11, 16]:
            if e1 - e2 == -5:
                clashingEdge1 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
            if e1 - e2 == 1:
                if e3 - e4 == 5:
                    clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_1')
                    self.clashingEdges[base][obj].append(clashingEdge1)
                    clashingEdge2 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_2',
                                     f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_2')
                    self.clashingEdges[base][obj].append(clashingEdge2)
                    clashingEdge3 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_1')
                    self.clashingEdges[base][obj].append(clashingEdge3)
                    clashingEdge4 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_2',
                                     f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_2')
                    self.clashingEdges[base][obj].append(clashingEdge4)
                if e3 - e4 == -5:
                    clashingEdge1 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_1',
                                     f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_1')
                    self.clashingEdges[base][obj].append(clashingEdge1)
            if e1 - e2 == 5:
                clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsS5}{self.nID + 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsS5}{self.nID + 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)

    def findClashingRoutesForLeftStreets(self, base, obj):
        """Funzione altamente specifica per la rete utilizzata che memorizza le traiettorie incidentali interne
        all'incrocio, in particolare quelle che si hanno nello svoltare a sinistra."""

        e1 = int(base[1:3])
        e2 = int(base[4:6])

        bs = f'{"0" if self.nID <= 9 else ""}'
        bsS1 = f'{"0" if self.nID - 1 <= 9 else ""}'  # come bs, ma sottrae 1
        bsA1 = f'{"0" if self.nID + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
        bsS5 = f'{"0" if self.nID - 5 <= 9 else ""}'  # come bs, ma aggiunge 5
        bsA5 = f'{"0" if self.nID + 5 <= 9 else ""}'  # come bs, ma sottrae 5

        if self.nID in [2, 3, 4]:
            if e1 - e2 == 1:
                clashingEdge1 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge3)
                clashingEdge4 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge4)
            if e1 - e2 == 5:
                clashingEdge1 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)
            if e1 - e2 == -1:
                clashingEdge1 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)
        if self.nID in [10, 15, 20]:
            if e1 - e2 == -5:
                clashingEdge1 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)
            if e1 - e2 == 5:
                clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge3)
                clashingEdge4 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge4)
            if e1 - e2 == -1:
                clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)
        if self.nID in [22, 23, 24]:
            if e1 - e2 == -5:
                clashingEdge1 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)
            if e1 - e2 == 1:
                clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsS1}{self.nID - 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)
            if e1 - e2 == -1:
                clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_1')
                self.clashingEdges[base][obj].append(clashingEdge3)
                clashingEdge4 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS1}{self.nID - 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge4)
        if self.nID in [6, 11, 16]:
            if e1 - e2 == -5:
                clashingEdge1 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsA1}{self.nID + 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge3)
                clashingEdge4 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge4)
            if e1 - e2 == 1:
                clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsA5}{self.nID + 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsS5}{self.nID - 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)
            if e1 - e2 == 5:
                clashingEdge1 = (f'e{bsS5}{self.nID - 5}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA1}{self.nID + 1}_2')
                self.clashingEdges[base][obj].append(clashingEdge1)
                clashingEdge2 = (f'e{bsS5}{self.nID + 1}_{bs}{self.nID}_1',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_1')
                self.clashingEdges[base][obj].append(clashingEdge2)
                clashingEdge3 = (f'e{bsS5}{self.nID + 1}_{bs}{self.nID}_2',
                                 f'e{bs}{self.nID}_{bsA5}{self.nID + 5}_2')
                self.clashingEdges[base][obj].append(clashingEdge3)

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
                if i[-1] == '1':  # front
                    self.findClashingRoutesForCentralStreets(i, k)
                if i[-1] == '2':  # left
                    self.findClashingRoutesForLeftStreets(i, k)


class FourWayJunction(Junction):
    """Caso di incrocio a quattro strade, unici utilizzati nelle simulazioni finali."""

    def __init__(self, numericID, vehicles, iP, sM, bM, groupDimension=None):
        super().__init__(numericID, vehicles, iP, sM, bM, groupDimension)
        self.edgeCalc()
        self.laneCalc()
        self.incomingLanesCalc()
        self.outgoingLanesCalc()
        self.crossingLanesCalc()
        self.laneNESOMapping()
        self.findPossibleRoutes()
        self.findClashingEdges()

        self.tails_per_lane = {lane: [] for lane in self.incomingLanes}

    def edgeCalc(self):
        """Funzione utilizzata per calcolare le strade entranti ed uscenti dall'incrocio. Funzione eseguita in fase di
        pre-processing."""

        bs = f'{"0" if self.nID <= 9 else ""}'  # determina se deve essere presente uno 0 prima degli id degli edge
        bsS1 = f'{"0" if self.nID - 1 <= 9 else ""}'  # come bs, ma sottrae 1
        bsA1 = f'{"0" if self.nID + 1 <= 9 else ""}'  # come bs, ma aggiunge 1
        bsS5 = f'{"0" if self.nID - 5 <= 9 else ""}'  # come bs, ma sottrae 5
        bsA5 = f'{"0" if self.nID + 5 <= 9 else ""}'  # come bs, ma aggiunge 5

        self.node_ids = [self.nID - 5, self.nID + 1, self.nID + 5, self.nID - 1]

        self.edges = [f'e{bs}{self.nID}_{bsS1}{self.nID - 1}', f'e{bsS1}{self.nID - 1}_{bs}{self.nID}',
                      f'e{bsA1}{self.nID + 1}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA1}{self.nID + 1}',
                      f'e{bs}{self.nID}_{bsS5}{self.nID - 5}', f'e{bsS5}{self.nID - 5}_{bs}{self.nID}',
                      f'e{bsA5}{self.nID + 5}_{bs}{self.nID}', f'e{bs}{self.nID}_{bsA5}{self.nID + 5}']

    def laneNESOMapping(self):
        """Mapping effettuato sulla base della rete utilizzata, altamente specifico per essa."""
        self.mapNESO = {'N': self.lanes[12:18], 'E': self.lanes[6:12], 'S': self.lanes[-6:], 'O': self.lanes[:6]}

    def getArrivalEdgesFromEdge(self, start):
        """Funzione che trova la lane corretta da far seguire al veicolo dati il nodo di partenza e quello di
        destinazione"""

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

    def findPossibleRoutes(self):
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

                """Determino se sono presenti strade frontali (passaggio diritto all'incrocio) e ne calcolo l'id"""
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

    def findClashingRoutesForCentralStreets(self, left, front, right, base, obj):
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

    def findClashingRoutesForLeftStreets(self, left, front, right, base, obj):
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
        for i in self.possibleRoutes:
            self.clashingEdges[i] = {self.possibleRoutes[i][j]: [] for j in self.possibleRoutes[i]
                                     if self.possibleRoutes[i][j] != ''}
        for i in self.possibleRoutes:
            for j in self.possibleRoutes[i]:
                if self.possibleRoutes[i][j] == '':
                    continue
                k = self.possibleRoutes[i][j]
                left, front, right = self.getArrivalEdgesFromEdge(int(i[1:3]))
                if i[-1] == '1':  # front
                    self.findClashingRoutesForCentralStreets(left, front, right, i, k)
                if i[-1] == '2':  # left
                    self.findClashingRoutesForLeftStreets(left, front, right, i, k)
