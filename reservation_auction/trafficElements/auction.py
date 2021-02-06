import math
import random
from abc import abstractmethod, ABC
from reservation_auction.main import isClashing
import traci  #noqa


def payBid_(bid, veh):
    """Funzione utilizzata per pagare quanto dovuto dopo un'asta. Attualmente impiegata solo dalla
    versione delle simulazioni non bufferate."""
    wallet = traci.vehicle.getParameter(veh, "wallet")
    wallet -= bid
    # il portafoglio del veicolo non è mai negativo
    if wallet < 0:
        wallet = 0
    traci.vehicle.setParameter(veh, "wallet", wallet)


def makeBid(veh):
    """Funzione utilizzata per effettuare le offerte per le aste. Attualmente impiegata solo dalla versione delle
    simulazioni non bufferate."""
    cap = int(traci.vehicle.getParameter(veh, "wallet") / 2)
    # controllo per fare in modo che il veicolo effettui un'offerta minima in un asta
    if cap > 10:
        return random.randint(10, cap)
    else:
        return 10


class Auction(ABC):
    """Classe che, dati una serie di veicoli in ingresso, esegue un'asta determinando quali di questi possano
    attraversare l'incrocio e quali no."""

    def __init__(self, vehicles, junction, oV=False):
        self.partecipantsGrouped = vehicles.copy()
        self.junction = junction
        # lista contente i partecipanti non raggruppati per corsia
        self.partecipantsNonGrouped = [j for i in vehicles for j in i]
        self.bids = {}
        self.bidsInc = {}
        self.oneVehicle = oV
        # TODO: alla fine questo controllo sarà da rimuovere
        if not junction.bufferMode:
            self.createAuction()

    def getPartecipants(self):
        """Funzione che restituisce i partecipanti ad un'asta non raggruppati per corsia"""
        return self.partecipantsNonGrouped

    def getPartecipantsGroupedByLane(self):
        """Funzione che restituisce i partecipanti raggruppati per corsia di appartenenza"""
        return self.partecipantsGrouped

    @abstractmethod
    def startAnAuction(self):
        """
        Funzione che richiede ad una lista di veicoli accorpati (quelli appartenenti alla stessa corsia devono stare
        assieme, visto che partecipano all'asta insieme) di effettuare un'offerta per vincere l'asta ed ottenere la
        possibilità di passare per primo all'incrocio"""
        pass

    def manageStarvation(self, vehicle, bid, numVeh):
        """Funzione utilizzata per gestire la starvation. Contiene più formule che perseguono lo scopo. L'unica non
        commentata è quella utilizzata nella simulazione finale."""
        # finalBid = bid + (vehicle.numberOfAuctionAtJunction-1)**3

        finalBid = bid * (math.log(vehicle.numberOfAuctionAtJunction) + 1)

        # finalBid = bid * (math.log(vehicle.numberOfAuctionAtJunction) + 1) / (1 + (numVeh - 1) / 20)

        # m = math.log(vehicle.numberOfAuctionAtJunction) + 1
        # multiplier = m - m * ((numVeh-1) / (self.junction.maxDimensionOfGroups))
        # multiplier = (m * numVeh)/self.junction.maxDimensionCalc(vehicle.getCurrentLane()) #- m * ((numVeh - 1) / (self.junction.maxDimensionOfGroups))
        # finalBid = bid * multiplier

        # finalBid = bid

        # finalBid = bid*(math.log(numVeh)+1)

        return finalBid

    def createAuction(self):
        """Funzione che effettua l'asta e ordina i gruppi di veicoli per offerta totale decrescente."""
        for pG in self.partecipantsGrouped:
            partecipants = pG[0]
            sponsors = pG[1]
            bidsFromLane = []
            """Raccolgo le offerte dei membri del gruppo principale."""
            for p in partecipants:
                if p.hasPassedFreely:
                    # la seguente variabile booleana indica che il veicolo ha dovuto partecipare ad un'asta, il counter
                    # può essere incrementato solo una volta per ogni incrocio (conta il numero di volte in cui almeno
                    # un'asta si è resa necessaria)
                    p.hasPassedFreely = False
                    p.notFreePassageCounter += 1
                bid = makeBid(p)
                bidInc = self.manageStarvation(p, bid, len(partecipants))
                self.bids[p] = bid
                self.bidsInc[p] = bidInc
                bidsFromLane.append(bidInc)
                p.forbidLaneChange()
            """Raccolgo le offerte dei membri del gruppo degli sponsors."""
            for s in sponsors:
                if s.hasPassedFreely:
                    s.hasPassedFreely = False
                    s.notFreePassageCounter += 1
                sponsorship = s.makeSponsorship()
                sponsorshipInc = self.manageStarvation(s, sponsorship, len(sponsors))
                # sponsorshipInc = 0
                self.bids[s] = sponsorship
                self.bidsInc[s] = sponsorshipInc
                bidsFromLane.append(sponsorshipInc)
            pG.append(sum(bidsFromLane))

        """Ordino i partecipanti in base all'offerta fatta, in modo decrescente."""
        self.partecipantsGrouped = sorted(self.partecipantsGrouped, key=lambda x: x[2], reverse=True)
        # for pls in self.partecipantsGrouped:
        #     g1 = pls[0]
        #     print(f'\ngroup of partecipants of lane {g1[0].getCurrentLane()}')
        #     for i in g1:
        #         print(i.getID(), f'n auction lost {i.numberOfAuctionAtJunction}', f'{(self.bids[i], self.bidsInc[i])}', end=', ')
        #     g2 = pls[1]
        #     print('\ngroup of sponsors')
        #     for i in g2:
        #         print(i.getID(), f'n auction lost {i.numberOfAuctionAtJunction}', f'{(self.bids[i], self.bidsInc[i])}', end=', ')
        #     print('total offer: ', pls[2])
        # number of partecipants without winners
        """Con il seguente blocco di codice ricarico il budget dei veicoli in modo proporzionale all'offerta che hanno 
        fatto all'asta che hanno appena perso."""
        npww = [i for j in self.partecipantsGrouped for i in j[0] + j[1] if self.partecipantsGrouped.index(j) != 0]
        totalLoserOffer = sum([self.bids[i] for i in npww])
        totalWinnerOffer = sum([self.bids[i] for i in self.partecipantsGrouped[0][0]])
        # rechargeValue = self.partecipantsGrouped[0][2] / len(npww)
        for veh in npww:
            if not self.oneVehicle and self.junction.isCompetitive:
                veh.numberOfAuctionAtJunction += 1
            percBid = self.bids[veh] / totalLoserOffer
            # print(f'% {percBid} of {totalLoserOffer}, based on the original offer {self.bids[veh]}')
            rechargeValue = math.ceil(totalWinnerOffer * percBid)
            veh.fillWallet(rechargeValue)


class CompetitiveAuction(Auction):
    """Classe che, dati una serie di veicoli in ingresso, esegue un'asta determinando quali di questi possano
    attraversare l'incrocio e quali no."""

    def __init__(self, vehicles, junction, oV=False, instantPay=False, bufferMode=True):
        super().__init__(vehicles, junction, oV)
        self.winners = []
        self.lanesObjectiveOfWinners = {}
        self.losers = []
        self.instantPay = instantPay
        self.bufferMode = bufferMode
        if not bufferMode:
            self.partecipantsNonGrouped = [i for j in self.partecipantsGrouped for i in j[0]]
        self.startAnAuction(oV)

    def getWinners(self):
        """Funzione che restituisce i veicoli vincitori, autorizzati ad attraverdare l'incrocio"""
        return self.winners

    def getLosers(self):
        """Funzione che restituisce i veicoli perdenti, bloccati all'incrocio"""
        return self.losers

    def getLanesObjectiveOfWinners(self):
        return self.lanesObjectiveOfWinners

    def startAnAuction(self, oneVehicle=False):
        """
        Funzione che richiede ad una lista di veicoli accorpati (quelli appartenenti alla stessa corsia devono stare
        assieme, visto che partecipano all'asta insieme) di effettuare un'offerta per vincere l'asta ed ottenere la
        possibilità di passare per primo all'incrocio
        :param vehicles: i veicoli che parteciperanno all'asta raggruppati per corsia;
        :param oneVehicle: booleano che indica se la simulazione richiede un solo vincitore alla volta o un gruppo di
        essi;
        :return winner: i veicoli vincenti;
        :return losers: , i capofila delle corsie perdenti.
        """
        """Il ramo della funzione utilizzato è questo. Salvo i vincitori e gli sconfitti e faccio pagare 
        chi deve pagare in base al setup della simulazione."""
        winners = self.partecipantsGrouped[0][0]
        losers = []
        for lis in self.partecipantsGrouped[1:]:
            if isClashing(traci.vehicle.getRoute(lis[0][0]),
                          traci.vehicle.getRoute(winners[0])):
                losers.extend(lis[0])
        self.winners = winners.copy()
        self.losers = losers.copy()
        if self.instantPay:
            allPartecipants = self.partecipantsNonGrouped.copy()
            # aggiungo gli sponsor di tutti i partecipanti
            allPartecipants.extend([i for j in self.partecipantsGrouped for i in j[1]])
            for v in allPartecipants:
                payBid_(self.bids[v], v)
        else:
            # aggiungo gli sponsor dei vincitori
            winners.extend(self.partecipantsGrouped[0][1])
            for v in winners:
                payBid_(self.bids[v], v)


class CooperativeAuction(Auction):
    def __init__(self, vehicles, junction, instantPay=False, bufferMode=True):
        super().__init__(vehicles, junction)
        self.instantPay = instantPay
        self.bufferMode = bufferMode
        if not bufferMode:
            self.partecipantsNonGrouped = [i for j in self.partecipantsGrouped for i in j[0]]
        self.orderedPartecipants = []
        self.startAnAuction()

    def startAnAuction(self):
        if not self.bufferMode:
            """Il ramo della funzione utilizzato è questo. Salvo la classifica in orderedPartecipants e faccio pagare 
            chi deve pagare in base al setup della simulazione."""
            self.orderedPartecipants = [i[0] for i in self.partecipantsGrouped]
            if self.instantPay:
                allPartecipants = self.partecipantsNonGrouped.copy()
                allPartecipants.extend([i for j in self.partecipantsGrouped for i in j[1]])
                for v in allPartecipants:
                    v.payBid_(self.bids[v])
            else:
                allFirsts = self.orderedPartecipants[0].copy()
                allFirsts.extend(self.partecipantsGrouped[0][1])
                for v in allFirsts:
                    v.payBid_(self.bids[v])
            # for w in winners:
            #     print(
            #         f'winner {w.getID()}, {w.distanceFromEndLane()} (lane {w.getCurrentLane()}) is paying {self.bids[w]}')
            # for l in losers:
            #     print(
            #         f'loser {l.getID()}, {l.distanceFromEndLane()} (lane {l.getCurrentLane()}) is paying {self.bids[l]}')
        else:
            """Ramo incompleto."""
            partecipants = []
            for vehiclesInALane in self.partecipantsGrouped:
                bidsFromALane = []
                for veh in vehiclesInALane:
                    bidVeh = veh.makeABid(self.junction)
                    bidsFromALane.append(bidVeh)
                    self.bids[veh] = bidVeh
                totalBid = sum(bidsFromALane)
                partecipants.append((vehiclesInALane, totalBid))
            partecipants.sort(key=lambda x: x[1], reverse=True)
            self.orderedPartecipants = [i[0] for i in partecipants]
            for i in self.partecipantsNonGrouped:
                if i.isAllowedLaneChange():
                    i.forbidLaneChange()
            if not self.partecipantsNonGrouped[0].instantPay:
                # se devono pagare solo i veicoli vincitori
                for i in self.orderedPartecipants[0]:
                    i.payBid(self.bids[i])
                    # print(i.getID(), 'is paying', self.bids[i])
