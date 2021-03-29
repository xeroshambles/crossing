from .auction import CooperativeAuction
from .crossingManager import CrossingManager


class CooperativeCrossingManager(CrossingManager):
    """Classe che si occupa di coordinare il passaggio dei veicoli all'incrocio, basandosi sulle aste che sono avvenute
    e che continuano ad avvenire. Le aste che fanno riferimento a questa classe sono quelle che fanno uso di un
    algoritmo cooperativo."""

    def __init__(self, junction):
        super().__init__(junction)
        # lista utilizzata per determinare quale diritto abbia diritto di muoversi nel caso dell'approccio cooperativo
        self.orderedCooperativeList = []    # lista contente liste di veicoli in clash, ordinati per precedenza.
        self.selectedLanes = []             # lista contente le liste di veicoli riattivati

    def addAuctionResult(self, auction: CooperativeAuction):
        """Funzione che aggiunge i veicoli alla lista utilizzata nel caso in cui l'algoritmo adottato sia quello
        cooperativo. Aggiunge i veicoli alla lista nell'ordine in cui li ha ricevuti, mettendo i veicoli anche in liste
        precedentemente esistenti qualora questi siano in clash con veicoli in esse presenti."""
        for i in auction.getPartecipants():
            if i not in self.partecipants:
                print('type', i, type(i))
                self.partecipants.append(i)
                self.partecipantsRoutes[i] = self.junction.fromEdgesToLanes(i)
            if i not in self.vehiclesInAuction:
                self.vehiclesInAuction.append(i)
                # i.hasPassedFreely = False
            self.bids[i] = auction.bids[i]
        newSet = []
        # con questo "quadruplo" ciclo passo in rassegna tutti i veicoli di questa e delle precedenti aste, inserendo
        # in fondo ad ogni lista i nuovi veicoli, qualora questi siano in clash con anche un solo veicolo della fila
        # in questione
        for vehiclesInALane in auction.orderedPartecipants:
            for veh in vehiclesInALane:
                # il newSet sarà una nuova "coda" di veicoli da aggiungere a self.orderedCooperativeList
                newSet.append(veh)
                veh.tryStop()
                for previousSet in self.orderedCooperativeList:
                    for otherVeh in previousSet:
                        # TODO: ANCHE SE SONO NELLA STESSA CORSIA
                        if veh in previousSet:
                            previousSet.remove(veh)
                        if self.junction.isClashing(self.getVehicleLane(veh), self.getVehicleLane(otherVeh)):
                            print(veh.getID(), self.getVehicleLane(veh))
                            previousSet.append(veh)
                            break
        self.orderedCooperativeList.append(newSet)

    def saveAuctionResults(self, auction):
        """Funzione utilizzata per salvare i risultati di un'asta nel caso di non bufferizzazione."""
        self.orderedCooperativeList.append(auction.orderedPartecipants)
        # print(f'BBB {[v.getID() for v in auction.orderedPartecipants[0]]}')
        for i in auction.partecipantsNonGrouped:
            self.vehiclesInAuction.append(i)
            self.bids[i] = auction.bids[i]
            if i not in self.partecipants:
                # print('type', i, type(i))
                self.partecipants.append(i)
                self.partecipantsRoutes[i] = self.junction.fromEdgesToLanes(i)
            if i in self.nonStoppedVehicles:
                self.nonStoppedVehicles.remove(i)
            if not i.isStopped():
                i.stopVehicle()
        # print('saving auction result of', self.junction.getID())

    def removeVehicleFromPartecipants(self, vehicle, blockAllowChange=False):
        """Funzione che si attiva quando un vincitore attraversa l'incrocio, rimuovendone ogni riferimento"""
        # print('removing', vehicle.getID(), self.junction.getID())
        # print('va', [i.getID() for i in self.getVehiclesInAuction()])
        """La prima parte della funzione gestisce informazioni relative ai dati raccolti. Andare in fondo per trovare
        un riferimento alla funzione che rimuove le informazioni dei veicoli."""

        """Controllo dei tempi, resetto i timer nel caso alcuni non fossero stati salvati. Se non sono stati salvati è 
        perchè il veicolo si è fermato per ragioni diverse da quelle del traffico esistente."""
        if vehicle.getJunctionWaitingTime() != 0 and vehicle.hasPassedFreely:
            vehicle.resetJunctionWaitingTime()
        if vehicle.getTrafficWaitingTime() != 0 and vehicle.hasPassedFreely:
            vehicle.resetTrafficWaitingTime()
        if vehicle.getMainGroupWaitingTime() == 0 != 0 and vehicle.hasPassedFreely:
            vehicle.resetMainGroupWaitingTime()
        if vehicle.getSponsorGroupWaitingTime() != 0 and vehicle.hasPassedFreely:
            vehicle.resetSponsorGroupWaitingTime()
        assert vehicle.getJunctionWaitingTime() == 0, f'junction timer error {vehicle.getJunctionWaitingTime()}, ({type(vehicle.getJunctionWaitingTime())}, {vehicle.getJunctionWaitingTime() != 0})'
        assert vehicle.getTrafficWaitingTime() == 0, f'traffic timer error {vehicle.getTrafficWaitingTime()}, ({type(vehicle.getTrafficWaitingTime())})'
        assert vehicle.getMainGroupWaitingTime() == 0, f'junction timer error {vehicle.getMainGroupWaitingTime()}, ({type(vehicle.getJunctionWaitingTime())}, {vehicle.getJunctionWaitingTime() != 0})'
        assert vehicle.getSponsorGroupWaitingTime() == 0, f'traffic timer error {vehicle.getSponsorGroupWaitingTime()}, ({type(vehicle.getTrafficWaitingTime())})'

        # ############################################################################################################ #
        """Rimozione e/o reset di informazioni effettuata sia nel caso bufferato che nel non bufferato."""

        # riprestino alcune informazioni relative al veicolo
        vehicle.numberOfAuctionAtJunction = 1
        vehicle.isSlowed = False
        if vehicle.isLaneWrong:
            # vehicle.resetTarget()
            vehicle.isLaneWrong = False
        if not blockAllowChange:
            pass
            # vehicle.allowLaneChange()

        # rimuovo il veicolo dalle strutture dati del crossing manager
        self.partecipants.remove(vehicle)
        self.bids.pop(vehicle)
        self.partecipantsRoutes.pop(vehicle)
        # if vehicle in self.nonStoppedVehicles:
        self.nonStoppedVehicles.remove(vehicle)
        if vehicle in self.vehiclesInAuction:
            self.vehiclesInAuction.remove(vehicle)
        # ############################################################################################################ #

        # gestisco i counter relativi al numero di junction attraversati e al modo in cui ciò è avvenuto
        vehicle.hasSaved_T = False
        if not vehicle.hasPassedFreely:
            # vehicle.notFreePassageCounter += 1
            vehicle.hasPassedFreely = True
        else:
            vehicle.freePassageCounter += 1
        if not vehicle.hasAvoidTraffic:
            vehicle.numberOfTimesInTraffic += 1
            vehicle.hasAvoidTraffic = True
        vehicle.junctionCounter += 1

        vehicle.hasSaved_SG = False
        if not vehicle.hasPassedFreely_groups:
            # self.vehiclesInAuction.remove(vehicle)
            # vehicle.notFreePassageCounter_groups += 1
            vehicle.hasPassedFreely_groups = True
        else:
            vehicle.freePassageCounter_groups += 1
        if not vehicle.hasAvoidTraffic_groups:
            vehicle.numberOfTimesInTraffic_groups += 1
            vehicle.hasAvoidTraffic_groups = True

        if self.junction.bufferMode:
            self.removeVehicle_buffer(vehicle)
        else:
            self.removeVehicle_noBuffer(vehicle)

    def removeVehicle_buffer(self, vehicle):
        """Gestione delle operazioni di pulizia della struttura dati dopo la rimozione di un veicolo nel caso di uso del
        buffer di veicoli. Funzione incompleta."""
        # rimuovo il veicolo dai set in cui si trova, in più rimuovo i set se questi si sono svuotati
        setToBeRemoved = []

        for currentSet in self.orderedCooperativeList:
            if vehicle in currentSet:
                currentSet.remove(vehicle)
            if not currentSet:
                setToBeRemoved.append(currentSet)
        for i in setToBeRemoved:
            self.orderedCooperativeList.remove(i)

    def removeVehicle_noBuffer(self, vehicle):
        """Gestione delle operazioni di pulizia della struttura dati dopo la rimozione di un veicolo nel caso di non
        bufferizzazione dei risultati."""
        hasBeenFound = False
        for completeList in self.orderedCooperativeList:
            for currentSet in completeList:
                if vehicle in currentSet:
                    currentSet.remove(vehicle)
                    if not currentSet:
                        completeList.remove(currentSet)
                    hasBeenFound = True
                    break
            if not completeList:
                self.orderedCooperativeList.remove(completeList)
            if hasBeenFound:
                break
        # print('va', [i.getID() for i in self.getVehiclesInAuction()])

    def updateVehicleStatus(self, vehicle):
        """Funzione che aggiorna i permessi di passaggio per un veicolo che debba attraversare ma che non possa entrare
        in un'asta. I veicoli non possono entrare in un'asta in 2 casi: o dovrebbero parteciparvi con soli veicoli
        vincitori (i veicoli vincitori non prendono più parte ad aste) oppure non necessitano di competere, hanno solo
        bisogno di un permesso di passaggio."""
        # print('updating', self.junction.getID(), vehicle.getID(), vehicle.distanceFromEndLane())
        self.partecipants.append(vehicle)
        # vehicleRoute = self.junction.fromEdgesToLanes(vehicle.getCurrentRoute())
        vehicleRoute = self.junction.fromEdgesToLanes(vehicle)
        self.partecipantsRoutes[vehicle] = self.junction.fromEdgesToLanes(vehicle)
        self.bids[vehicle] = 0  # non ha partecipato ad un'asta quindi non ha ancora fatto un'offerta.
        # se il veicolo è in clash con un veicolo di qualche set lo inserisco in fondo a quei set, stessa cosa se trovo
        # dei veicoli presenti sulla stessa lane del veicolo in questione
        if self.junction.bufferMode:
            for currentSet in self.orderedCooperativeList:
                for previousVehicle in currentSet:
                    if self.junction.isClashing(vehicleRoute, self.getVehicleLane(previousVehicle)):
                        currentSet.append(vehicle)
                        break
        # self.partecipantsRoutes[vehicle] = self.junction.fromEdgesToLanes(vehicle.getCurrentRoute())

        vehicle.stopVehicle()

    def allowCrossing(self):
        """Funzione che, dopo aver controllato i veicoli nelle posizioni di testa, da il via libera ai veicoli che, nel
        passare, non risultano essere in traiettorie incidentali, rispettando la lista delle precedenze dei veicoli"""
        if self.junction.bufferMode:
            """Vai al ramo else"""
            for i in range(len(self.orderedCooperativeList)):
                currentSet = self.orderedCooperativeList[i]
                currentSet: list
                vehiclesToBeRestarted = []
                for veh in currentSet:
                    isInAClash = False
                    if currentSet.index(veh) != 0:
                        if self.getVehicleLane(currentSet[0])[0] != self.getVehicleLane(veh)[0]:
                            isInAClash = True
                    if not isInAClash:
                        for otherSet in self.orderedCooperativeList[:i]:
                            # se il veicolo è nel set allora vuol dire che è in clash con qualche veicolo
                            if veh in otherSet:
                                isInAClash = True
                            if not isInAClash:
                                # se non è nel set controllo comunque che in esso non ci siano veicoli nella stessa corsia,
                                # nel caso questi sarebbero davanti lui quindi non gli dovrebbe essere concessa la
                                # possibilità di muoversi.
                                for otherVehicle in otherSet:
                                    if self.getVehicleLane(veh)[0] == self.getVehicleLane(otherVehicle)[0]:
                                        # print('third kind of clash', veh.getID())
                                        isInAClash = True
                                        break
                            if not isInAClash:
                                for crossingVehicles in self.getVehiclesNowCrossing():
                                    if self.junction.isClashing(self.getVehicleLane(crossingVehicles),
                                                                self.getVehicleLane(veh)):
                                        isInAClash = True
                                        break
                    if not isInAClash:
                        vehiclesToBeRestarted.append(veh)
                    else:
                        # concludo l'analisi del set perchè se questo veicolo non può muoversi allora non potranno nemmeno
                        # quelli che seguono nella lista (la lista è ordinata per priorità e posizione dei veicoli)
                        break
                for newVehicle in vehiclesToBeRestarted:
                    if newVehicle not in self.nonStoppedVehicles:
                        # print('restarting', newVehicle.getID(), '1')
                        # self.nonStoppedVehicles.append(newVehicle)
                        self.tryRestartVehicle(newVehicle)

            vehiclesInHead = [i for i in self.crossingStatus.values() if i is not None and i in self.partecipants
                              and i.distanceFromEndLane() <= 5]
            # TODO: controlla questa cosa (dovrebbe funzionare)
            vehiclesInHead.sort(key=lambda x: self.bids[x], reverse=True)
            # print([i.getID() for i in vehiclesInHead])
            for veh in vehiclesInHead:
                if veh.distanceFromEndLane() <= 10:
                    isInAClash = False
                    for otherVeh in self.nonStoppedVehicles:
                        if veh != otherVeh:
                            if self.junction.isClashing(self.getVehicleLane(veh), self.getVehicleLane(otherVeh)):
                                isInAClash = True
                                break
                    if not isInAClash:
                        if veh not in self.nonStoppedVehicles:
                            # print('restarting', veh.getID(), '2')
                            # self.nonStoppedVehicles.append(veh)
                            self.tryRestartVehicle(veh)
            for veh in self.nonStoppedVehicles:
                veh.restartVehicle()
                if veh.getJunctionWaitingTime() != 0:     # and traci.vehicle.getSpeed(i.getID()) == 0:
                    # print('saving', veh.getJunctionWaitingTime())
                    veh.saveTimePassedAtJunction()
                    veh.resetJunctionWaitingTime()
                    # print(f'time at junction saved for vehicle {veh.getID()} ({veh.getTrafficWaitingTime()})')
                if veh.getTotalWaitingTime() != 0:     # and traci.vehicle.getSpeed(i.getID()) == 0:
                    veh.saveTotalWaitingTime()
                    veh.resetTotalWaitingTime()
                    # print(f'total waited time saved for vehicle {veh.getID()} ({veh.getTrafficWaitingTime()})')
        else:
            self.allowCrossing_nonBuffered()

    def allowCrossing_nonBuffered(self):
        """Funzione che concede effettivamente la capacità di movimento ai veicoli schedulati per il passaggio."""
        # if not self.selectedLanes:
        vehiclesInHead = [i for i in self.getCrossingStatus().values() if i is not None and
                          i.distanceFromEndLane() <= 15 and i not in self.nonStoppedVehicles]
        for vehiclesInOrderedLanes in self.orderedCooperativeList:
            vehiclesInFirstLane = vehiclesInOrderedLanes[0]
            # print('BBB', [v.getID() for v in vehiclesInFirstLane])
            # veh = vehiclesInFirstLane[0]
            for veh in vehiclesInFirstLane:
                if veh in vehiclesInHead: #and not self.isInClashWithCrossingVehicles(veh):
                    veh.restartVehicle()
                    self.nonStoppedVehicles.append(veh)
                    """Salvo i tempi di attesa"""
                    if not veh.hasPassedFreely:
                        veh.saveTimePassedAtJunction()
                        # print(f'time at junction saved for vehicle {vtr.getID()} ({vtr.getTrafficWaitingTime()})')
                        veh.saveMainGroupWaitingTime()
                        # print(
                        #     f'main group waited time saved for vehicle {vtr.getID()} ({vtr.getMainGroupWaitingTime()})')
                        veh.saveTotalWaitingTime()
                        # print(
                        #     f'total waited time saved for vehicle {vtr.getID()} ({vtr.getTrafficWaitingTime()})')
                    veh.resetJunctionWaitingTime()
                    veh.resetTotalWaitingTime()
                    veh.resetMainGroupWaitingTime()
            blockingVehicle = vehiclesInOrderedLanes[0][0:3].copy()
            for veh in vehiclesInOrderedLanes[1:]:
                veh = veh[0]
                if veh in vehiclesInHead:
                    isInAClash = False
                    for wv in blockingVehicle:
                        if self.junction.isClashing(self.partecipantsRoutes[veh], self.partecipantsRoutes[wv]):
                            isInAClash = True
                            break
                    if not isInAClash:
                        veh.restartVehicle()
                        # print('restart 2', veh.getID())
                        self.nonStoppedVehicles.append(veh)
                        blockingVehicle.append(veh)
                        """Salvo i tempi di attesa"""
                        if not veh.hasPassedFreely:
                            veh.saveTimePassedAtJunction()
                            # print(f'time at junction saved for vehicle {vtr.getID()} ({vtr.getTrafficWaitingTime()})')
                            veh.saveMainGroupWaitingTime()
                            # print(
                            #     f'main group waited time saved for vehicle {vtr.getID()} ({vtr.getMainGroupWaitingTime()})')
                            veh.saveTotalWaitingTime()
                            # print(
                            #     f'total waited time saved for vehicle {vtr.getID()} ({vtr.getTrafficWaitingTime()})')
                        veh.resetJunctionWaitingTime()
                        veh.resetTotalWaitingTime()
                        veh.resetMainGroupWaitingTime()
                    # else:
                    #     break
                                # print(
                                #     f'main group waited time saved for vehicle {veh.getID()} ({veh.getMainGroupWaitingTime()})')

        blockingVehicles = self.getBlockingVehicles()
        vehiclesWithRights = [x for j in self.orderedCooperativeList for i in j for x in i]
        """Il seguente blocco di codice è utilizzabile se si vogliono implementare politiche che blocchino il meccanismo
        di ottimizzazione in determinati frangenti. È commentato poichè non utilizzato nelle simulazioni finali."""
        isToBeBlocked = False
        # if vehiclesWithRights:
        # if self.junction.maxDimensionOfGroups != 1:
        #     if 0 < len(vehiclesWithRights) <= 2:
        #         isToBeBlocked = True
        # if len(vehiclesWithRights) != 1:
        if not isToBeBlocked:
            # if vehiclesWithRights and self.junction.maxDimensionOfGroups != 1:
            # if len(blockingVehicles) >= 3:
            if len(blockingVehicles) >= 5 and self.isAFirstVehicleTraversing(vehiclesWithRights):
                vehiclesNotInAuction = [i for i in vehiclesInHead if i not in self.vehiclesInAuction]
                restartableVehicles = self.getRestartableVehicles(vehiclesNotInAuction, blockingVehicles)
                if restartableVehicles:
                    for vtr in self.createSingularAuction(restartableVehicles):
                        vtr.restartVehicle()
                        # print('restart 3', vtr.getID())
                        self.nonStoppedVehicles.append(vtr)
                        """Salvo i tempi di attesa"""
                        if not vtr.hasPassedFreely:
                            vtr.saveTimePassedAtJunction()
                            # print(f'time at junction saved for vehicle {vtr.getID()} ({vtr.getTrafficWaitingTime()})')
                            vtr.saveMainGroupWaitingTime()
                            # print(
                            #     f'main group waited time saved for vehicle {vtr.getID()} ({vtr.getMainGroupWaitingTime()})')
                            vtr.saveTotalWaitingTime()
                            # print(
                            #     f'total waited time saved for vehicle {vtr.getID()} ({vtr.getTrafficWaitingTime()})')
                        vtr.resetJunctionWaitingTime()
                        vtr.resetTotalWaitingTime()
                        vtr.resetMainGroupWaitingTime()
                            # print(
                                # f'main group waited time saved for vehicle {vtr.getID()} ({vtr.getMainGroupWaitingTime()})')
            else:
                vehiclesInHead = [i for i in self.getCrossingStatus().values() if i is not None
                                  and i.distanceFromEndLane() < 15]
                vehiclesInHead.extend([i for i in self.getVehiclesNowCrossing() if i not in vehiclesInHead])
                for veh in vehiclesInHead:
                    if veh.distanceFromEndLane() < 5 and veh not in self.nonStoppedVehicles:
                        isInAClash = False
                        for otherVeh in vehiclesInHead:
                            if veh != otherVeh:
                                if self.junction.isClashing(self.partecipantsRoutes[veh],
                                                            self.partecipantsRoutes[otherVeh]):
                                    isInAClash = True
                                    break
                        if not isInAClash:
                            veh.restartVehicle()
                            self.nonStoppedVehicles.append(veh)
                            """Salvo i tempi di attesa"""
                            if not veh.hasPassedFreely:
                                veh.saveTimePassedAtJunction()
                                # print(f'time at junction saved for vehicle {vtr.getID()} ({vtr.getTrafficWaitingTime()})')
                                veh.saveMainGroupWaitingTime()
                                # print(
                                #     f'main group waited time saved for vehicle {vtr.getID()} ({vtr.getMainGroupWaitingTime()})')
                                veh.saveTotalWaitingTime()
                                # print(
                                #     f'total waited time saved for vehicle {vtr.getID()} ({vtr.getTrafficWaitingTime()})')
                            veh.resetJunctionWaitingTime()
                            veh.resetTotalWaitingTime()
                            veh.resetMainGroupWaitingTime()

    def getBlockingVehicles(self):
        """Funzione che calcola i veicoli bloccanti per gli altri veicoli in testa"""
        blockingVehicles = self.nonStoppedVehicles.copy()
        for l in self.orderedCooperativeList:
            vehiclesInFirstLane = l[0]
            # if len(vehiclesInFirstLane) > 2:
            blockingVehicles.extend([i for i in vehiclesInFirstLane[0:3] if i not in blockingVehicles])
        # blockingVehicles.extend([i for i in self.getVehiclesNowCrossing() if i not in blockingVehicles])
        return blockingVehicles

    def getRestartableVehicles(self, vehiclesNotInAuction, blockingVehicles):
        """Funzione che trova i veicoli che potrebbero muoversi"""
        restartableVehicles = []
        for nwv in vehiclesNotInAuction:
            isInAClash = False
            # for rv in self.nonStoppedVehicles:
            for rv in blockingVehicles:
                # print('rv', rv.getID())
                if self.junction.isClashing(self.partecipantsRoutes[nwv],
                                            self.partecipantsRoutes[rv]):
                    isInAClash = True
                    break
            if not isInAClash:
                restartableVehicles.append(nwv)
        return restartableVehicles

    def tryRestartVehicle(self, veh):
        """Funzione legata al caso bufferato.
        Funzione da utilizzare quando si cerca di sbloccare un veicolo, per dare la giusta priorità ad ogni veicolo e
        non rischiare di creare incidenti. Tale funzione si applica ai veicoli senza veicoli a cui dare la precedenza,
        e controlla che fra i veicoli con possibilità di movimento non c'è ne siano in traiettorie incidentali; se c'è
        ne allora: se il veicolo da inserire è un vincitore si toglie qualunque veicolo in CT, senza distinzioni (a meno
        di impossibilità di fermarsi del veicolo da rimuovere), invece se il veicolo è perdente allora si decide quale
        ha più priorità, procedendo o meno alla rimozione."""
        crossingVehicles = self.getVehiclesNowCrossing()
        isInAClash = False
        for crossingVehicle in crossingVehicles:
            if self.junction.isClashing(self.getVehicleLane(veh), self.getVehicleLane(crossingVehicle)):
                isInAClash = True
                break
        if not isInAClash:
            if veh not in self.nonStoppedVehicles:
                self.nonStoppedVehicles.append(veh)