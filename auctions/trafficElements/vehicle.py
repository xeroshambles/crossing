import random
import re
from random import randint, choice

from .junction import Junction

import traci


class Vehicle:

    def __init__(self, ID, measures, iP=False, bB=False):
        self.idVehicle = ID
        self.numericID = int(ID[3:])
        self.isOnAStop = False
        self.isSlowed = False
        self.isRestarted = False
        self.wallet = randint(150, 250)
        self.canChangeLane = True
        self.isActive = True
        self.nVehiclesToWait = 0
        self.instantPay = iP
        self.edgeObjective = None
        self.isLaneWrong = False
        self.balancedBidding = bB
        self.numberOfAuctionAtJunction = 1
        self.staticRouteGenerator = self.generatorOfStaticRoute()

        self.waitingTimeAtJunction = 0
        self.waitingTimeInTraffic = 0
        self.totalWaitingTime = 0
        self.mainGroupWaitingTime = 0
        self.sponsorGroupWaitingTime = 0
        self.junctionCounter = 0

        self.hasPassedFreely = True
        self.hasAvoidTraffic = True
        self.hasSaved_T = False
        self.hasSaved_SG = False
        self.freePassageCounter = 0
        self.notFreePassageCounter = 0
        self.numberOfTimesInTraffic = 0

        self.hasPassedFreely_groups = True
        self.hasAvoidTraffic_groups = True
        self.freePassageCounter_groups = 0
        self.notFreePassageCounter_groups = 0
        self.numberOfTimesInTraffic_groups = 0

        self.passedWaitingTimesInTraffic = []
        self.passedWaitingTimesAtJunction = []
        self.passedTotalWaitingTimes = []
        self.passedMainGroupTimes = []
        self.passedSponsorGroupTimes = []

        self.measures = measures

    def makeBid(self):
        """Funzione utilizzata per effettuare le offerte per le aste. Attualmente impiegata solo dalla versione delle
        simulazioni non bufferate."""
        if not self.balancedBidding:
            cap = int(self.wallet / 2)
            # controllo per fare in modo che il veicolo effettui un'offerta minima in un asta
            if cap > 10:
                return randint(10, cap)
            else:
                return 10

    def makeSponsorship(self):
        """Funzione utilizzata per sponsorizzare altri veicoli durante le aste. Attualmente impiegata solo dalla
        versione delle simulazioni non bufferate."""
        cap = int(self.wallet / 10)
        # controllo per fare in modo che il veicolo effettui un'offerta minima in un asta
        if cap > 5:
            return randint(5, cap)
        else:
            return 5

    def fillWallet(self, value):
        """Funzione utilizzata per ricaricare il portafoglio del veicolo"""
        self.wallet += value

    def payBid_(self, bid):
        """Funzione utilizzata per pagare quanto dovuto dopo un'asta. Attualmente impiegata solo dalla
        versione delle simulazioni non bufferate."""
        self.wallet -= bid
        # il portafoglio del veicolo non è mai negativo
        if self.wallet < 0:
            self.wallet = 0

    def checkPosition(self, junction):
        """Funzione che controlla se, dalla corsia corrente, il veicolo può raggiungere la corsia obiettivo"""
        currentRoute = junction.fromEdgesToLanes(self)
        nextLane = self.getNextEdge()
        if currentRoute[1] != nextLane:
            return False
        else:
            return True

    def getID(self):
        """Funzione che restituisce l'ID del veicolo."""
        return self.idVehicle

    def isStoppable(self):
        """Funzione che controlla se un veicolo è fermabile in un certo momento. ATTENZIONE, il veicolo potrebbe
        comunque non essere fermabile in momenti successivi."""
        return self.tryStop(tryButDontStop=True)

    def tryStop(self, tryButDontStop=False):
        """Funzione che prova a fermare un veicolo e, se ci riesce, restituisce True (fermandolo), altrimenti
        restituisce False.
        :param tryButDontStop: parametro booleano che, se diverso da False, si limita a provare a stoppare il
                         veicolo senza applicare effettivamente lo stop."""
        try:
            # provo a fermare il veicolo
            if tryButDontStop:
                # controllo che il veicolo non sia già fermo, altrimenti lo sbloccherei, se è già fermo posso restituire
                # True, essendo il veicolo già fermo o in frenata
                if not self.isStopped():
                    stopLane = traci.vehicle.getLaneID(self.getID())
                    traci.vehicle.setStop(self.getID(), stopLane[:-2], laneIndex=int(stopLane[-1]),
                                          pos=traci.lane.getLength(stopLane), duration=0)
            else:
                # tentativo riuscito
                self.stopVehicle()
            return True
        except:
            # tentativo fallito
            return False

    def stopVehicle(self):
        """Funzione che blocca il veicolo alla fine della corsia in cui si trova"""
        if not self.isStopped():
            stopLane = traci.vehicle.getLaneID(self.getID())
            try:
                traci.vehicle.setStop(self.getID(), stopLane[:-2], laneIndex=int(stopLane[-1]),
                                    pos=traci.lane.getLength(stopLane))
            except traci.exceptions.TraCIException as e:
                # print(f"ERROR: {e}")
                pass
            self.isOnAStop = True

    def restartVehicle(self):
        """Funzione che sblocca il veicolo nel caso in cui questo fosse bloccato."""
        try:
            if self.isStopped():
                stopLane = traci.vehicle.getLaneID(self.getID())
                traci.vehicle.setStop(self.getID(), stopLane[:-2], laneIndex=int(stopLane[-1]),
                                      pos=traci.lane.getLength(stopLane), duration=0)
                self.isOnAStop = False
        except:
            pass

    def getNextEdge(self):
        """funzione che ritorna l'edge verso cui il veicolo si sta dirigendo"""
        try:
            route = traci.vehicle.getRoute(self.getID())
        except:
            return None
        pos = self.getCurrentLane()
        find = False
        route_corrected = []
        for i in reversed(route):
            if i not in route_corrected:
                route_corrected.insert(0, i)
        for i in route_corrected:
            if i == pos[:-2]:
                find = True
                continue
            # se ho trovato l'edge corrente ritorno la lane successiva
            if find:
                return f'{i}_{pos[-1]}'

    def getCurrentRoute(self):
        """Funzione che restituisce l'edge in cui si trova attualmente il veicolo e quello verso cui si sta
        dirigendo."""
        try:
            # prendo la route del veicolo contenente tutti gli edges da cui deve passare
            route = traci.route.getEdges(traci.vehicle.getRouteID(self.getID()))
        except:
            return None
        # prendo l'edge corrente su cui è il veicolo
        currentEdge = self.getCurrentLane()[:-2]
        nextEdge = ''
        find = False
        route_corrected = []
        for i in reversed(route):
            if i not in route_corrected:
                route_corrected.insert(0, i)
        for i in route_corrected:
            if i != currentEdge:
                nextEdge = i
                break
        return currentEdge, nextEdge

    def getCurrentLane(self):
        """Funzione che restituisce la corsia in cui il veicolo si trova correntemente."""
        return traci.vehicle.getLaneID(self.getID())

    def getCurrentJunction(self):
        """Funzione che restituisce il junction verso cui il veicolo si sta dirigendo attualmente."""
        return 'n' + traci.vehicle.getLaneID(self.getID())[1:3]

    def distanceFromEndLane(self, otherVehicle=None):
        """Funzione che calcola la distanza dalla fine della corsia che sta venendo percorsa dal veicolo."""
        if otherVehicle is not None:
            vehicle = otherVehicle
        else:
            vehicle = self
        # 180 è la lunghezza massima di un edge, se questa non è recuperabile è perchè il veicolo sta attraversando
        # un incrocio
        if traci.vehicle.getLaneID(vehicle.getID()) == '':
            return 180
        distance = traci.lane.getLength(traci.vehicle.getLaneID(vehicle.getID())) - \
                   traci.vehicle.getLanePosition(vehicle.getID())
        return distance

    def isAllowedLaneChange(self):
        """Funzione che, se restituisce True, indica che un veicolo ha la possibilità di cambiare corsia; se restituisce
        False il contrario"""
        return self.canChangeLane

    def isStopped(self):
        return self.isOnAStop

    def getRelativeDistanceFromVehicle(self, vehicle):
        """Funzione che calcola la distanza che c'è fra 2 veicoli rispetto all'incrocio verso cui si stanno dirigendo"""
        veh1 = self.distanceFromEndLane()
        veh2 = self.distanceFromEndLane(vehicle)
        relativeDistance = abs(veh1 - veh2)
        return relativeDistance

    def forbidLaneChange(self):
        """Funzione che disattiva la possibilità di cambiare corsia ma mantiene la distanza di sicurezza ed evita le
        collisioni."""
        traci.vehicle.setLaneChangeMode(self.getID(), 512)
        self.canChangeLane = False

    def allowLaneChange(self):
        """Funzione che riattiva la possibilità di cambiare corsia."""
        # valori di lane change di default
        # traci.vehicle.setLaneChangeMode(self.getID(), 1621)
        traci.vehicle.setLaneChangeMode(self.getID(), 1541)
        self.canChangeLane = True

    def setEdgeObjective(self, edge):
        """Memorizza la corsia obiettivo prima di un cambio temporaneo (effettuato a seguito di errori di
        posizionamento)."""
        self.edgeObjective = edge

    def changeTarget(self, momentaryChange=False, junction=None, staticRoutes=False):
        """Funzione che modifica la route del veicolo in seguito alla fine della precedente. Inoltre si occupa
        dell'immediata gestione del caso in cui un veicolo si sia trovato nella corsia sbagliata e sia impossibilitato a
        muoversi."""
        if not momentaryChange:
            # da una nuova corsia obiettivo ad un veicolo che ha completato il suo percorso
            dest = traci.vehicle.getRoute(self.getID())[-1]
            if dest == traci.vehicle.getLaneID(self.getID())[:len(dest)]:
                j = re.search('e(.*)_(.*)', dest).group(1)
                target = self.generateRoute(int(j), staticRoutes)
                traci.vehicle.changeTarget(self.getID(), target)
                self.setEdgeObjective(target)
        else:
            # cambia momentaneamente la corsia obiettivo in modo da poter far muovere il veicolo attraverso l'incrocio
            junction: Junction
            self.isLaneWrong = True
            frontLane = junction.possibleRoutes[self.getCurrentLane()]['front']
            frontEdge = frontLane[:-2]
            traci.vehicle.changeTarget(self.getID(), frontEdge)
            self.checkPosition(junction)

    def resetTarget(self):
        """Funzione che resetta l'obiettivo a quello memorizzato prima di un cambio temporaneo."""
        traci.vehicle.changeTarget(self.getID(), self.edgeObjective)

    def generateRoute(self, initEdge=None, static=False):
        """Metodo che genera una coppia di edge seguendo una serie di vincoli"""
        if initEdge is None:
            junction = [randint(1, 25)]
        else:
            junction = [initEdge]
        if not static:
            # restringendo il set di incroci che possono essere obiettivo di un veicolo posso concentrare il traffico
            # al centro della rete aumentando le congestioni
            listOfChoice = [3, 7, 8, 9, 12, 13, 14, 17, 18, 19, 23]
            if initEdge is not None:
                listOfChoice.remove(initEdge)
            n = choice(listOfChoice)
        else:
            n = self.getNextRoute_Static()
        junction.append(n)
        edge = []
        # metodo particolare per calcolare gli edge della route
        for i in range(2):
            chooser = randint(0, 1)  # 0 orizzontale, 1 verticale
            addOrSub = randint(0, 1)  # 0 se si somma, 1 se si sottrae
            if chooser == 1:
                # TODO: sono utili le prime 4 operazioni?
                addOrSub = 0 if junction[i] == 1 else addOrSub
                addOrSub = 1 if junction[i] == 21 else addOrSub
                addOrSub = 0 if junction[i] == 5 else addOrSub
                addOrSub = 1 if junction[i] == 25 else addOrSub
                addOrSub = 0 if junction[i] <= 5 else addOrSub
                addOrSub = 1 if junction[i] >= 21 else addOrSub
                edge.append([junction[i], junction[i] + 5 * (-1) ** addOrSub])
            else:
                if junction[i] % 5 == 0:
                    addOrSub = 1
                if junction[i] % 5 == 1:
                    addOrSub = 0
                edge.append([junction[i], junction[i] + (-1) ** addOrSub])
        if initEdge is None:
            return f"e{0 if edge[0][0] <= 9 else ''}{edge[0][0]}_{0 if edge[0][1] <= 9 else ''}{edge[0][1]}", \
                   f"e{0 if edge[1][0] <= 9 else ''}{edge[1][0]}_{0 if edge[1][1] <= 9 else ''}{edge[1][1]}"
        else:
            return f"e{0 if edge[1][0] <= 9 else ''}{edge[1][0]}_{0 if edge[1][1] <= 9 else ''}{edge[1][1]}"

    def generatorOfStaticRoute(self):
        """Funzione utilizzabile per ottenere il prossimo incrocio obiettivo nel caso statico"""
        random.seed(self.numericID)
        # restringendo il set di incroci che possono essere obiettivo di un veicolo posso concentrare il traffico
        # al centro della rete aumentando le congestioni
        choicesList = [3, 7, 8, 9, 11, 12, 13, 14, 15, 17, 18, 19, 23]
        for i in range(100000000):
            yield random.choice(choicesList)

    def getNextRoute_Static(self):
        """Funzione che ottiene il nuovo incrocio obiettivo, curandosi di controllare che non sia uguale al
        precedente."""
        newObjective = next(self.staticRouteGenerator)
        if self.edgeObjective is not None:
            currentObj = int(self.edgeObjective[1:3])
            while newObjective == currentObj:
                newObjective = next(self.staticRouteGenerator)
        return newObjective

    """Funzioni relative ai tempi di attesa"""

    """Total Waiting Times"""

    def setTotalWaitingTime(self):
        """Setta il timer per il tempo di attesa totale, se non è già stato settato."""
        if self.totalWaitingTime == 0:
            self.totalWaitingTime = traci.simulation.getTime()

    def getTotalWaitingTime(self):
        """Restituisce il valore corrente di totalWaitingTime"""
        return self.totalWaitingTime

    def saveTotalWaitingTime(self):
        """Se il tempo di attesa totale è stato settato e questa funzione viene chiamata viene calcolato il tempo
        trascorso fra quello attuale e quello in cui il timer è stato fatto partire e lo si salva."""
        if self.totalWaitingTime != 0:
            timePassed = max((traci.simulation.getTime() - self.totalWaitingTime), 0)
            self.passedTotalWaitingTimes.append(timePassed)

    def resetTotalWaitingTime(self):
        """Azzera il counter totalWaitingTime."""
        self.totalWaitingTime = 0

    """Junction Waiting Time - singular"""

    def setJunctionWaitingTime(self):
        """Setta il timer per il tempo di attesa in testa ad una corsia, se non è già stato settato."""
        if self.waitingTimeAtJunction == 0:
            self.waitingTimeAtJunction = traci.simulation.getTime()

    def getJunctionWaitingTime(self):
        """Restituisce il valore corrente di waitingTimeAtJunction"""
        return self.waitingTimeAtJunction

    def saveTimePassedAtJunction(self):
        """Se il tempo di attesa all'incrocio è stato settato e questa funzione viene chiamata viene calcolato il tempo
        trascorso fra quello attuale e quello in cui il timer è stato fatto partire e lo si salva."""
        if self.waitingTimeAtJunction != 0:
            timePassed = max((traci.simulation.getTime() - self.waitingTimeAtJunction), 0)
            self.passedWaitingTimesAtJunction.append(timePassed)

    def resetJunctionWaitingTime(self):
        """Azzera il counter waitingTimeAtJunction."""
        self.waitingTimeAtJunction = 0

    """Traffic Waiting Time - singular"""

    def setTrafficWaitingTime(self):
        """Setta il timer per il tempo di attesa nel traffico, cioè dei veicoli dopo quello di testa, se non è già
         stato settato."""
        if self.waitingTimeInTraffic == 0:
            self.waitingTimeInTraffic = traci.simulation.getTime()

    def getTrafficWaitingTime(self):
        """Restituisce il valore corrente di waitingTimeInTraffic"""
        return self.waitingTimeInTraffic

    def saveTimePassedInTraffic(self):
        """Se il tempo di attesa nel traffico è stato settato e questa funzione viene chiamata viene calcolato il tempo
        trascorso fra quello attuale e quello in cui il timer è stato fatto partire e lo si salva."""
        if self.waitingTimeInTraffic != 0:
            timePassed = max((traci.simulation.getTime() - self.waitingTimeInTraffic), 0)
            self.passedWaitingTimesInTraffic.append(timePassed)

    def resetTrafficWaitingTime(self):
        """Azzera il counter waitingTimeInTraffic."""
        self.waitingTimeInTraffic = 0

    """Main Group Waiting Time"""

    def setMainGroupWaitingTime(self):
        """Setta il timer per il tempo di attesa nel gruppo principale, se non è già stato settato"""
        if self.mainGroupWaitingTime == 0:
            self.mainGroupWaitingTime = traci.simulation.getTime()

    def getMainGroupWaitingTime(self):
        """Restituisce il valore corrente di mainGroupWaitingTime"""
        return self.mainGroupWaitingTime

    def saveMainGroupWaitingTime(self):
        """Se il tempo di attesa nel gruppo principale è stato settato e questa funzione viene chiamata viene calcolato
        il tempo trascorso fra quello attuale e quello in cui il timer è stato fatto partire e lo si salva."""
        if self.mainGroupWaitingTime != 0:
            timePassed = max((traci.simulation.getTime() - self.mainGroupWaitingTime), 0)
            self.passedMainGroupTimes.append(timePassed)

    def resetMainGroupWaitingTime(self):
        """Azzera il counter mainGroupWaitingTime."""
        self.mainGroupWaitingTime = 0

    """Sponsor Group Waiting Time"""

    def setSponsorGroupWaitingTime(self):
        """Setta il timer per il tempo di attesa nel gruppo degli sponsor, se non è già stato settato"""
        if self.sponsorGroupWaitingTime == 0:
            self.sponsorGroupWaitingTime = traci.simulation.getTime()

    def getSponsorGroupWaitingTime(self):
        """Restituisce il valore corrente di sponsorGroupWaitingTime"""
        return self.sponsorGroupWaitingTime

    def saveSponsorGroupWaitingTime(self):
        """Se il tempo di attesa nel gruppo degli sponsor è stato settato e questa funzione viene chiamata viene
        calcolato il tempo trascorso fra quello attuale e quello in cui il timer è stato fatto partire e lo si salva."""
        if self.sponsorGroupWaitingTime != 0:
            timePassed = max((traci.simulation.getTime() - self.sponsorGroupWaitingTime), 0)
            self.passedSponsorGroupTimes.append(timePassed)

    def resetSponsorGroupWaitingTime(self):
        """Azzera il counter sponsorGroupWaitingTime."""
        self.sponsorGroupWaitingTime = 0

    """Liste per raccogliere i tempi di attesa"""

    def getPassedTotalWaitingTimes(self):
        """Restituisce tutti i tempi di attesa totali del veicolo."""
        return self.passedTotalWaitingTimes

    def getPassedJunctionWaitingTimes(self):
        """Restituisce tutti i tempi di attesa all'incrocio del veicolo."""
        return self.passedWaitingTimesAtJunction

    def getPassedTrafficWaitingTimes(self):
        """Restituisce tutti i tempi di attesa nel traffico del veicolo."""
        return self.passedWaitingTimesInTraffic

    def getPassedMainGroupTimes(self):
        """Restituisce tutti i tempi di attesa nel gruppo principale del veicolo."""
        return self.passedMainGroupTimes

    def getPassedSponsorGroupTimes(self):
        """Restituisce tutti i tempi di attesa nel gruppo degli sponsor del veicolo."""
        return self.passedSponsorGroupTimes
