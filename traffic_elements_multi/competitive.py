from .auction import CompetitiveAuction
from .crossingManager import CrossingManager

import traci


class CompetitiveCrossingManager(CrossingManager):
    """Classe che si occupa di coordinare il passaggio dei veicoli all'incrocio, basandosi sulle aste che sono avvenute
    e che continuano ad avvenire. Le aste che fanno riferimento a questa classe sono quelle che fanno uso di un
    algoritmo competitivo."""

    def __init__(self, junction):
        super().__init__(junction)
        # dizionario contente tutti i veicoli che vogliono attraversare l'incrocio con associati i veicoli di cui devono
        # attendere il passaggio.
        # self.junction = junction
        # self.partecipants = []
        self.precedences = {}
        self.vehiclesInAuction = []
        self.currentWinners = []
        self.currentLosers = []
        # il seguente dizionario tiene in memoria le liste dei veicoli vincitori che hanno partecipato assieme, ordinate
        # temporalmente.
        self.winnersLanes = {}

    # ################################################################################################################ #
    """Le prossime funzioni sono relative al caso bufferato e sono incomplete."""
    def addAuctionResult_(self, auction: CompetitiveAuction):
        """Funzione che aggiorna lo stato dei permessi di passaggio in seguito allo svolgimento di un'asta"""
        # print('adding an auction')
        for i in auction.getPartecipants():
            if i not in self.partecipants:
                # non aggiungo i veicoli ai partecipanti per poter eseguire l'ereditarietà delle precedenze di sotto
                # self.partecipants.append(i)
                self.precedences[i] = []
                # self.partecipantsRoutes[i] = self.junction.fromEdgesToLanes(i.getCurrentRoute())
                self.partecipantsRoutes[i] = self.junction.fromEdgesToLanes(i)
            if i not in self.vehiclesInAuction:
                self.vehiclesInAuction.append(i)
                # i.hasPassedFreely = False
            self.bids[i] = auction.bids[i]
        # per far ereditare le precedenze attivare la funzione
        self.inheritPrecedences(auction)
        for i in auction.getWinners():
            if i in self.currentLosers:
                self.currentLosers.remove(i)
            if i not in self.partecipants:
                self.partecipants.append(i)
            if 'placeholder' in self.precedences[i]:
                self.precedences[i].remove('placeholder')
            # TODO: visto il winnersLane si può pensare di non salvare esplicitamente i vincitori
            # bisect.insort(self.winnersLanes[i.getCurrentLane()], i, key)
            self.winnersLanes[i.getCurrentLane()].append(i)
            self.currentWinners.append(i)
        for i in auction.getLosers():
            if i not in self.partecipants:
                self.partecipants.append(i)
            if i not in self.currentLosers:
                self.currentLosers.append(i)
            if self.precedences[i]:
                # se viene passato un veicolo che ha perso una precedente asta allora aggiungo i nuovi veicoli che
                # deve attendere
                # self.precedences[i] += [j for j in auction.getWinners() if self.junction.isClashing(
                #     self.junction.fromEdgesToLanes(i.getCurrentRoute()), self.partecipantsRoutes[j])]
                self.precedences[i] += [j for j in auction.getWinners() if self.junction.isClashing(
                    self.junction.fromEdgesToLanes(i), self.partecipantsRoutes[j])]
            else:
                # self.precedences[i] = [j for j in auction.getWinners() if self.junction.isClashing(
                #     self.junction.fromEdgesToLanes(i.getCurrentRoute()), self.partecipantsRoutes[j])]
                self.precedences[i] = [j for j in auction.getWinners() if self.junction.isClashing(
                    self.junction.fromEdgesToLanes(i), self.partecipantsRoutes[j])]
        # se esistono già dei vincitori allora devo decidere chi dei 2 passerà per primo:
        for i in range(len(self.currentWinners)):
            veh = self.currentWinners[i]
            # itero su tutti i veicoli vincitori eccetto il fissato i
            for otherVeh in self.currentWinners[:i] + self.currentWinners[i + 1:]:
                # se i 2 veicoli messi a confronto non sono sullo stesso edge
                if self.partecipantsRoutes[veh][0][:-2] != self.partecipantsRoutes[otherVeh][0][:-2]:
                    # controllo che nessuno dei 2 veicoli contenga l'altro nella propria lista delle precedenze
                    # (se uno è nella lista delle precedenze dell'altro allora l'ordinamento è già stato fatto)
                    if otherVeh not in self.precedences[veh] and veh not in self.precedences[otherVeh]:
                        # se fra questi 2 vincitori c'è un clash
                        if self.junction.isClashing(self.partecipantsRoutes[veh], self.partecipantsRoutes[otherVeh]):
                            # prendo la somma accumulata dai veicoli in corsia accodati al veicolo considerato
                            laneVeh = self.partecipantsRoutes[veh][0]
                            laneOtherVeh = self.partecipantsRoutes[otherVeh][0]
                            bidsLaneVeh = 0
                            bidsLaneOtherVeh = 0
                            for j in self.currentWinners:
                                if self.partecipantsRoutes[j][0] == laneVeh and \
                                        j.distanceFromEndLane() >= veh.distanceFromEndLane():
                                    bidsLaneVeh += self.bids[j]
                                if self.partecipantsRoutes[j][0] == laneOtherVeh and \
                                        j.distanceFromEndLane() >= otherVeh.distanceFromEndLane():
                                    print(j.getID(), self.bids[j], end=' ,')
                                    bidsLaneOtherVeh += self.bids[j]
                            losingVehicle = veh if bidsLaneVeh < bidsLaneOtherVeh else otherVeh
                            # if bidsLaneVeh == bidsLaneOtherVeh:
                            # seleziono come veicolo perdente quello con una offerta minore
                            # losingVehicle = veh if self.bids[veh] < self.bids[otherVeh] else otherVeh
                            if self.bids[veh] == self.bids[otherVeh]:
                                # se le loro offerte sono uguali seleziono come vincitore il veicolo che è meno
                                # distante dall'incrocio
                                losingVehicle = veh if veh.distanceFromEndLane() > otherVeh.distanceFromEndLane() \
                                    else otherVeh
                            winningVehicle = veh if losingVehicle != veh else otherVeh
                            if not losingVehicle.isStoppable():
                                # faccio valere le regole precedenti solo se il veicolo perdente non è troppo a
                                # ridosso dell'incrocio, altrimenti questo non potrà fermarsi
                                losingVehicle, winningVehicle = winningVehicle, losingVehicle
                            self.precedences[losingVehicle].append(winningVehicle)
        for i in auction.getPartecipants():
            if not i.isStopped():
                i.tryStop()
            if i in self.nonStoppedVehicles:
                self.nonStoppedVehicles.remove(i)

    def addAuctionResult(self, auction: CompetitiveAuction):
        """Funzione che aggiorna lo stato dei permessi di passaggio in seguito allo svolgimento di un'asta"""
        # print('adding an auction')
        for i in auction.getPartecipants():
            if i not in self.partecipants:
                # non aggiungo i veicoli ai partecipanti per poter eseguire l'ereditarietà delle precedenze di sotto
                # self.partecipants.append(i)
                self.precedences[i] = []
                self.partecipantsRoutes[i] = self.junction.fromEdgesToLanes(i)
                self.partecipants.append(i)
            if i not in self.vehiclesInAuction:
                self.vehiclesInAuction.append(i)
                # i.hasPassedFreely = False
            if 'placeholder' in self.precedences[i]:
                self.precedences[i].remove('placeholder')
            if i in auction.getWinners():
                if i in self.currentLosers:
                    self.currentLosers.remove(i)
                # self.winnersLanes[i.getCurrentLane()].append(i)
                self.currentWinners.append(i)
            self.winnersLanes[auction.getWinners()[0].getCurrentLane()].append(auction.getWinners().copy())
            if i in auction.getLosers():
                if i not in self.currentLosers:
                    self.currentLosers.append(i)
            self.bids[i] = auction.bids[i]
        for i in auction.getLosers():
            self.precedences[i] += [j for j in auction.getWinners()
                                    if self.junction.isClashing(self.junction.fromEdgesToLanes(i),
                                                                self.partecipantsRoutes[j])]
        for i in auction.getPartecipants():
            if not i.isStopped():
                i.tryStop()
            if i in self.nonStoppedVehicles:
                self.nonStoppedVehicles.remove(i)
    # ################################################################################################################ #

    def saveAuctionResults(self, auction: CompetitiveAuction):
        """Funzione utilizzata per salvare i risultati di un'asta nel caso di non bufferizzazione e quindi di non
        necessità di un merge dei vincitori. Evita di utilizzare la struttura delle precedenze, in modo da risparmiare
        complessità computazionale."""
        winners = auction.getWinners()
        losers = auction.getLosers()
        self.winnersLanes[winners[0].getCurrentLane()] = winners
        # print(f'BBB {[v.getID() for v in winners]}')
        for i in winners:
            if i not in self.partecipants:
                self.partecipants.append(i)
                if not i.isStopped():
                    i.stopVehicle()
                # print('saving', i.getID(), 'sar', self.junction.getID(), 'w', i.distanceFromEndLane())
                self.partecipantsRoutes[i] = self.junction.fromEdgesToLanes(i)
            if i in self.currentLosers:
                self.removeLoser(i)
            self.addWinner(i)
            self.precedences[i] = losers
        #     print(f'precedences of veh {i.getID()}: {[j.getID() for j in self.precedences[i]]}')
        # print([i.getID() for i in self.getCurrentWinners()], 'junction', self.junction.getID())
        for i in losers:
            self.addLoser(i)
            self.partecipantsRoutes[i] = self.junction.fromEdgesToLanes(i)
            i.nVehiclesToWait += len(winners)
            if i not in self.partecipants:
                self.partecipants.append(i)
                if not i.isStopped():
                    i.stopVehicle()
                self.precedences[i] = []
                # print('saving', i.getID(), 'sar', self.junction.getID(), 'l', i.distanceFromEndLane())

        # print('saving auction result of', self.junction.getID())

    def removeVehicleFromPartecipants(self, vehicle, blockAllowChange=False):
        """Funzione che si attiva quando un vincitore attraversa l'incrocio, rimuovendone ogni riferimento"""
        # print('removing', vehicle.getID(), self.junction.getID())
        """Eccetto per un piccolo frammento di codice, la prima parte della funzione gestisce informazioni relative ai 
        dati raccolti. Andare in fondo per trovare un riferimento alla funzione che rimuove le informazioni dei 
        veicoli."""

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
        assert vehicle.getJunctionWaitingTime() == 0, f'junction timer error {vehicle.getJunctionWaitingTime()}, ' \
                                                      f'({type(vehicle.getJunctionWaitingTime())}, ' \
                                                      f'{vehicle.getJunctionWaitingTime() != 0})'
        assert vehicle.getTrafficWaitingTime() == 0, f'traffic timer error {vehicle.getTrafficWaitingTime()}, ' \
                                                     f'({type(vehicle.getTrafficWaitingTime())})'

        # ############################################################################################################ #
        """Rimozione e/o reset di informazioni effettuata sia nel caso bufferato che nel non bufferato."""
        vehicle.numberOfAuctionAtJunction = 1
        vehicle.isSlowed = False
        if vehicle.isLaneWrong:
            vehicle.resetTarget()
            vehicle.isLaneWrong = False
        if not blockAllowChange:
            pass
            # vehicle.allowLaneChange()
        self.partecipants.remove(vehicle)
        # ############################################################################################################ #

        vehicle.hasSaved_T = False
        if not vehicle.hasPassedFreely:
            # self.vehiclesInAuction.remove(vehicle)
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
        if vehicle in self.vehiclesInAuction:
            # print('removing from auction', vehicle.getID(), vehicle.getCurrentLane())
            self.vehiclesInAuction.remove(vehicle)
            # print('a v', [i.getID() for i in self.vehiclesInAuction if i is not None])
        self.precedences.pop(vehicle)
        for precedencesList in self.precedences.values():
            if vehicle in precedencesList:
                precedencesList.remove(vehicle)
        self.bids.pop(vehicle)
        listToBeRemoved = []
        for lis in self.winnersLanes[self.partecipantsRoutes[vehicle][0]]:
            if vehicle in lis:
                lis.remove(vehicle)
            if not lis:
                listToBeRemoved.append(lis)
        for lis in listToBeRemoved:
            self.winnersLanes[self.partecipantsRoutes[vehicle][0]].remove(lis)
        self.partecipantsRoutes.pop(vehicle)
        if vehicle in self.nonStoppedVehicles:
            self.nonStoppedVehicles.remove(vehicle)
        if vehicle in self.currentWinners:
            self.currentWinners.remove(vehicle)
        else:
            self.currentLosers.remove(vehicle)

    def removeVehicle_noBuffer(self, vehicle):
        """Gestione delle operazioni di pulizia della struttura dati dopo la rimozione di un veicolo nel caso di non
        bufferizzazione dei risultati."""
        # print('va', [i.getID() for i in self.getVehiclesInAuction()])
        if vehicle in self.currentWinners:
            # print('wv', [i.getID() for i in self.getCurrentWinners()])
            # print(f'current losers: {[j.getID() for j in self.currentLosers]}')
            vehToBeRemoved = []
            for loser in self.currentLosers:
                # print(f'precedences of {vehicle.getID()} before removal: {[j.getID() for j in self.precedences[vehicle]]}')
                # print(loser.getID())
                if loser in self.precedences[vehicle]:
                    # print(loser.getID())
                    loser.nVehiclesToWait -= 1
                if loser.nVehiclesToWait == 0:
                    # print(f'removing {loser.getID()} from current losers list')
                    # self.removeLoser(loser)
                    vehToBeRemoved.append(loser)
            for loser in vehToBeRemoved:
                # print(f'removing {loser.getID()} from current losers list')
                self.removeLoser(loser)
            self.removeWinner(vehicle)
            # print('lv', [i.getID() for i in self.getCurrentLosers()])
        else:
            # print(vehicle.getID())
            # print('lv', [i.getID() for i in self.currentLosers])
            if vehicle in self.currentLosers:
                # self.currentLosers.remove(vehicle)
                self.removeLoser(vehicle)
                vehicle.nVehiclesToWait = 0
                # print('lv', [i.getID() for i in self.getCurrentLosers()])
                # if vehicle in self.vehiclesInAuction:
                #     self.vehiclesInAuction.remove(vehicle)
        lane = self.partecipantsRoutes[vehicle][0]
        if lane in self.winnersLanes:
            if vehicle in self.winnersLanes[lane]:
                self.winnersLanes[lane].remove(vehicle)
            if not self.winnersLanes[lane]:
                self.winnersLanes.pop(lane)
        if vehicle in self.nonStoppedVehicles:
            self.nonStoppedVehicles.remove(vehicle)
        self.partecipantsRoutes.pop(vehicle)
        self.precedences.pop(vehicle)
        # print('wv', [i.getID() for i in self.getCurrentWinners()])
        # print('va', [i.getID() for i in self.getVehiclesInAuction()])

    # TODO: è da aggiustare.
    def updateVehicleStatus(self, vehicle):
        """Funzione che aggiorna i permessi di passaggio per un veicolo che debba attraversare ma che non possa entrare
        in un'asta. I veicoli non possono entrare in un'asta in 2 casi: o dovrebbero parteciparvi con soli veicoli
        vincitori (i veicoli vincitori non prendono più parte ad aste) oppure non necessitano di competere, hanno solo
        bisogno di un permesso di passaggio."""
        # print('updating', self.junction.getID(), vehicle.getID(), vehicle.distanceFromEndLane())
        self.partecipants.append(vehicle)
        # print('p v', [i.getID() for i in self.getCurrentPartecipants() if i is not None])
        self.partecipantsRoutes[vehicle] = self.junction.fromEdgesToLanes(vehicle)
        self.precedences[vehicle] = {}
        # print('r v', [(i.getID(),j) for i,j in self.partecipantsRoutes.items() if i is not None])
        vehicle.stopVehicle()
        if self.junction.bufferMode:
            # vehicleRoute = self.junction.fromEdgesToLanes(vehicle)
            vehiclesInCT = ['placeholder']
            # for i in self.currentWinners:
            #     if self.junction.isClashing(vehicleRoute, self.partecipantsRoutes[i]):
            #         vehiclesInCT.append(i)

            self.precedences[vehicle] = vehiclesInCT
            # print(f'initializing {vehicle.getID()}')
            self.currentLosers.append(vehicle)
            # self.partecipantsRoutes[vehicle] = self.junction.fromEdgesToLanes(vehicle.getCurrentRoute())
            self.bids[vehicle] = 0  # non ha partecipato ad un'asta quindi non ha ancora fatto un'offerta.

    def allowCrossing(self):
        """Funzione che, dopo aver controllato i veicoli nelle posizioni di testa, da il via libera ai veicoli che, nel
        passare, non risultano essere in traiettorie incidentali, rispettando la lista delle precedenze dei veicoli"""
        # prendo i veicoli in testa poichè sono gli unici che possono passare all'atto pratico
        # vehiclesInHead = [i for i in self.crossingStatus.values() if i is not None and i in self.precedences]
        vehiclesInHead = [i for i in self.crossingStatus.values() if i is not None and i in self.precedences
                          and i.distanceFromEndLane() <= 15]
        # prendo i veicoli che stanno attraversando per evitare che i nuovi veicoli autorizzati partano troppo presto
        vehiclesCrossing = self.getVehiclesNowCrossing()
        if self.junction.bufferMode:
            """Vai all'else, questo ramo riguarda la versione bufferata ed è incompleto"""
            numberOfStoppedVehicles = 0
            numberOfOngoingVehicles = 0
            for i in range(len(vehiclesInHead)):
                veh = vehiclesInHead[i]
                if veh.isStopped():
                    # attraverso questi contatori si può arrivare ad ottenere una condizione che identifica un deadlock all'
                    # incrocio: tutti i veicoli bloccati e fermi senza alcun veicolo in condizione di muoversi, nel caso
                    # succeda ciò si attiva del codice in grado di risolvere il blocco.
                    if traci.vehicle.getSpeed(veh.getID()) == 0.0:
                        numberOfStoppedVehicles += 1
                    else:
                        numberOfOngoingVehicles += 1
                isInAClash = False
                # se l'elenco dei veicoli a cui dare la precedenza è vuoto
                # if not self.precedences[veh]:
                for j in vehiclesInHead:
                    if j in self.precedences[veh]:
                        isInAClash = True
                        break
                if not isInAClash:
                    for k in vehiclesCrossing:
                        # controllo che il veicolo in questione non sia in clash con un veicolo che sta già attraversando
                        if self.junction.isClashing(self.getVehicleLane(k), self.getVehicleLane(veh)):
                            isInAClash = True
                            break
                if not isInAClash:
                    # se non è in un clash allora provo a dargli il permesso di muoversi
                    # print('Trying restart of Type 1')
                    # veh.restartVehicle()
                    # restartedVehicles.append(veh)
                    if veh not in self.nonStoppedVehicles:
                        for j in self.nonStoppedVehicles:
                            if self.junction.isClashing(self.getVehicleLane(j), self.getVehicleLane(veh)):
                                isInAClash = True
                        if not isInAClash:
                            self.nonStoppedVehicles.append(veh)
                        # self.tryRestartVehicle(veh)
                else:
                    # unico momento in cui c'è il rischio che veicoli in clash attraverino insieme, in quel caso si fa
                    # affidamento ai meccanismi di sumo che evitano gli scontri.
                    if not veh.isStopped():
                        if veh.isStoppable():
                            veh.tryStop()
                            # veh.stopVehicle()
                            if veh in self.nonStoppedVehicles:
                                self.nonStoppedVehicles.remove(veh)
            # qui comincia il meccanismo che ottimizza il passaggio dei veicoli, permettendo il movimento di quelli non di
            # intralcio ad altri autorizzati.
            # sortedWinners = [(i, self.bids[i]) for i in vehiclesInHead if i in self.currentWinners
            #                  and i.distanceFromEndLane() <= 10 and traci.vehicle.getSpeed(i.getID()) == 0]
            sortedWinners = [(i, sum([self.bids[j] for j in self.getCurrentPartecipants() if i.getCurrentLane() ==
                                      j.getCurrentLane()])) for i in vehiclesInHead if i in self.currentWinners
                             and i.distanceFromEndLane() <= 1]
            sortedWinners.sort(key=lambda x: x[1], reverse=True)
            # sortedLosers = [(i, self.bids[i]) for i in vehiclesInHead if i in self.currentLosers
            #                 and i.distanceFromEndLane() <= 10 and traci.vehicle.getSpeed(i.getID()) == 0]
            sortedLosers = [(i, sum([self.bids[j] for j in self.getCurrentPartecipants() if i.getCurrentLane() ==
                                     j.getCurrentLane()])) for i in vehiclesInHead if i in self.currentLosers
                            and i.distanceFromEndLane() <= 1]
            sortedLosers.sort(key=lambda x: x[1], reverse=True)
            sortedVehicles = sortedWinners + sortedLosers
            for i in sortedVehicles:
                veh = i[0]
                # if veh not in restartedVehicles:
                if veh not in self.nonStoppedVehicles:
                    isInAClash = False
                    for j in self.nonStoppedVehicles:
                        if self.junction.isClashing(self.getVehicleLane(j), self.getVehicleLane(veh)):
                        # if j in self.precedences[veh]:
                            isInAClash = True
                            break
                    if not isInAClash:
                        for k in vehiclesCrossing:
                            if self.junction.isClashing(self.getVehicleLane(k), self.getVehicleLane(veh)):
                                isInAClash = True
                                break
                    if not isInAClash:
                        # print('Restart of Type 2')
                        # print("I'm moving the vehicle ", veh.getID())
                        # veh.restartVehicle()
                        # restartedVehicles.append(veh)
                        if veh not in self.nonStoppedVehicles:
                            self.nonStoppedVehicles.append(veh)
                            # self.tryRestartVehicle(veh)
                    else:
                        if not veh.isStopped():
                            veh.tryStop()
            for i in self.nonStoppedVehicles:
                i.restartVehicle()
                if i.getJunctionWaitingTime() != 0:     # and traci.vehicle.getSpeed(i.getID()) == 0:
                    i.saveTimePassedAtJunction()
                    i.resetJunctionWaitingTime()
            #         print(f'time at junction saved for vehicle {i.getID()} ({i.getTrafficWaitingTime()})')
            # print('restarted vehicles:', end=' ')
            # for i in self.nonStoppedVehicles:
            #     print((i.getID()), i.getCurrentLane(), end=', ')
            # print()
            self.nonStoppedVehicles.clear()
        else:
            self.allowCrossing_nonBuffered()

    def allowCrossing_nonBuffered(self):
        """Funzione che concede effettivamente la capacità di movimento ai veicoli schedulati per il passaggio."""
        # print('trying to move vehicles')
        vehiclesInHead = [i for i in self.getCrossingStatus().values() if i is not None and
                          i.distanceFromEndLane() <= 15 and i not in self.nonStoppedVehicles]
        # con il seguente ciclo rimuoviamo dalla corsia dei vincitori i veicoli che hanno cominciato ad attraversare la
        # l'incrocio
        for wv in self.currentWinners:
            lane = self.partecipantsRoutes[wv][0]
            # print(lane)
            if lane in self.winnersLanes:
                # print(f'winnersLane {lane}', [i.getID() for i in self.winnersLanes[lane]])
                if wv in self.winnersLanes[lane] and wv in self.getVehiclesNowCrossing():
                    self.winnersLanes[lane].remove(wv)
                if not self.winnersLanes[lane]:
                    # print('removing lane', lane)
                    self.winnersLanes.pop(lane)
        winningVehicles = [i for i in self.currentWinners if i in vehiclesInHead]
        # print([wv.getID() for wv in winningVehicles])
        for wv in winningVehicles:
            # if not self.isInClashWithCrossingVehicles(wv):
            wv.restartVehicle()
            self.nonStoppedVehicles.append(wv)
            """Salvo i tempi di attesa"""
            if not wv.hasPassedFreely:
                wv.saveTimePassedAtJunction()
                # print(f'time at junction saved for vehicle {vtr.getID()} ({vtr.getTrafficWaitingTime()})')
                wv.saveMainGroupWaitingTime()
                # print(
                #     f'main group waited time saved for vehicle {vtr.getID()} ({vtr.getMainGroupWaitingTime()})')
                wv.saveTotalWaitingTime()
                # print(
                #     f'total waited time saved for vehicle {vtr.getID()} ({vtr.getTrafficWaitingTime()})')
            wv.resetJunctionWaitingTime()
            wv.resetTotalWaitingTime()
            wv.resetMainGroupWaitingTime()

        # ricreiamo veh in head perchè alcuni veicoli potrebbero dover essere rimossi
        vehiclesInHead = [i for i in self.getCrossingStatus().values() if i is not None and
                          i.distanceFromEndLane() <= 15 and i not in self.nonStoppedVehicles]
        """Il seguente blocco di codice è utilizzabile se si vogliono implementare politiche che blocchino il meccanismo
        di ottimizzazione in determinati frangenti. È commentato poichè non utilizzato nelle simulazioni finali."""
        isToBeBlocked = False
        # if self.currentWinners:
        #     # lane = self.partecipantsRoutes[self.currentWinners[0]][0]
        #     # if lane not in self.winnersLanes:
        #     if not self.winnersLanes:
        #         isToBeBlocked = True
        # if self.junction.maxDimensionOfGroups != 1:
        #     if 0 < len(self.currentWinners) <= 2:
        #             isToBeBlocked = True
        # else:
        #     if len(self.currentWinners) == 1:
        #             isToBeBlocked = True
        if not isToBeBlocked:
            blockingVehicles = self.getBlockingVehicles()
            # if self.currentWinners and self.junction.maxDimensionOfGroups != 1:

            if len(blockingVehicles) >= 5 and self.isAFirstVehicleTraversing(self.currentWinners):
                """In questo ramo si cercano dei veicoli che possano prendere parte ad un'asta a passaggio singolo."""
                vehiclesNotInAuction = [i for i in vehiclesInHead if i not in self.vehiclesInAuction]
                losingVehicles = [i for i in vehiclesInHead if i in self.currentLosers]
                nonWinningVehicles = vehiclesNotInAuction + losingVehicles
                restartableVehicles = self.getRestartableVehicles(nonWinningVehicles, blockingVehicles)
                for vtr in self.createSingularAuction(restartableVehicles):
                    vtr.restartVehicle()
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
            else:
                """In questo ramo si cercano i veicoli che non sono in clash con nessun altro veicolo e gli permetto di
                passare."""
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
        # else:
        #     vehToBeRemoved = []
        #     for v in self.nonStoppedVehicles:
        #         if v not in self.getVehiclesNowCrossing() and v.isStoppable():
        #             v.stopVehicle()
        #             vehToBeRemoved.append(v)
        #     for v in vehToBeRemoved:
        #         self.nonStoppedVehicles.remove(v)

    def getBlockingVehicles(self):
        """Funzione che calcola i veicoli bloccanti per gli altri veicoli in testa"""
        blockingVehicles = self.nonStoppedVehicles.copy()
        # print('bv1', [i.getID() for i in blockingVehicles])
        # blockingVehicles.extend([i for i in self.getVehiclesNowCrossing() if i not in blockingVehicles])
        for lane in self.winnersLanes:
            wl = self.winnersLanes[lane]
            blockingVehicles.extend([i for i in wl[0:3] if i not in blockingVehicles])
        # print('bv2', [i.getID() for i in blockingVehicles])
        return blockingVehicles

    def getRestartableVehicles(self, nonWinningVehicles, blockingVehicles):
        """Funzione che trova i veicoli che potrebbero muoversi"""
        restartableVehicles = []
        for nwv in nonWinningVehicles:
            isInAClash = False
            # for rv in self.nonStoppedVehicles:
            # print('bv', [i.getID() for i in blockingVehicles])
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
        non rischiare di creare incidenti. Tale funzione si applica ai veicoli senza precedenze da dare,
        e controlla che fra i veicoli con possibilità di movimento non c'è ne siano in traiettorie incidentali; se c'è
        ne allora: se il veicolo da inserire è un vincitore si toglie qualunque veicolo in CT, senza distinzioni (a meno
        di impossibilità di fermarsi del veicolo da rimuovere), invece se il veicolo è perdente allora si decide quale
        ha più priorità, procedendo o meno alla rimozione."""
        vehiclesCrossing = self.getVehiclesNowCrossing()
        vehiclesToBeRemoved = []
        isInAClash = False
        # un veicolo vincitore senza precedenze non viene sbloccato se e solo se si trova in clash con un veicolo già in
        # moto e non bloccabile
        # if veh in self.getCurrentWinners():
        if not self.precedences[veh]:
            for i in self.nonStoppedVehicles:
                if i not in vehiclesCrossing:
                    if self.junction.isClashing(self.getVehicleLane(veh), self.getVehicleLane(i)):
                        # print('tryStopWarning 1', i.getID(), i.isStoppable())
                        if i.isStoppable():
                            vehiclesToBeRemoved.append(i)
                        else:
                            vehiclesToBeRemoved.clear()
                            isInAClash = True
                            break
        # un veicolo perdente senza precedenze viene bloccato se il veicolo con cui è in clash non è fermabile oppure se
        # il veicolo con cui è in clash ha presentato un'offerta migliore della sua
        # if veh in self.getCurrentLosers():
        else:
            for i in self.nonStoppedVehicles:
                if i not in vehiclesCrossing:
                    # if veh in self.precedences[i]:
                    # print(veh.getID(), self.getVehicleLane(veh), i.getID(), self.getVehicleLane(i))
                    if self.junction.isClashing(self.getVehicleLane(veh), self.getVehicleLane(i)):
                        # print('tryStopWarning 2', i.getID(), i.isStoppable())
                        if self.bids[i] < self.bids[veh] and i.isStoppable():
                            vehiclesToBeRemoved.append(i)
                        else:
                            vehiclesToBeRemoved.clear()
                            isInAClash = True
                            break
        if not isInAClash:
            self.nonStoppedVehicles.append(veh)
        for i in vehiclesToBeRemoved:
            i.stopVehicle()
            self.nonStoppedVehicles.remove(i)

    def manageDeadlock(self, vehiclesInHead):
        """Funzione legata al caso bufferato.
        Funzione che sblocca l'incrocio nel caso in cui si verifichi una situazione di deadlock. Ordina i veicoli
        in testa rispetto all'offerta che hanno effettuato e gli dà libertà di movimento alla condizione che non siano
        in traiettoria incidentale con i veicoli già sbloccati (conseguentemente il veicolo con l'offerta maggiore viene
        sempre sbloccato, sciogliendo il deadlock in ogni caso).
        :param vehiclesInHead: lista contente i riferimenti ai veicoli attualmente in testa sulle corsie che portano
        all'incrocio."""
        vehiclesSortedByBid = [[i, self.bids[i]] for i in vehiclesInHead]
        vehiclesSortedByBid.sort(key=lambda x: x[1], reverse=True)
        vehiclesUnlocked = [vehiclesSortedByBid[0][0]]
        for j in vehiclesSortedByBid:
            isInAClash = False
            for k in vehiclesUnlocked:
                if k in self.precedences[j[0]]:
                    isInAClash = True
                    break
            if not isInAClash:
                vehiclesUnlocked.append(j[0])
        for i in vehiclesUnlocked:
            # print('Restart of type 3')
            i.restartVehicle()
            if i not in self.nonStoppedVehicles:
                self.nonStoppedVehicles.append(i)

    def getPrecedences(self):
        """Restituisce il dizionario delle precedenze"""
        return self.precedences

    def getCurrentWinners(self):
        """Restituisce la lista dei vincitori"""
        return self.currentWinners

    def getCurrentLosers(self):
        """Restituisce la lista degli sconfitti"""
        return self.currentLosers

    # def getVehicleLane(self, vehicle):
    #     """Funzione che restituisce la route seguita dal veicolo passato in argomento"""
    #     if vehicle in self.getPrecedences().keys():
    #         return self.partecipantsRoutes[vehicle]
    #     else:
    #         return None

    def getPrecedencesOfVehicle(self, vehicle):
        """Funzione legata al caso bufferizzato.
        Funzione che restituisce la lista di veicoli di cui aspettare il passaggio che il veicolo passato in
        posseduta dal veicolo passato in argomento. Se tale lista è vuota allora il veicolo non corre pericoli
        nell'attraversare l'incrocio."""
        if vehicle in self.precedences:
            return self.getPrecedences()[vehicle]
        else:
            # se un veicolo non è segnato all'interno delle precedenze viene restituito None: a questo segnale viene
            # richiesto un update al manager
            return None

    def inheritPrecedences(self, auction):
        """Funzione legata al caso bufferizzato.
        Funzione che fa ereditare le precedenze da dare ai veicoli nel caso in cui questi arrivino
        dietro a dei veicoli fermi"""
        for i in auction.getPartecipants():
            for j in self.partecipants:
                # forse questo controllo è da ripensare
                # if j.isStopped() and traci.vehicle.getSpeed(j.getID()) == 0.0:
                if self.getVehicleLane(j) == self.getVehicleLane(i):
                    for k in self.precedences[j]:
                        if k not in self.precedences[i]:
                            self.precedences[i].append(k)
                elif self.getVehicleLane(j)[0] == self.getVehicleLane(i)[0]:
                    for k in self.precedences[j]:
                        if k not in self.precedences[i] and self.junction.isClashing(self.getVehicleLane(k),
                                                                                     self.getVehicleLane(i)):
                            self.precedences[i].append(k)

    def addWinner(self, vehicle):
        """Funzione che aggiunge il vincitore sia ai veicoli vincitori sia a quelli in un'asta"""
        self.currentWinners.append(vehicle)
        self.vehiclesInAuction.append(vehicle)
        assert self.currentWinners.count(vehicle) == 1, vehicle.getID()
        assert self.vehiclesInAuction.count(vehicle) == 1, vehicle.getID()

    def removeWinner(self, vehicle):
        """Funzione che rimuove un veicolo vincitore dalla lista dei vincitori e dei partecipanti ad un'asta"""
        self.currentWinners.remove(vehicle)
        self.vehiclesInAuction.remove(vehicle)
        assert self.currentWinners.count(vehicle) == 0, vehicle.getID()
        assert self.vehiclesInAuction.count(vehicle) == 0, vehicle.getID()

    def addLoser(self, vehicle):
        """Funzione che aggiunge il vincitore sia ai veicoli sconfitti sia a quelli in un'asta"""
        self.currentLosers.append(vehicle)
        self.vehiclesInAuction.append(vehicle)
        assert self.currentLosers.count(vehicle) == 1, vehicle.getID()
        assert self.vehiclesInAuction.count(vehicle) == 1, vehicle.getID()

    def removeLoser(self, vehicle):
        """Funzione che rimuove un veicolo vincitore dalla lista degli sconfitti e dei partecipanti ad un'asta"""
        self.currentLosers.remove(vehicle)
        self.vehiclesInAuction.remove(vehicle)
        assert self.currentLosers.count(vehicle) == 0, vehicle.getID()
        assert self.vehiclesInAuction.count(vehicle) == 0, vehicle.getID()

    def printPrecedences(self):
        """Funzione utilizzabile per visualizzare le precedenze in un formato leggibile"""
        for vehicle, precedences in self.precedences.items():
            print(vehicle.getID(), end=': ')
            for v in precedences:
                if v != 'placeholder':
                    print(v.getID(), end=', ')
            print()

