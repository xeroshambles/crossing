from abc import abstractmethod, ABC

import traci

from trafficElements.auction import CompetitiveAuction


class CrossingManager(ABC):
    """Classe che si occupa di coordinare il passaggio dei veicoli all'incrocio, basandosi sulle aste che sono avvenute
    e che continuano ad avvenire."""

    def __init__(self, junction):
        # dizionario contente tutti i veicoli che vogliono attraversare l'incrocio con associati i veicoli di cui devono
        # attendere il passaggio.
        self.junction = junction
        self.partecipants = []
        self.bids = {}
        self.partecipantsRoutes = {}
        # il seguente dizionario viene aggiornato ad ogni step e contiene i veicoli allo sbocco sull'incrocio di ogni
        # corsia
        self.crossingStatus = {}
        # elenco di veicoli che negli step precedenti sono stati riattivati
        self.nonStoppedVehicles = []
        self.vehiclesInAuction = []

    @abstractmethod
    def addAuctionResult(self, auction: CompetitiveAuction):
        """Funzione che aggiorna lo stato dei permessi di passaggio in seguito allo svolgimento di un'asta"""
        pass

    # @abstractmethod
    # def saveAuctionResult(self, auction: CompetitiveAuction):
    #     """Funzione che salva lo stato dei permessi di passaggio in seguito allo svolgimento di un'asta"""
    #     pass

    @abstractmethod
    def removeVehicleFromPartecipants(self, vehicle, blockAllowChange=False):
        """Funzione che si attiva quando un vincitore attraversa l'incrocio, rimuovendone ogni riferimento"""
        pass

    @abstractmethod
    def updateVehicleStatus(self, vehicle):
        """Funzione che aggiorna i permessi di passaggio per un veicolo che debba attraversare ma che non possa entrare
        in un'asta. I veicoli non possono entrare in un'asta in 2 casi: o dovrebbero parteciparvi con soli veicoli
        vincitori (i veicoli vincitori non prendono più parte ad aste) oppure non necessitano di competere, hanno solo
        bisogno di un permesso di passaggio."""
        pass

    @abstractmethod
    def allowCrossing(self):
        # TODO: - ricontrollare con attenzione: soprattutto gli if con i self.precedences
        """Funzione che, dopo aver controllato i veicoli nelle posizioni di testa, da il via libera ai veicoli che, nel
        passare, non risultano essere in traiettorie incidentali, rispettando la lista delle precedenze dei veicoli"""
        pass

    def tryRestartVehicle(self, veh):
        """Funzione da utilizzare quando si cerca di sbloccare un veicolo, per dare la giusta priorità ad ogni veicolo e
        non rischiare di creare incidenti. Tale funzione si applica ai veicoli senza veicoli a cui dare la precedenza,
        e controlla che fra i veicoli con possibilità di movimento non c'è ne siano in traiettorie incidentali; se c'è
        ne allora: se il veicolo da inserire è un vincitore si toglie qualunque veicolo in CT, senza distinzioni (a meno
        di impossibilità di fermarsi del veicolo da rimuovere), invece se il veicolo è perdente allora si decide quale
        ha più priorità, procedendo o meno alla rimozione."""
        pass

    def updateCrossingStatus(self, vehicles):
        """Funzione che trova i veicoli attualmente in testa ad ogni corsia. Questi saranno i veicoli papabili per un
        attraversamento"""
        # con il seguente ciclo determino i veicoli attualmente in testa alle corsie che vanno verso l'incrocio
        vehiclesInHead = []
        otherVehicles = []
        for lane in self.junction.getIncomingLanes():
            # il veicolo più vicino all'incrocio è quello indicato all'ultima posizione della lista ottenuta attraverso
            # la funzione traci.lane.getLastStepVehicleIDs(idLane)
            laneQueueTemp = traci.lane.getLastStepVehicleIDs(lane)
            laneQueue = []
            for j in laneQueueTemp:
                # try che gestisce un errore che può verificarsi dopo il superamento della soglia di fine simulazione,
                # per cui dei veicoli potrebbero ancora trovarsi nella simulazione e quindi essere restituiti da traci
                # pur essendo già stati rimossi da tutte le altre strutture dati.
                try:
                    laneQueue.append(vehicles[j])
                except:
                    pass
            # prendendo l'ultimo veicolo seleziono quello in testa alla corsia.
            if laneQueue:
                # self.crossingStatus[i] = vehicles[laneQueue[-1]]
                self.crossingStatus[lane] = laneQueue[-1]
                vehiclesInHead.append(laneQueue[-1])
                otherVehicles += laneQueue[:-1]
            else:
                self.crossingStatus[lane] = None
        vehiclesPassed = []
        for i in self.getCurrentPartecipants():
            # visto che questo ciclo passa in rassegna tutti i veicoli ad un incrocio ho aggiunto queste 2 righe che
            # impediscono ad un veicolo di cambiare corsia nel momento in cui si trovano troppo vicini all'incrocio
            # TODO: da tenere?
            if not i.isSlowed:
                i.isSlowed = True
                traci.vehicle.slowDown(i.getID(), 3, 3)     # TODO: 8 o 4?
            if i.isAllowedLaneChange() and i.distanceFromEndLane() < 15:
                i.forbidLaneChange()
            # print('control', traci.vehicle.getLaneID(i.getID())[1:3], self.junction.getNumericID())
            # se il veicolo si trova su una corsia il cui primo numero indicato è quello dell'id dell'incrocio allora
            # il veicolo si trova su di una corsia uscente e può essere rimosso dal crossing manager
            if traci.vehicle.getLaneID(i.getID()):
                if traci.vehicle.getLaneID(i.getID())[0] == 'e' and \
                        int(traci.vehicle.getLaneID(i.getID())[1:3]) == self.junction.getNumericID():
                    vehiclesPassed.append(i)
        for i in vehiclesPassed:
            self.removeVehicleFromPartecipants(i)

            """codice utilizzato per la distribuzione del traffico."""
            if self.junction.isFrontalTrajectory(i):
                currentLane = int(i.getCurrentLane()[-1])
                newLane = 0 if currentLane == 1 else 1
                nlaneID = list(i.getCurrentLane())
                nlaneID[-1] = str(newLane)
                nlaneID = ''.join(nlaneID)
                if len(traci.lane.getLastStepVehicleIDs(i.getCurrentLane())) >= 2*len(traci.lane.getLastStepVehicleIDs(nlaneID)):
                    currentLane = int(i.getCurrentLane()[-1])
                    newLane = 0 if currentLane == 1 else 1
                    traci.vehicle.changeLane(i.getID(), newLane, 10)
                    i.forbidLaneChange()

        for i in self.getCurrentPartecipants():
            if traci.vehicle.getLaneID(i.getID())[0] == 'e':
                # if traci.vehicle.getLaneID(i.getID())[0] == 'e':
                self.partecipantsRoutes[i] = self.junction.fromEdgesToLanes(i)

    def getVehiclesNowCrossing(self):
        """Funzione che restituisce i veicoli in fase di attraversamento."""
        vehiclesCrossing = []
        for i in self.getCurrentPartecipants():
            # if traci.vehicle.getLaneID(i.getID())[:4] == f':{self.junction.getID()}':
            if i.getCurrentLane()[:4].replace('_', '') == f':{self.junction.getID()}':
                vehiclesCrossing.append(i)
        # for i in vehiclesCrossing:
        #     for j in vehiclesCrossing:
        #         if i != j:
        #             if self.junction.isClashing(self.getVehicleLane(j), self.getVehicleLane(i)):
                        # print('error: CT', i.getID(), j.getID())
        return vehiclesCrossing

    def getAverageSpeedOfThePartecipants(self):
        """Funzione che restituisce la velocità media dei partecipanti. Inutilizzata nelle simulazioni finali."""
        speed = 0
        for veh in self.getCurrentPartecipants():
            speed += traci.vehicle.getSpeed(veh.getID())
        try:
            return speed / len(self.getCurrentPartecipants())
        except:
            return 0.0

    def getNonStoppedVehicles(self):
        """Funzione che restituisce i veicoli con diritti di movimento."""
        return self.nonStoppedVehicles

    def getCurrentPartecipants(self):
        """Funzione che restituisce i veicoli salvati dal crossing manager."""
        return self.partecipants

    def getCrossingStatus(self):
        """Funzione che restituisce il dizionario contenente i veicoli in testa alle rispettive corsie."""
        return self.crossingStatus

    def getVehiclesInAuction(self):
        """Funzione che restituisce i veicoli in un'asta."""
        return self.vehiclesInAuction

    def getVehicleLane(self, vehicle):
        """Funzione che restituisce la route seguita dal veicolo passato in argomento"""
        # if vehicle in self.getPrecedences().keys():
        #     return self.partecipantsRoutes[vehicle]
        # else:
        #     return None
        if vehicle in self.getCurrentPartecipants():
            return self.partecipantsRoutes[vehicle]
        else:
            return None

    def isVehicleOnTheRightPath(self, vehicle):
        """Funzione che restituisce False se il veicolo passato non ha modo di raggiungere l'edge prefissato dalla
        posizione in cui si trova, True altrimenti"""
        currentRoute = vehicle.getCurrentRoute()
        currentEdge = (int(currentRoute[0][1:3]), int(currentRoute[0][4:6]))
        nextEdge = (int(currentRoute[1][1:3]), int(currentRoute[1][4:6]))
        if abs(currentEdge[0] - currentEdge[1]) == abs(nextEdge[0] - nextEdge[1]):
            return True  # perchè il veicolo deve andare dritto quindi ogni corsia va bene
        # pathToBeFollowed = self.junction.fromEdgesToLanes(currentRoute)
        pathToBeFollowed = self.junction.fromEdgesToLanes(vehicle)
        currentLane = traci.vehicle.getLaneID(vehicle.getID())
        if pathToBeFollowed[0] != currentLane:
            print('error: correct edge is not reachable')
            return False
        return True

    def createSingularAuction(self, restartableVehicles):
        """Funzione che organizza aste a passaggio singolo per decidere chi far passare fra una serie di veicoli in
        clash."""
        clashingLists = []
        clashingHeads = []
        vehiclesInHead = [i for i in self.getCrossingStatus().values() if i is not None and
                          i.distanceFromEndLane() <= 15]
        vehiclesToBeRestarted = []
        vehToBeRemoved = []

        # ############################################################################################################ #
        """Impedisce ai veicoli alle spalle dei vincitori di prendere parte ad aste a passaggio singolo, per non 
        avvantaggiarli."""
        for veh in restartableVehicles:
            toBeChecked = False
            for rv in self.nonStoppedVehicles:
                if self.partecipantsRoutes[rv][0] == veh.getCurrentLane():
                    toBeChecked = True
            if toBeChecked:
                vehToBeRemoved.append(veh)
                isInAClash = False
                for vh in vehiclesInHead:
                    if self.junction.isClashing(self.partecipantsRoutes[veh], self.partecipantsRoutes[vh]):
                        isInAClash = True
                        break
                if not isInAClash:
                    vehiclesToBeRestarted.append(veh)
        for v in vehToBeRemoved:
            restartableVehicles.remove(v)
        # ############################################################################################################ #

        # ############################################################################################################ #
        """Trovo i veicoli che devono prendere parte ad un'asta."""
        for veh in restartableVehicles:
            for otherVeh in restartableVehicles[restartableVehicles.index(veh) + 1:]:

                if self.junction.isClashing(self.junction.fromEdgesToLanes(veh),
                                            self.junction.fromEdgesToLanes(otherVeh)):
                    vehInCH = True
                    otherVehInCH = True
                    if veh not in clashingHeads:
                        clashingHeads.append(veh)
                        vehInCH = False
                    if otherVeh not in clashingHeads:
                        clashingHeads.append(otherVeh)
                        otherVehInCH = False
                    if vehInCH and not otherVehInCH:
                        for cl in clashingLists:
                            for couple in cl:
                                # print('1 check', otherVeh.getID(), couple[0][0].getID())
                                if veh == couple[0][0]:
                                    cl.append([[otherVeh], self.findSponsors(otherVeh)])
                                    break
                    elif not vehInCH and otherVehInCH:
                        for cl in clashingLists:
                            for couple in cl:
                                # print('2 check', veh.getID(), couple[0][0].getID())
                                if otherVeh == couple[0][0]:
                                    cl.append([[veh], self.findSponsors(veh)])
                                    break
                    elif vehInCH and otherVehInCH:
                        cls = []
                        for v in [veh, otherVeh]:
                            for cl in clashingLists:
                                for couple in cl:
                                    # print('3 check', v.getID(), couple[0][0].getID())
                                    if v == couple[0][0]:
                                        # print('cl', cl)
                                        cls.append(cl)
                                        break
                        # print('cls', cls)
                        # print('ch', [i.getID() for i in clashingHeads])
                        # cls = list(*cls)
                        if cls[0] != cls[1]:
                            # print('cls[0]', cls[0], '\n', 'cls[1]', cls[1])
                            clashingLists.remove(cls[0])
                            clashingLists.remove(cls[1])
                            cls[0].extend(cls[1])
                            clashingLists.append(cls[0])
                    elif not vehInCH and not otherVehInCH:
                        # print('4 rrr check', veh.getID(), otherVeh.getID())
                        cl = [[[veh], self.findSponsors(veh)], [[otherVeh], self.findSponsors(otherVeh)]]
                        clashingLists.append(cl)
        """Inserisco fra i veicoli da riavviare quelli che non sono in clash con nessun altro veicolo."""
        vehiclesToBeRestarted.extend([i for i in restartableVehicles if i not in clashingHeads])
        # ############################################################################################################ #
        """Organizzo tante aste a passaggio singolo quante sono le clashing list"""
        for cl in clashingLists:
            auction = CompetitiveAuction(cl, self.junction, oV=True, instantPay=self.junction.payMode,
                                         bufferMode=self.junction.bufferMode)
            vehiclesToBeRestarted.append(auction.getWinners()[0])
        # print(f'vehicles to be restarted of {self.junction.getID()}')
        # for veh in vehiclesToBeRestarted:
            # print(veh.getID())
        return vehiclesToBeRestarted

    def findSponsors(self, vehicle):
        """Funzione che trova gli sponsor per i veicoli di testa partecipanti all'asta"""
        vehicles = self.junction.vehicles
        ls = [vehicles[i] for i in traci.lane.getLastStepVehicleIDs(vehicle.getCurrentLane())
              if vehicles[i].checkPosition(self.junction)]
        # print([i.getID() for i in ls])
        # print(vehicle.getID())
        if vehicle in ls:
            ls.remove(vehicle)
        return ls

    def isInClashWithCrossingVehicles(self, wv):
        """Funzione che determina se il veicolo in argomento sia in clash con i veicoli che stanno attraversando"""
        isInAClash = False
        for cv in self.getVehiclesNowCrossing():
            if self.junction.isClashing(self.partecipantsRoutes[cv],
                                        self.partecipantsRoutes[wv]):
                isInAClash = True
                break
        return isInAClash

    def isAFirstVehicleTraversing(self, vehiclesWithRights):
        """Funzione che restituisce True se almeno uno dei vincitori dell'asta generale sta attraversando."""
        isPassing = False
        for vr in vehiclesWithRights:
            if vr in self.getVehiclesNowCrossing():
                isPassing = True
                break
        return isPassing
