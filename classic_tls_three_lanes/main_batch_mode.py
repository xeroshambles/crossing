import sys
import os
import main
from math import sqrt
from multiprocessing import Pool
import matplotlib

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Dichiarare la variabile d'ambiente 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa

config_file = "intersection.sumocfg"
junction_id = 7
lanes_per_road = 3
lanes = []
node_ids = [2, 6, 8, 12]

for i in node_ids:
    for lane in range(0, lanes_per_road):
        lanes.append(f'e{"0" if i < 12 else ""}{i}_0{junction_id}_{lane}')
        lanes.append(f'e0{junction_id}_{"0" if i < 12 else ""}{i}_{lane}')


def printFile(s, f):
    print(s, file=f)


if __name__ == "__main__":
    choice = ''
    schema = 'n'
    while choice not in ['d', 'D', 'g', 'G']:
        choice = input('\nVuoi raccogliere dati o avere una visualizzazione grafica? (d = dati, g = grafica): ')
        if choice not in ['d', 'D', 'g', 'G']:
            print('\nInserire un carattere tra d e g!')
    if choice in ['d', 'D']:
        sumoBinary = checkBinary('sumo')
        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"]
    else:
        sumoBinary = checkBinary('sumo-gui')
        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"]
        choice = ''
        while choice not in ['s', 'S', 'n', 'N']:
            choice = input('\nDesideri visualizzare le auto con uno schema di colori significativo? (s, n): ')
            if choice not in ['s', 'S', 'n', 'N']:
                print('\nInserire un carattere tra s e n!')
        schema = choice
    diffSim = 0
    while diffSim <= 0:
        diffSim = int(input('\nInserire il numero di simulazioni diverse: '))
        if diffSim <= 0:
            print('\nInserire un numero di simulazioni positivo!')
    port = 60000
    for i in range(1, diffSim + 1):
        with open(f"output_batch_{i}.txt", "w") as f:
            repeatSim = 0
            while repeatSim <= 0:
                repeatSim = int(input(f'\nInserire il numero di esecuzioni della simulazione {i}: '))
                if repeatSim <= 0:
                    print('\nInserire un numero di simulazioni positivo!')
            numberOfVehicles = 0
            while numberOfVehicles <= 0:
                numberOfVehicles = int(input(f'\nInserire il numero di veicoli nella simulazione {i}: '))
                if numberOfVehicles <= 0:
                    print('\nInserire un numero di veicoli positivo!')
            pool = Pool(processes=repeatSim)
            pool_arr = []
            for j in range(0, repeatSim):
                pool_arr.append(pool.apply_async(main.run, (numberOfVehicles, schema, port, sumoCmd)))
                port += 1
            pool.close()
            totalTimeArr = []
            meanHeadTimeArr = []
            varHeadTimeArr = []
            stDevHeadTimeArr = []
            maxHeadTimeArr = []
            meanTailTimeArr = []
            varTailTimeArr = []
            stDevTailTimeArr = []
            maxTailTimeArr = []
            meanSpeedArr = []
            maxSpeedArr = []
            meanTailLengthArr = []
            maxTailLengthArr = []
            nStoppedVehiclesArr = []
            meanThroughputArr = []
            for j in range(0, repeatSim):
                ret = pool_arr[j].get()
                printFile('----------------------------------------------------\n', f)
                printFile(f'SIMULAZIONE NUMERO {i}:{j}\n', f)
                printFile('----------------------------------------------------\n', f)
                printFile(f'NUMERO DI VEICOLI: {numberOfVehicles}\n', f)
                printFile(f'TEMPO TOTALE DI SIMULAZIONE: {ret[0]} step\n', f)
                totalTimeArr.append(ret[0])
                printFile(f'TEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(ret[1], 2)} step\n', f)
                meanHeadTimeArr.append(ret[1])
                printFile(f'VARIANZA DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(ret[2], 2)} step\n', f)
                varHeadTimeArr.append(ret[2])
                printFile(
                    f'DEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(sqrt(ret[2]), 2)} step\n', f)
                stDevHeadTimeArr.append(sqrt(ret[2]))
                printFile(f'TEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {ret[3]} step\n', f)
                maxHeadTimeArr.append(ret[3])
                printFile(f'TEMPO MEDIO PASSATO IN CODA: {round(ret[4], 2)} step\n', f)
                meanTailTimeArr.append(ret[4])
                printFile(f'VARIANZA DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(ret[5], 2)} step\n', f)
                varTailTimeArr.append(ret[5])
                printFile(
                    f'DEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(sqrt(ret[5]), 2)} step\n', f)
                stDevTailTimeArr.append(sqrt(ret[5]))
                printFile(f'TEMPO MASSIMO PASSATO IN CODA: {ret[6]} step\n', f)
                maxTailTimeArr.append(ret[6])
                printFile(f'VELOCITA MEDIA DEI VEICOLI: {round(ret[7], 2)} m/s\n', f)
                meanSpeedArr.append(ret[7])
                printFile(f'VELOCITA MASSIMA DEI VEICOLI: {round(ret[8], 2)} m/s\n', f)
                maxSpeedArr.append(ret[8])
                printFile(f'LUNGHEZZA MEDIA DELLE CODE: {round(ret[9], 2)} auto\n', f)
                meanTailLengthArr.append(ret[9])
                printFile(f'LUNGHEZZA MASSIMA DELLE CODE: {round(ret[10], 2)} auto\n', f)
                maxTailLengthArr.append(ret[10])
                printFile(f'NUMERO DI VEICOLI FERMI: {ret[11]} ({round(ret[11] / numberOfVehicles * 100, 2)}%)\n', f)
                nStoppedVehiclesArr.append(ret[11])
                printFile(f'THROUGHPUT MEDIO: {round(ret[12], 2)}\n', f)
                meanThroughputArr.append(ret[12])
            printFile('----------------------------------------------------\n', f)
            printFile(f'VALORI MEDI\n', f)
            printFile('----------------------------------------------------\n', f)
            printFile(f'TEMPO TOTALE DI SIMULAZIONE: {round(sum(totalTimeArr) / len(totalTimeArr))} step\n', f)
            printFile(f'TEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(sum(meanHeadTimeArr) / len(meanHeadTimeArr), 2)} step\n', f)
            printFile(f'VARIANZA DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(sum(varHeadTimeArr) / len(varHeadTimeArr), 2)} step\n', f)
            printFile(
                f'DEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(sum(stDevHeadTimeArr) / len(stDevHeadTimeArr), 2)} step\n', f)
            printFile(f'TEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {round(sum(maxHeadTimeArr) / len(maxHeadTimeArr), 2)} step\n', f)
            printFile(f'TEMPO MEDIO PASSATO IN CODA: {round(sum(meanTailTimeArr) / len(meanTailTimeArr), 2)} step\n', f)
            printFile(f'VARIANZA DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(sum(varTailTimeArr) / len(varTailTimeArr), 2)} step\n', f)
            printFile(
                f'DEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(sum(stDevTailTimeArr) / len(stDevTailTimeArr), 2)} step\n', f)
            printFile(f'TEMPO MASSIMO PASSATO IN CODA: {round(sum(maxTailTimeArr) / len(maxTailTimeArr), 2)} step\n', f)
            printFile(f'VELOCITA MEDIA DEI VEICOLI: {round(sum(meanSpeedArr) / len(meanSpeedArr), 2)} m/s\n', f)
            printFile(f'VELOCITA MASSIMA DEI VEICOLI: {round(sum(maxSpeedArr) / len(maxSpeedArr), 2)} m/s\n', f)
            printFile(f'LUNGHEZZA MEDIA DELLE CODE: {round(sum(meanTailLengthArr) / len(meanTailLengthArr), 2)} auto\n', f)
            printFile(f'LUNGHEZZA MASSIMA DELLE CODE: {round(sum(maxTailLengthArr) / len(maxTailLengthArr), 2)} auto\n', f)
            printFile(f'NUMERO DI VEICOLI FERMI: {sum(nStoppedVehiclesArr) / len(nStoppedVehiclesArr)} ({round((sum(nStoppedVehiclesArr) / len(nStoppedVehiclesArr)) / numberOfVehicles * 100, 2)}%)\n', f)
            printFile(f'THROUGHPUT MEDIO: {round(sum(meanThroughputArr) / len(meanThroughputArr), 2)}\n', f)