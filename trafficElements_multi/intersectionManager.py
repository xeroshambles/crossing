import math

import traci

###########################################################################
###########################################################################
###########################################################################
###########################################################################
###########################################################################
###########################################################################
###########################################################################
###########################################################################
###########################################################################
###########################################################################
###########################################################################
###########################################################################


class IntersectionManager:
    """Classe per gestire le prenotazioni di tutti gli incroci"""

    def __init__(self, junction, cellsPerSide, matrixTrajectories, securitySecs):
        self.junction = junction  # incrocio su cui agisce l'intersection manager
        self.cellsPerSide = cellsPerSide  # numero di celle per lato dell'incrocio
        self.matrixTrajectories = matrixTrajectories  # traiettorie calcolate in pre-processing
        self.securitySecs = securitySecs  # secondi di sicurezza per il passaggio dei veicoli
        self.waitingList = []  # ordine di arrivo su lista, si resetta quando le auto liberano incrocio
        self.passageList = []  # auto in passaggio nell'incrocio
        self.arrivalList = []  # auto entrate nelle vicinanze dell'incrocio, non si resetta
        self.crossingMatrix = []  # rappresenta la suddivisione matriciale dell'incrocio (in celle)
        self.exitList = []  # auto uscite dall'incrocio, non si resetta
        self.stoppedList = []  # lista di auto ferme allo stop

        shape = traci.junction.getShape(junction.junctionID)
        self.stop = []
        self.stopCoordinates(shape)  # lista che indica di quanto si distanzia lo stop dal centro
        # dell'incrocio [dx, sotto, sx, sopra]

        self.centerJunctionId = traci.junction.getPosition(junction.junctionID)  # coordinate (x,y) del centro di un
        # incrocio
        self.cellPassage = []  # salvo in che cella si trova l'auto in passaggio [cross_id][ [auto , cella_X ,
        # cella_Y ], ...]
        self.slowedList = []  # lista di auto rallentate in prossimità dell'incrocio
        self.precPassage = []  # salvo l'ultima situazione di auto in passaggio per rilasciarle all'uscita

        self.cellsLimitsX = []  # utile per verificare l'appartenenza ad una cella all'interno della matrice
        self.cellsLimitsY = []  # utile per verificare l'appartenenza ad una cella all'interno della matrice
        self.cellsLimits()

        # popolo la matrice dell'incrocio
        for x in range(0, cellsPerSide):
            self.crossingMatrix.append([])
            for y in range(0, cellsPerSide):
                # ogni cella è un'array dei tempi stimati di occupazione della medesima
                self.crossingMatrix[x].append([])

        # trovo lunghezza e altezza auto in celle
        x_cell_in_m = abs(self.cellsLimitsX[1] - self.cellsLimitsX[0])
        y_cell_in_m = abs(self.cellsLimitsY[1] - self.cellsLimitsY[0])
        x_vehicle_in_m = traci.vehicle.getHeight("idV0")
        y_vehicle_in_m = traci.vehicle.getLength("idV0")
        self.xVehiclesInCells = float(x_vehicle_in_m) / float(x_cell_in_m)
        self.yVehiclesInCells = float(y_vehicle_in_m) / float(y_cell_in_m)

    def getLaneIndexFromEdges(self, edges, vehicle):
        """Funzione che trova la lane corretta da far seguire al veicolo dati il nodo di partenza e quello di
        destinazione correnti"""

        distance = -1
        i = 0
        found = False

        start = int(edges[vehicle.edgeIndex][1:3])
        end = int(edges[vehicle.edgeIndex + 1][4:6])

        while True:
            if self.junction.node_ids[i % 4] == start:
                found = True
            if found:
                distance += 1
                if self.junction.node_ids[i % 4] == end:
                    break
            i += 1

        lane = 0

        if distance == 1:
            lane = 2
        if distance == 2:
            lane = 1
        if distance == 3:
            lane = 0

        return lane, start, end

    def getRoute(self, vehicle):
        """Funzione che restituisce l'identificativo della route corretta calcolata in fase di pre-processing"""

        route = traci.vehicle.getRouteID(vehicle.idVehicle)
        edges = traci.route.getEdges(route)

        suffix, start, end = self.getLaneIndexFromEdges(edges, vehicle)

        if suffix == 0:
            if start - end == -4 or (start - end == -25 and end == 51) or start - end == 26 or start - end == -55:
                return 'route_2'
            if start - end == -24 or start - end == 6 or (start - end == 25 and start == 55) or start - end == 55:
                return 'route_3'
            if start - end == -45 or (start - end == -25 and end == 75) or start - end == 4 or start - end == 24:
                return 'route_7'
            if start - end == -26 or start - end == -6 or (start - end == 25 and start == 71) or start - end == 45:
                return 'route_11'
        if suffix == 1:
            if start - end == -30 or start - end == -10 or start - end == 20:
                return 'route_1'
            if start - end == -49 or start - end == 2 or start - end == 51:
                return 'route_5'
            if start - end == -20 or start - end == 10 or start - end == 30:
                return 'route_6'
            if start - end == -51 or start - end == -2 or start - end == 49:
                return 'route_10'
        if suffix == 2:
            if start - end == -55 or (start - end == -25 and end == 55) or start - end == -6 or start - end == 24:
                return 'route_0'
            if start - end == -24 or start - end == -4 or (start - end == 25 and start == 75) or start - end == 45:
                return 'route_4'
            if start - end == -45 or (start - end == -25 and end == 71) or start - end == 6 or start - end == 26:
                return 'route_8'
            if start - end == -26 or start - end == 4 or (start - end == 25 and start == 51) or start - end == 55:
                return 'route_9'

    def stopCoordinates(self, shape):
        """Calcolo gli estremi dell'incrocio, dove sono presenti gli stop"""

        for count in range(0, len(shape) - 1):
            if shape[count][0] == shape[count + 1][0]:
                self.stop.append(shape[count][0])
            elif shape[count][1] == shape[count + 1][1]:
                self.stop.append(shape[count][1])

    def cellsLimits(self):
        """Calcolo i metri all'interno dell'incrocio di ogni cella della matrice"""

        # lunghezza totale incrocio nell'asse X e Y
        length_X = self.stop[1] - self.stop[3]
        length_Y = self.stop[0] - self.stop[2]

        # lunghezza di una sola cella
        cell_length_X = float(length_X) / float(self.cellsPerSide)
        cell_length_Y = float(length_Y) / float(self.cellsPerSide)

        for i in range(0, self.cellsPerSide + 1):  # scrivo sui vettori
            self.cellsLimitsX.append(round((self.stop[3] + (cell_length_X * i)), 3))
            self.cellsLimitsY.append(round((self.stop[0] - (cell_length_Y * i)), 3))

    def getCellFromPosVehicle(self, vehicle):
        """Ritorno le coordinate della cella nella matrice in cui si trova l'auto"""

        cell_X = 0
        cell_Y = 0
        pos = traci.vehicle.getPosition(vehicle)

        for x in range(0, len(self.cellsLimitsX) - 1):
            if self.cellsLimitsX[x] <= pos[0] <= self.cellsLimitsX[x + 1]:
                cell_X = x

        for y in range(0, len(self.cellsLimitsY) - 1):
            if self.cellsLimitsY[y] >= pos[1] >= self.cellsLimitsY[y + 1]:
                cell_Y = y

        return [vehicle, cell_X, cell_Y]

    def inCrossing(self, pos):
        """Controllo se l'auto è all'incrocio"""

        if (self.stop[3] <= pos[0] <= self.stop[1]) and \
                (self.stop[2] <= pos[1] <= self.stop[0]):
            return True
        else:
            return False

    def metersFromCrossing(self, vehicle):
        """Calcolo la distanza dell'auto in metri dall'incrocio come numero negativo (l'inizio dell'incrocio è 0)"""

        pos = traci.vehicle.getPosition(vehicle)
        ang = traci.vehicle.getAngle(vehicle)
        dist = 0
        if ang == 0:
            dist = abs(float(self.stop[2]) - float(pos[1]))
        if ang == 180:
            dist = abs(float(self.stop[0]) - float(pos[1]))
        if ang == 90:
            dist = abs(float(self.stop[3]) - float(pos[0]))
        if ang == 270:
            dist = abs(float(self.stop[1]) - float(pos[0]))
        dist = 0 - dist
        return dist

    def arrivalTimeCell(self, vehicle, metersFromCrossing, metersFromCell):
        """Calcolo il timestep di arrivo sulla cella"""

        vi = traci.vehicle.getSpeed(vehicle)
        vf = traci.vehicle.getMaxSpeed(vehicle)
        a = traci.vehicle.getAccel(vehicle)
        xa = (((vf * vf) - (vi * vi)) / (float(2) * a)) + metersFromCrossing
        t1 = (- vi + math.sqrt((vi * vi) + (float(2) * a) * (xa - metersFromCrossing))) / a
        t2 = (metersFromCell - xa) / vf
        t = t1 + t2
        t = round(t, 4)

        return t + traci.simulation.getTime()

    def occupiedCellsGivenAng(self, ang):
        """Restituisce le celle occupate data l'angolazione del veicolo, centrate in [0][0]"""

        occupied_cells = []
        ang = ang % 180
        ang = - ang
        x_vehicle = self.xVehiclesInCells * 1.2
        y_vehicle = self.yVehiclesInCells * 1.1

        ang = math.radians(ang)  # converto in radianti
        a1 = [- float(x_vehicle) / float(2), float(y_vehicle) / float(2)]
        a2 = [float(x_vehicle) / float(2), float(y_vehicle) / float(2)]
        b1 = [- float(x_vehicle) / float(2), - float(y_vehicle) / float(2)]
        b2 = [float(x_vehicle) / float(2), - float(y_vehicle) / float(2)]

        # coordinate degli angoli ruotati
        a1 = [round(a1[0] * math.cos(ang) - a1[1] * math.sin(ang), 4),
              round(a1[0] * math.sin(ang) + a1[1] * math.cos(ang), 4)]
        a2 = [round(a2[0] * math.cos(ang) - a2[1] * math.sin(ang), 4),
              round(a2[0] * math.sin(ang) + a2[1] * math.cos(ang), 4)]
        b1 = [round(b1[0] * math.cos(ang) - b1[1] * math.sin(ang), 4),
              round(b1[0] * math.sin(ang) + b1[1] * math.cos(ang), 4)]
        b2 = [round(b2[0] * math.cos(ang) - b2[1] * math.sin(ang), 4),
              round(b2[0] * math.sin(ang) + b2[1] * math.cos(ang), 4)]

        r1 = [a2[1] - a1[1], a1[0] - a2[0], - a1[0] * a2[1] + a2[0] * a1[1]]
        r2 = [b2[1] - a2[1], a2[0] - b2[0], - a2[0] * b2[1] + b2[0] * a2[1]]
        r3 = [b2[1] - b1[1], b1[0] - b2[0], - b1[0] * b2[1] + b2[0] * b1[1]]
        r4 = [b1[1] - a1[1], a1[0] - b1[0], - a1[0] * b1[1] + b1[0] * a1[1]]

        # per ogni cella guardo se uno dei 4 angoli e' all'interno del rettangolo
        maximus = max([x_vehicle, y_vehicle])
        for y_cell in range(-int(maximus / 2) - 3, int(maximus / 2) + 4):
            for x_cell in range(-int(maximus / 2) - 3, int(maximus / 2) + 4):
                inserted = False
                if not inserted and (r1[0] * (x_cell - 0.5) + r1[1] * (y_cell - 0.5) + r1[2] >= 0) and \
                        (r2[0] * (x_cell - 0.5) + r2[1] * (y_cell - 0.5) + r2[2] >= 0) and \
                        (r3[0] * (x_cell - 0.5) + r3[1] * (y_cell - 0.5) + r3[2] <= 0) and \
                        (r4[0] * (x_cell - 0.5) + r4[1] * (y_cell - 0.5) + r4[2] <= 0):
                    occupied_cells.append([y_cell, x_cell])
                    inserted = True
                if not inserted and (r1[0] * (x_cell + 0.5) + r1[1] * (y_cell - 0.5) + r1[2] >= 0) and \
                        (r2[0] * (x_cell + 0.5) + r2[1] * (y_cell - 0.5) + r2[2] >= 0) and \
                        (r3[0] * (x_cell + 0.5) + r3[1] * (y_cell - 0.5) + r3[2] <= 0) and \
                        (r4[0] * (x_cell + 0.5) + r4[1] * (y_cell - 0.5) + r4[2] <= 0):
                    occupied_cells.append([y_cell, x_cell])
                    inserted = True
                if not inserted and (r1[0] * (x_cell - 0.5) + r1[1] * (y_cell + 0.5) + r1[2] >= 0) and \
                        (r2[0] * (x_cell - 0.5) + r2[1] * (y_cell + 0.5) + r2[2] >= 0) and \
                        (r3[0] * (x_cell - 0.5) + r3[1] * (y_cell + 0.5) + r3[2] <= 0) and \
                        (r4[0] * (x_cell - 0.5) + r4[1] * (y_cell + 0.5) + r4[2] <= 0):
                    occupied_cells.append([y_cell, x_cell])
                    inserted = True
                if not inserted and (r1[0] * (x_cell + 0.5) + r1[1] * (y_cell + 0.5) + r1[2] >= 0) and \
                        (r2[0] * (x_cell + 0.5) + r2[1] * (y_cell + 0.5) + r2[2] >= 0) and \
                        (r3[0] * (x_cell + 0.5) + r3[1] * (y_cell + 0.5) + r3[2] <= 0) and \
                        (r4[0] * (x_cell + 0.5) + r4[1] * (y_cell + 0.5) + r4[2] <= 0):
                    occupied_cells.append([y_cell, x_cell])
                    inserted = True

        return occupied_cells

    def arrivalVehicle(self, vehicle):
        """Gestisco l'arrivo dell'auto in prossimità dello stop"""

        if not self.getFromCrossingMatrix(vehicle):
            # faccio fermare l'auto
            self.stoppedList.append(vehicle.idVehicle)
            traci.vehicle.setSpeed(vehicle.idVehicle, 0.0)
        # l'auto può passare, la segno nella matrice e nei vettori
        else:
            # disattivo la safe speed del veicolo
            traci.vehicle.setSpeedMode(vehicle.idVehicle, 30)
            self.passageList.append([vehicle.idVehicle, traci.vehicle.getRoadID(vehicle.idVehicle),
                                     traci.vehicle.getAngle(vehicle.idVehicle)])
            # tolgo l'auto dalla lista d'attesa e la sottoscrivo nella matrice
            self.waitingList.pop(self.waitingList.index(vehicle.idVehicle))
            self.setInCrossingMatrix(vehicle)

            route = traci.vehicle.getRouteID(vehicle.idVehicle)
            edges = traci.route.getEdges(route)
            lane = self.getLaneIndexFromEdges(edges, vehicle)
            # se l'auto non gira a destra
            if lane != 0:
                self.cellPassage.append([vehicle.idVehicle, None, None])
            # se l'auto gira a destra la faccio rallentare fino a dimezzarne la velocità
            else:
                traci.vehicle.setSpeed(vehicle.idVehicle, traci.vehicle.getMaxSpeed(vehicle.idVehicle) / float(2))

    def setInCrossingMatrix(self, vehicle):
        """Segna sulla matrice_incrocio l'occupazione delle celle toccate dall'auto durante l'attraversamento"""

        rou = self.getRoute(vehicle)

        for route in self.matrixTrajectories:
            if route[0] == rou:
                for cells in route[1]:
                    # calcolo timestep di arrivo su tale cella
                    timestep = self.arrivalTimeCell(vehicle.idVehicle,
                                                    self.metersFromCrossing(vehicle.idVehicle), cells[2])
                    occupied_cells = self.occupiedCellsGivenAng(cells[3])
                    # controllo le celle occupate dall'auto
                    for surrounding_cells in occupied_cells:
                        index_y = surrounding_cells[0]
                        index_x = surrounding_cells[1]
                        if ((cells[0] + index_y) >= 0) and ((cells[1] + index_x) >= 0) and \
                                ((cells[0] + index_y) < len(self.crossingMatrix)) and \
                                ((cells[1] + index_x) < len(self.crossingMatrix)):
                            self.crossingMatrix[cells[0] + index_y][cells[1] + index_x].append(round(timestep, 4))

    def getFromCrossingMatrix(self, vehicle):
        """Data l'auto e la matrice dell'incrocio restituisce True se non sono state rilevate collisioni
        dall'attuale situazione di passaggio rilevata all'interno della matrice, False se sono rilevate collisioni"""

        rou = self.getRoute(vehicle)

        free = True

        for route in self.matrixTrajectories:
            if route[0] == rou and free:
                for cells in route[1]:
                    timestep = self.arrivalTimeCell(vehicle.idVehicle,
                                                    self.metersFromCrossing(vehicle.idVehicle), cells[2])
                    occupied_cells = self.occupiedCellsGivenAng(cells[3])
                    # controllo le celle occupate dall'auto
                    for surrounding_cells in occupied_cells:
                        index_y = surrounding_cells[0]
                        index_x = surrounding_cells[1]
                        if ((cells[0] + index_y) >= 0) and ((cells[1] + index_x) >= 0) and \
                                ((cells[0] + index_y) < len(self.crossingMatrix)) and \
                                ((cells[1] + index_x) < len(self.crossingMatrix)):
                            # scorre i tempi di occupazione segnati all'interno della cella
                            for t in self.crossingMatrix[cells[0] + index_y][cells[1] + index_x]:
                                # controlla che il timestep di arrivo calcolato non cada in un range di sicurezza
                                # dal valore selezionato
                                if t - self.securitySecs <= timestep <= t + self.securitySecs:
                                    free = False
                                    break

        return free

    def freePath(self, vehicles):
        """Controllo se è cambiata la situazione all'interno dell'incrocio"""

        for x in self.passageList:

            route = traci.vehicle.getRouteID(x[0])
            edges = traci.route.getEdges(route)
            lane = self.getLaneIndexFromEdges(edges, vehicles[x[0]])
            # se l'auto non gira a destra
            if lane != 0:
                for y in self.cellPassage:
                    if x[0] == y[0]:

                        pos = traci.vehicle.getPosition(x[0])
                        # se l'auto è ancora nell'incrocio
                        if self.inCrossing(pos):

                            cell = self.getCellFromPosVehicle(x[0])
                            actual_pos_X = cell[1]
                            actual_pos_Y = cell[2]
                            # se la posizione dell'auto nelle celle cambia
                            if actual_pos_X != y[1] or actual_pos_Y != y[2]:
                                # aggiorno poi il vettore con la nuova posizione della cella in cui si trova l'auto
                                self.cellPassage[self.cellPassage.index(y)] = [y[0], actual_pos_X,
                                                                               actual_pos_Y]
                        # se l'auto è uscita dall'incrocio
                        else:
                            # se ho None allora l'auto non è ancora entrata nell'incrocio e non la tolgo
                            if y[1] is not None and y[2] is not None:
                                self.passageList.pop(self.passageList.index(x))
                                self.cellPassage.pop(self.cellPassage.index(y))
            # se gira a destra guardo se cambia strada e la tolgo dal vettore passaggio
            else:
                road = self.nextStreet()
                if traci.vehicle.getRoadID(x[0]) == road:
                    self.passageList.pop(self.passageList.index(x))
                    # faccio riaccelerare l'auto
                    traci.vehicle.setSpeed(x[0], traci.vehicle.getMaxSpeed(x[0]) * 4)

    def forwardVehicle(self, vehicle):
        """Faccio avanzare le auto"""

        traci.vehicle.setSpeedMode(vehicle.idVehicle, 30)

        traci.vehicle.setSpeed(vehicle.idVehicle, traci.vehicle.getMaxSpeed(vehicle.idVehicle))  # riparte l'auto
        self.passageList.append([vehicle.idVehicle, traci.vehicle.getRoadID(vehicle.idVehicle),
                                 traci.vehicle.getAngle(vehicle.idVehicle)])
        self.setInCrossingMatrix(vehicle)

        if self.stoppedList:
            try:
                self.stoppedList.pop(self.stoppedList.index(vehicle.idVehicle))  # tolgo dalla lista di auto ferme
            except ValueError:  # per le auto che faccio partire senza fermare non serve toglerle dalla lista
                pass
        self.waitingList.pop(self.waitingList.index(vehicle.idVehicle))  # tolgo dalla lista l'auto
        self.cellPassage.append([vehicle.idVehicle, None, None])

    def nextStreet(self):
        """Ottengo il nome della via a cui l'auto e' diretta"""

        route = traci.vehicle.getRoute(self.passageList[0])  # ottengo rotta dell'auto che sta attraversando
        att_road = self.passageList[1]  # strada attuale
        next_road_id = route.index(att_road) + 1  # posizione nel vettore attuale via + 1 = prossima
        next_road = route[next_road_id]  # prossima strada
        return next_road

    def cleanMatrix(self):
        "Ogni 10 step pulisco la matrice da valori vecchi"

        for y in self.crossingMatrix:
            index_y = self.crossingMatrix.index(y)
            for x in self.crossingMatrix[index_y]:
                index_x = self.crossingMatrix[index_y].index(x)
                for val in self.crossingMatrix[index_y][index_x]:
                    index_val = self.crossingMatrix[index_y][index_x].index(val)
                    if val < (traci.simulation.getTime() - self.securitySecs - 1):
                        self.crossingMatrix[index_y][index_x].pop(index_val)
