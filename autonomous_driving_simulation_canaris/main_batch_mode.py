import sys
from math import sqrt
from random import randint

import traci
from trafficElements.junction import FourWayJunction
from trafficElements.vehicle import Vehicle


def run(allWaitingTimesAtJunction, allWaitingTimesInTraffic, allTotalTimes, allMGTimes, allSGTimes, batch_mode, numberOfVehicles=0, numberOfSteps=0,
        simulationMode=None, instantPay=None, routeMode=None, bM=True, dimensionOfGroups=0):
    choice = ''
    if not batch_mode:
        while choice not in ['y', 'Y', 'n', 'N']:
            choice = input('Le route devono essere statiche o dinamiche?[y = statiche/n = dinamiche]\n: ')
            if choice not in ['y', 'Y', 'n', 'N']:
                print('Inserire un carattere fra y e n')
        routeMode = True if choice in ['y', 'Y'] else False
        choice = ''
        while choice not in ['y', 'Y', 'n', 'N']:
            choice = input('Tutti i veicoli devono pagare subito? se no pagheranno solo i vincitori delle aste [y/n]\n: ')
            if choice not in ['y', 'Y', 'n', 'N']:
                print('Inserire un carattere fra y e n')
        instantPay = True if choice in ['y', 'Y'] else False
        choice = ''
        while choice not in ['y', 'Y', 'n', 'N']:
            choice = input('Si deve usare un approccio competitivo? se no si userà il cooperativo [y/n]\n: ')
            if choice not in ['y', 'Y', 'n', 'N']:
                print('Inserire un carattere fra y e n')
        simulationMode = True if choice in ['y', 'Y'] else False
        choice = ''
        while choice not in ['y', 'Y', 'n', 'N']:
            choice = input('Si deve usare la buffer mode?\n: ')
            if choice not in ['y', 'Y', 'n', 'N']:
                print('Inserire un carattere fra y e n')
        bM = True if choice in ['y', 'Y'] else False
        dimensionOfGroups = None
        if not bM:
            choice = ''
            while choice not in [str(i) for i in range(1, 8)] + ['-1']:
                choice = input('Quale dimensione deve avere il numero di veicoli considerato? Per usare dimensioni '
                               'proporzionali inserire -1\n'
                               'I gruppi possono avere una dimensione che va da 1 a 7.\n: ')
                if choice not in [str(i) for i in range(1, 8)] + ['-1']:
                    print('Inserire un numero fra 1 e 7, oppure -1')
            dimensionOfGroups = int(choice)
        while True:
            try:
                choice = int(input('Quanti step deve avere la simulazione?\n: '))
                break
            except:
                print('Inserire un numero intero')
        numberOfSteps = choice
        while True:
            try:
                choice = int(input('Quanti veicoli deve avere la simulazione?\n: '))
                break
            except:
                print('Inserire un numero intero')
        numberOfVehicles = choice
        traci.start(sumoCmd)
    vehicles = {}  # dizionario contente dei riferimenti ad oggetto: idVx: Vehicle(x)
    vehicleNumber = numberOfVehicles  # numero di veicoli nella simulazione
    stepNumber = numberOfSteps  # numero di passi della simulazione
    bufferMode = bM
    max_avg_WTJ = 0
    min_avg_WTJ = 100000000
    max_avg_WTT = 0
    min_avg_WTT = 100000000
    max_avg_TotT = 0
    min_avg_TotT = 100000000
    max_avg_MG = 0
    min_avg_MG = 100000000
    max_avg_SG = 0
    min_avg_SG = 100000000
    nJunctionCrossed = 0
    nJunctionCrossedFreely = 0
    nTimesInTraffic = 0
    nNotFreePassage = 0
    # con il seguente ciclo inizializzo i veicoli e gli assegno una route generata casualmente
    for i in range(1, vehicleNumber + 1):
        idV = f"idV{i}"
        vehicles[f'idV{i}'] = Vehicle(f'idV{i}', instantPay)
        base_route = vehicles[idV].generateRoute(static=routeMode)
        route = traci.simulation.findRoute(base_route[0], base_route[1])
        traci.route.add(f"trip_{i}", route.edges)
        vehicles[idV].setEdgeObjective(base_route[1])
        carType = 'car' if i % 2 == 0 else 'autonomousCar'
        traci.vehicle.add(idV, f"trip_{i}", typeID=carType)
        # print(traci.route.getEdges(traci.vehicle.getRouteID(idV)))

    # ciclo che si limita ad assegnare un colore ai veicoli, per renderli meglio distinguibili
    for i in range(1, vehicleNumber):
        if i % 8 == 1:
            traci.vehicle.setColor(f'idV{i}', (0, 255, 255))  # azzurro
        if i % 8 == 2:
            traci.vehicle.setColor(f'idV{i}', (160, 100, 100))  # rosa
        if i % 8 == 3:
            traci.vehicle.setColor(f'idV{i}', (255, 0, 0))  # rosso
        if i % 8 == 4:
            traci.vehicle.setColor(f'idV{i}', (0, 255, 0))  # verde
        if i % 8 == 5:
            traci.vehicle.setColor(f'idV{i}', (0, 0, 255))  # blu
        if i % 8 == 6:
            traci.vehicle.setColor(f'idV{i}', (255, 255, 255))  # bianco
        if i % 8 == 7:
            traci.vehicle.setColor(f'idV{i}', (255, 0, 255))  # viola
        if i % 8 == 8:
            traci.vehicle.setColor(f'idV{i}', (255, 100, 0))  # arancione

    # di seguito inizializzo gli incroci che fanno parte della simulazione, assegnando loro una classe che ne descriva
    # il comportamento specifico (o incroci a 3 strade o a 4 strade).
    junctions = []  # dovrà contenere tutti gli incroci
    for i in range(1, 26):
        if i == 1 or i == 5 or i == 21 or i == 25:
            # junctions.append(TwoWayJunction(i))
            pass
        elif i % 5 == 0 or i % 5 == 1:
            # junctions.append(ThreeWayJunction(i, sM=simulationMode, bM=bufferMode))
            pass
        elif i in range(2, 5) or i in range(22, 25):
            # junctions.append(ThreeWayJunction(i, sM=simulationMode, bM=bufferMode))
            pass
        else:
            junctions.append(FourWayJunction(i, vehicles, iP=instantPay, sM=simulationMode, bM=bufferMode,
                                             groupDimension=dimensionOfGroups))

    # di seguito il ciclo entro cui avviene tutta la simulazione, una volta usciti la simulazione è conclusa.
    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        print('step', step)
        traci.simulationStep()
        step += 1
        if step == numberOfSteps:
            for veh in vehicles:
                veh = vehicles[veh]
                # Tempi in testa
                allWaitingTimesAtJunction += veh.getPassedJunctionWaitingTimes()
                avg_WTJ = sum(veh.getPassedJunctionWaitingTimes()) / max(len(veh.getPassedJunctionWaitingTimes()), 1)
                if avg_WTJ > max_avg_WTJ:
                    max_avg_WTJ = avg_WTJ
                if avg_WTJ > 0:
                    if avg_WTJ < min_avg_WTJ:
                        min_avg_WTJ = avg_WTJ
                # print('junction times ' + veh.getID(), veh.getPassedJunctionWaitingTimes())
                # print('traffic times ' + veh.getID(), veh.getPassedTrafficWaitingTimes())

                # Tempi totali
                allTotalTimes += veh.getPassedTotalWaitingTimes()
                avg_WTotT = sum(veh.getPassedTotalWaitingTimes()) / max(len(veh.getPassedTotalWaitingTimes()), 1)
                if avg_WTotT > max_avg_TotT:
                    max_avg_TotT = avg_WTotT
                if avg_WTotT > 0:
                    if avg_WTotT < min_avg_TotT:
                        min_avg_TotT = avg_WTotT

                #Tempi nel traffico
                allWaitingTimesInTraffic += veh.getPassedTrafficWaitingTimes()
                avg_WTT = sum(veh.getPassedTrafficWaitingTimes()) / max(len(veh.getPassedTrafficWaitingTimes()), 1)
                if avg_WTT > max_avg_WTT:
                    max_avg_WTT = avg_WTT
                if avg_WTT > 0:
                    if avg_WTT < min_avg_WTT:
                        min_avg_WTT = avg_WTT

                # Tempi nel gruppo principale
                allMGTimes += veh.getPassedMainGroupTimes()
                avg_MGT = sum(veh.getPassedMainGroupTimes()) / max(len(veh.getPassedMainGroupTimes()), 1)
                if avg_MGT > max_avg_MG:
                    max_avg_MG = avg_MGT
                if avg_MGT > 0:
                    if avg_MGT < min_avg_MG:
                        min_avg_MG = avg_MGT

                # Tempi nel gruppo degli sponsors
                allSGTimes += veh.getPassedSponsorGroupTimes()
                avg_SGT = sum(veh.getPassedSponsorGroupTimes()) / max(len(veh.getPassedSponsorGroupTimes()), 1)
                if avg_SGT > max_avg_SG:
                    max_avg_SG = avg_SGT
                if avg_SGT > 0:
                    if avg_SGT < min_avg_SG:
                        min_avg_SG = avg_SGT
                # print('junction times ' + veh.getID(), veh.getPassedJunctionWaitingTimes())
                # print('traffic times ' + veh.getID(), veh.getPassedTrafficWaitingTimes())

                # Statistiche relative
                nJunctionCrossed += veh.junctionCounter
                nJunctionCrossedFreely += veh.freePassageCounter
                nTimesInTraffic += veh.numberOfTimesInTraffic
                nNotFreePassage += veh.notFreePassageCounter
            traci.close()
            return max_avg_WTJ, min_avg_WTJ, max_avg_WTT, min_avg_WTT, max_avg_TotT, min_avg_TotT, max_avg_MG, \
                   min_avg_MG, max_avg_SG, min_avg_SG, nJunctionCrossed, nJunctionCrossedFreely, nTimesInTraffic, \
                   nNotFreePassage

        # riassegno una nuova route ai veicoli che raggiungono il loro obbiettivo
        for i in range(1, vehicleNumber + 1):
            vehicles[f'idV{i}'].changeTarget(staticRoutes=routeMode)
        # qui, per ogni incrocio, controllo l'arrivo di nuovi veicoli e li gestisco.
        for junction in junctions:
            # print(junction.getID())
            """Prime operazioni sull'incrocio"""
            vehAtJunction = junction.getVehiclesAtJunction()
            crossingManager = junction.getCrossingManager()
            crossingManager.updateCrossingStatus(vehicles)
            # print('h v', [i.getID() for i in crossingManager.getCrossingStatus().values() if i is not None])
            # prendo i tempi dei veicoli qualora fossero costretti a fermarsi
            vehiclesInHead = crossingManager.getCrossingStatus().values()
            vehiclesCrossing = crossingManager.getVehiclesNowCrossing()

            # print('p v', [(i.getID(), crossingManager.partecipantsRoutes[i]) for i in crossingManager.partecipants])
            # print('n s v', [i.getID() for i in crossingManager.nonStoppedVehicles])
            # if not simulationMode:
            #     print('o v', [i.getID() for j in crossingManager.orderedCooperativeList for x in j for i in x])
                # print('w v', [(i.getID(), crossingManager.partecipantsRoutes[i]) for i in crossingManager.currentWinners])
                # print('l v', [i.getID() for i in crossingManager.currentLosers])
            # print('c v', [i.getID() for i in crossingManager.getVehiclesNowCrossing() if i is not None])

            for v in vehAtJunction:
                veh = vehicles[v]
                for i in crossingManager.nonStoppedVehicles:
                    assert crossingManager.nonStoppedVehicles.count(i) == 1, i.getID()

                """Controllo lo stato dei veicoli e avvio/salvo i counter dei tempi di attesa"""
                # i veicoli che stanno attraversando non vengono considerati nel processo
                if veh not in vehiclesCrossing:
                    if veh in vehiclesInHead:
                        # if veh.getTrafficWaitingTime() != 0:
                        if not veh.hasPassedFreely:
                            if not veh.hasSaved_T:
                                veh.hasSaved_T = True
                                veh.saveTimePassedInTraffic()
                                # print(f'time in traffic saved for vehicle {veh.getID()} ({veh.getTrafficWaitingTime()})')
                        veh.resetTrafficWaitingTime()
                        if traci.vehicle.getSpeed(veh.getID()) == 0:
                            if not veh.hasPassedFreely and veh not in crossingManager.nonStoppedVehicles:
                                if veh.getJunctionWaitingTime() == 0:
                                    veh.setJunctionWaitingTime()
                                    # veh.hasPassedFreely = False
                                    # print(f'starting the time counter for {veh.getID()} (in head) ({veh.getCurrentLane()})')
                                if veh.getTotalWaitingTime() == 0:
                                    veh.setTotalWaitingTime()
                                    # veh.hasAvoidTraffic = False
                                    # print(f'starting the time counter for {veh.getID()} (total) ({veh.getCurrentLane()})')
                    else:
                        if traci.vehicle.getSpeed(veh.getID()) == 0 and not veh.hasPassedFreely:
                            if veh.getTrafficWaitingTime() == 0:
                                veh.setTrafficWaitingTime()
                                veh.hasAvoidTraffic = False
                                # print(f'starting the time counter for {veh.getID()} (in traffic) ({veh.getCurrentLane()})')
                            if veh.getTotalWaitingTime() == 0:
                                veh.setTotalWaitingTime()
                                # veh.hasAvoidTraffic = False
                                # print(f'starting the time counter for {veh.getID()} (total) ({veh.getCurrentLane()})')
                    """Sezione dei tempi di gruppo"""
                    if junction.isWithinMaxDimension(veh):
                        # if veh.getSponsorGroupWaitingTime() != 0:
                        if not veh.hasPassedFreely:
                            if not veh.hasSaved_SG:
                                veh.hasSaved_SG = True
                                veh.saveSponsorGroupWaitingTime()
                                # print(f'sponsor time saved for vehicle {veh.getID()} ({veh.getSponsorGroupWaitingTime()})')
                        veh.resetSponsorGroupWaitingTime()
                        if traci.vehicle.getSpeed(veh.getID()) == 0:
                            if not veh.hasPassedFreely and veh not in crossingManager.nonStoppedVehicles:
                                if veh.getMainGroupWaitingTime() == 0:
                                    veh.setMainGroupWaitingTime()
                                    veh.hasPassedFreely_groups = False
                                    # print(f'starting the time counter for {veh.getID()} (main vehicles) ({veh.getMainGroupWaitingTime()})')
                    else:
                        if traci.vehicle.getSpeed(veh.getID()) == 0 and not veh.hasPassedFreely:
                            if veh.getSponsorGroupWaitingTime() == 0:
                                veh.setSponsorGroupWaitingTime()
                                veh.hasAvoidTraffic_groups = False
                                # print(
                                #     f'starting the time counter for {veh.getID()} (sponsor) ({veh.getSponsorGroupWaitingTime()})')

            """Controllo che non ci siano errori di posizionamento su corsia"""
            for veh in vehiclesInHead:
                # if veh is not None:
                #     print('checking wrong lane', veh.getID(), veh.distanceFromEndLane())
                if veh is not None and veh.distanceFromEndLane() < 20:
                    if not veh.checkPosition(junction):
                        veh.changeTarget(momentaryChange=True, junction=junction)

            """Flusso principale"""
            for idVeh in vehAtJunction:
                if idVeh in vehicles:
                    objVeh = vehicles[idVeh]
                    if bufferMode:
                        if objVeh.notFreePassageCounter != 0 and objVeh.notFreePassageCounter % 10 == 0:
                            objVeh.fillWallet(randint(100, 250))

                    if objVeh.distanceFromEndLane() < 50:
                        if objVeh not in crossingManager.getCurrentPartecipants():
                            crossingManager.updateVehicleStatus(objVeh)

                        if objVeh.distanceFromEndLane() < 20:
                            if bufferMode:
                                if simulationMode:
                                    if objVeh in crossingManager.getCurrentLosers() and objVeh.checkPosition(
                                            junction):
                                        junction.createAuction(objVeh, vehicles)
                                else:
                                    if objVeh not in crossingManager.vehiclesInAuction and objVeh.checkPosition(
                                            junction):
                                        junction.createAuction(objVeh, vehicles)
                            else:
                                """Ramo d'interesse"""
                                if objVeh in crossingManager.getCrossingStatus().values() and objVeh not in \
                                        crossingManager.getVehiclesInAuction() and objVeh.checkPosition(junction)\
                                        and objVeh not in crossingManager.nonStoppedVehicles:
                                    # print('c a b v', objVeh.getID(), objVeh not in crossingManager.
                                    #       getVehiclesInAuction())
                                    # print('c a i a v', [z.getID() for z in crossingManager.getVehiclesInAuction() if
                                    #                     z is not None])
                                    # print('c a w v', [z.getID() for z in crossingManager.getCurrentWinners() if
                                    #                     z is not None])
                                    # print('c a l v', [z.getID() for z in crossingManager.getCurrentLosers() if
                                    #                   z is not None])
                                    junction.createAuction(objVeh, vehicles)
            if len(vehAtJunction) > 0:
                # print('precross', [i for i in vehAtJunction])
                crossingManager.allowCrossing()


if __name__ == "__main__":
    from sumolib import checkBinary

    sumoBinary = checkBinary('sumo')
    # sumoCmd = [sumoBinary, "-c", "provaStop.sumocfg"]
    sumoCmd = [sumoBinary, "-c", "autonomousDrivingSimulator.sumocfg", "--time-to-teleport", "-1"]
    combinations = [
                    # (True, True, True, 1), (True, True, True, 5), (True, True, True, -1),
                    # (True, True, False, 1), (True, True, False, 5), (True, True, False, -1),
                    # (True, False, True, 1), (True, False, True, 5),(True, False, True, -1),
                    # (False, True, True, 1), (False, True, True, 5),(False, True, True, -1),
                    # (True, False, False, 1), (True, False, False, 5), (True, False, False, -1),
                    # (False, True, False, 1), (False, True, False, 5), (False, True, False, -1),
                    # (False, False, True, 1), (False, False, True, 5), (False, False, True, -1),
                    # (False, False, False, 1), (False, False, False, 5), (False, False, False, -1)
                    ]
    # combinations = [(True, True), (False, True)]
    # combinations = [(True, False), (False, False)]
    # combinations = [(False, True), (False, False)]
    ipDict = {True: 'All-Vehicles-Pay_(AWP)', False: 'Only-Winners-Pay_(OWP)'}
    smDict = {True: 'Competitive_approach', False: 'Cooperative_approach'}
    routeDict = {True: 'Static_Routes', False: 'Random_Routes'}
    numberOfSteps = 5000
    numberOfVehiclesSet = [150]
    for nV in numberOfVehiclesSet:
        if nV == 150:
            combinations = [
                # (True, True, True, 1), (True, True, True, 5), (True, True, True, -1),
                # (True, True, False, 1), (True, True, False, 5), (True, True, False, -1),
                # (True, False, True, 1),
                (True, False, True, 5), (True, False, True, -1),
                #(False, True, True, 1),
                (False, True, True, 5), (False, True, True, -1),
                # (True, False, False, 1), (True, False, False, 5), (True, False, False, -1),
                # (False, True, False, 1), (False, True, False, 5), (False, True, False, -1),
                # (False, False, True, 1), (False, False, True, 5), (False, False, True, -1),
                # (False, False, False, 1), (False, False, False, 5), (False, False, False, -1)
            ]
        else:
            combinations = [
                # (True, True, True, 1), (True, True, True, 5), (True, True, True, -1),
                # (True, True, False, 1), (True, True, False, 5), (True, True, False, -1),
                (True, False, True, 1), (True, False, True, 5), (True, False, True, -1),
                (False, True, True, 1), (False, True, True, 5), (False, True, True, -1),
                # (True, False, False, 1), (True, False, False, 5), (True, False, False, -1),
                # (False, True, False, 1), (False, True, False, 5), (False, True, False, -1),
                # (False, False, True, 1), (False, False, True, 5), (False, False, True, -1),
                # (False, False, False, 1), (False, False, False, 5), (False, False, False, -1)
            ]
        for c in combinations:
            sM = c[0]
            iP = c[1]
            rM = c[2]
            dim = c[3]
            traci.start(sumoCmd)
            # da eliminare lasciando solo il run() quando non in debugging
            # try:
            # di default la simulazione utilizza l'algoritmo competitivo con pagamento dei soli vincitori
            # simulationMode = True => algoritmo competitivo, = False => algoritmo cooperativo
            allWaitingTimesAtJunction = []
            allWaitingTimesInTraffic = []
            allTotalTimes = []
            allMGTimes = []
            allSGTimes = []
            max_avg_WTJ, min_avg_WTJ, max_avg_WTT, min_avg_WTT, max_avg_WTotT, min_avg_WTotT, max_avg_MG, \
            min_avg_MG, max_avg_SG, min_avg_SG, num_of_traversed_junction, free_lanes, nTimesInTraffic, nNotFreePassage = \
                run(allWaitingTimesAtJunction, allWaitingTimesInTraffic, allTotalTimes, allMGTimes, allSGTimes,
                    True, nV, numberOfSteps, simulationMode=sM, instantPay=iP, routeMode=rM, bM=False,
                    dimensionOfGroups=dim)
            original_stdout = sys.stdout
            f = open(f"risultati/num_veh_{nV}/results_{smDict[sM]}_{ipDict[iP]}_{routeDict[rM]}_dim_{dim}.txt", "w+")
            sys.stdout = f

            """Junction Times"""
            avgTJ = sum(allWaitingTimesAtJunction) / max(1, len(allWaitingTimesAtJunction))
            print('avgTJ: ', avgTJ)
            stdDvBase = 0
            for i in allWaitingTimesAtJunction:
                stdDvBase += (i - avgTJ) ** 2
            stdDvBase /= max(1, len(allWaitingTimesAtJunction))
            stdDvTJ = sqrt(stdDvBase)
            print('stdDvTJ: ', stdDvTJ)
            allWaitingTimesAtJunction = [i for i in allWaitingTimesAtJunction if i != 0]
            avgTJ = sum(allWaitingTimesAtJunction) / max(1, len(allWaitingTimesAtJunction))
            print('avgTJ without 0: ', avgTJ)
            stdDvBase = 0
            for i in allWaitingTimesAtJunction:
                stdDvBase += (i - avgTJ) ** 2
            stdDvBase /= max(1, len(allWaitingTimesAtJunction))
            stdDvTJ = sqrt(stdDvBase)
            print('stdDvTJ without 0: ', stdDvTJ)
            print('maxTJ: ', max_avg_WTJ)
            print('minTJ: ', min_avg_WTJ)

            print()
            """Traffic Times"""
            avgTT = sum(allWaitingTimesInTraffic) / max(1, len(allWaitingTimesInTraffic))
            print('avgTT: ', avgTT)
            stdDvBase = 0
            for i in allWaitingTimesInTraffic:
                stdDvBase += (i - avgTT) ** 2
            stdDvBase /= max(1, len(allWaitingTimesInTraffic))
            stdDvTT = sqrt(stdDvBase)
            print('stdDvTT: ', stdDvTT)
            allWaitingTimesInTraffic = [i for i in allWaitingTimesInTraffic if i != 0]
            avgTT = sum(allWaitingTimesInTraffic) / max(1, len(allWaitingTimesInTraffic))
            print('avgTT without 0: ', avgTT)
            stdDvBase = 0
            for i in allWaitingTimesInTraffic:
                stdDvBase += (i - avgTT) ** 2
            stdDvBase /= max(1, len(allWaitingTimesInTraffic))
            stdDvTT = sqrt(stdDvBase)
            print('stdDvTT without 0: ', stdDvTT)
            print('maxTT: ', max_avg_WTT)
            print('minTT: ', min_avg_WTT)

            print()
            """Total Times"""
            avgTotT = sum(allTotalTimes) / max(1, len(allTotalTimes))
            print('avgTotT: ', avgTotT)
            stdDvBase = 0
            for i in allTotalTimes:
                stdDvBase += (i - avgTotT) ** 2
            stdDvBase /= max(1, len(allTotalTimes))
            stdDvTotT = sqrt(stdDvBase)
            print('stdDvTotT: ', stdDvTotT)
            allTotalTimes = [i for i in allTotalTimes if i != 0]
            avgTotT = sum(allTotalTimes) / max(1, len(allTotalTimes))
            print('avgTotT without 0: ', avgTotT)
            stdDvBase = 0
            for i in allTotalTimes:
                stdDvBase += (i - avgTotT) ** 2
            stdDvBase /= max(1, len(allTotalTimes))
            stdDvTotT = sqrt(stdDvBase)
            print('stdDvTotT without 0: ', stdDvTotT)
            print('maxTotT: ', max_avg_WTotT)
            print('minTotT: ', min_avg_WTotT)

            print()
            """Main Group Times"""
            avgMGT = sum(allMGTimes) / max(1, len(allMGTimes))
            print('avgMGT: ', avgMGT)
            stdDvBase = 0
            for i in allMGTimes:
                stdDvBase += (i - avgMGT) ** 2
            stdDvBase /= max(1, len(allMGTimes))
            stdDvMGT = sqrt(stdDvBase)
            print('stdDvMGT: ', stdDvMGT)
            allMGTimes = [i for i in allMGTimes if i != 0]
            avgMGT = sum(allMGTimes) / max(1, len(allMGTimes))
            print('avgMGT without 0: ', avgMGT)
            stdDvBase = 0
            for i in allMGTimes:
                stdDvBase += (i - avgMGT) ** 2
            stdDvBase /= max(1, len(allMGTimes))
            stdDvMGT = sqrt(stdDvBase)
            print('stdDvMGT without 0: ', stdDvMGT)
            print('maxMGT: ', max_avg_MG)
            print('minMGT: ', min_avg_MG)

            print()
            """Sponsor Group Times"""
            avgSGT = sum(allSGTimes) / max(1, len(allSGTimes))
            print('avgSGT: ', avgSGT)
            stdDvBase = 0
            for i in allSGTimes:
                stdDvBase += (i - avgSGT) ** 2
            stdDvBase /= max(1, len(allSGTimes))
            stdDvSGT = sqrt(stdDvBase)
            print('stdDvSGT: ', stdDvSGT)
            allSGTimes = [i for i in allSGTimes if i != 0]
            avgSGT = sum(allSGTimes) / max(1, len(allSGTimes))
            print('avgSGT without 0: ', avgSGT)
            stdDvBase = 0
            for i in allSGTimes:
                stdDvBase += (i - avgSGT) ** 2
            stdDvBase /= max(1, len(allSGTimes))
            stdDvSGT = sqrt(stdDvBase)
            print('stdDvSGT without 0: ', stdDvSGT)
            print('maxSGT: ', max_avg_SG)
            print('minSGT: ', min_avg_SG)

            print()
            """Lanes %"""
            free_lanes_perc = free_lanes / max(1, num_of_traversed_junction) * 100
            print('free lanes %: ', free_lanes_perc, '%, number of free traverse: ', free_lanes, 'num of traverse',
                  num_of_traversed_junction)
            nTimesInTrafficPerc = nTimesInTraffic / max(1, num_of_traversed_junction) * 100
            print('number of times in traffic %: ', nTimesInTrafficPerc, '%, numero di volte nel traffico: ',
                  nTimesInTraffic, 'num of traverse',
                  num_of_traversed_junction)
            not_free_passage_perc = nNotFreePassage / max(1, num_of_traversed_junction) * 100
            print('not free passage %: ', not_free_passage_perc, '%, number of not free passage: ', nNotFreePassage, 'num of traverse',
                  num_of_traversed_junction)

            """All times complete"""
            print('junction times\n', allWaitingTimesAtJunction, '\n')
            print('traffic times\n', allWaitingTimesInTraffic, '\n')
            print('total times\n', allTotalTimes, '\n')
            print('MGT times\n', allMGTimes, '\n')
            print('SGT times\n', allSGTimes)
            sys.stdout = original_stdout
            f.close()
