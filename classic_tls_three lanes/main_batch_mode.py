import sys
import os
import main
from math import sqrt
from multiprocessing import Pool

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
    numberOfSimulations = 0
    while numberOfSimulations <= 0:
        numberOfSimulations = int(input('\nInserire il numero di simulazioni: '))
        if numberOfSimulations <= 0:
            print('\nInserire un numero di simulazioni positivo!')
    numberOfVehicles = 0
    while numberOfVehicles <= 0:
        numberOfVehicles = int(input(f'\nInserire il numero di veicoli nelle simulazioni: '))
        if numberOfVehicles <= 0:
            print('\nInserire un numero di veicoli positivo!')
    pool = Pool(processes=numberOfSimulations)
    pool_arr = []
    port = 50000
    with open("output_batch.txt", "w") as f:
        for i in range(1, numberOfSimulations + 1):
            traci.init(port, host='localhost')
            pool_arr.append(pool.apply_async(main.run, (numberOfVehicles, schema)))
            traci.close()
            port += 1
        for i in range(1, numberOfSimulations + 1):
            ret = pool_arr[i].get()
            printFile('----------------------------------------------------\n', f)
            printFile(f'SIMULAZIONE NUMERO {i}\n', f)
            printFile('----------------------------------------------------\n', f)
            printFile(f'NUMERO DI VEICOLI: {numberOfVehicles}\n', f)
            printFile(f'TEMPO TOTALE DI SIMULAZIONE: {ret[0]} step\n', f)
            printFile(f'TEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(ret[1], 2)} step\n', f)
            printFile(f'VARIANZA DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(ret[2], 2)} step\n', f)
            printFile(
                f'DEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(sqrt(ret[3]), 2)} step\n', f)
            printFile(f'TEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {ret[4]} step\n', f)
            printFile(f'TEMPO MEDIO PASSATO IN CODA: {round(ret[5], 2)} step\n', f)
            printFile(f'VARIANZA DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(ret[6], 2)} step\n', f)
            printFile(
                f'DEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(sqrt(ret[7]), 2)} step\n', f)
            printFile(f'TEMPO MASSIMO PASSATO IN CODA: {ret[8]} step\n', f)
            printFile(f'VELOCITA MEDIA DEI VEICOLI: {round(ret[9], 2)} m/s\n', f)
            printFile(f'VELOCITA MASSIMA DEI VEICOLI: {round(ret[10], 2)} m/s\n', f)
            printFile(f'LUNGHEZZA MEDIA DELLE CODE: {round(ret[11], 2)} auto\n', f)
            printFile(f'LUNGHEZZA MASSIMA DELLE CODE: {round(ret[12], 2)} auto\n', f)
            printFile(f'NUMERO DI VEICOLI FERMI: {ret[13]} ({round(ret[13] / numberOfVehicles * 100, 2)}%)\n', f)
            printFile(f'THROUGHPUT MEDIO: {round(ret[14], 2)}\n', f)
