import sys
import os
import main
from math import sqrt
from multiprocessing import Pool
import output

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Dichiarare la variabile d'ambiente 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa

config_file = "intersection.sumocfg"  # file di configurazione della simulazione
mode = 'auto'  # stringa che imposta la modalità automatica per le simulazioni
repeatSim = 10  # numero di volte per cui la stessa simulazione deve essere ripetuta
numberOfVehicles = [10, 15, 20, 25]  # lista contenente il numero di veicoli per ogni simulazione diversa
diffSim = len(numberOfVehicles)  # numero di simulazioni diverse che devono essere eseguite
period = 10  # tempo di valutazione del throughput del sistema incrocio
num_measures = 15  # numero di misure effettuate nella simulazione


def checkInput(d, def_string, ask_string, error_string):
    """Funzione che verifica se l'input dell'utente è corretto"""

    i = 0
    while i <= 0:
        t = input(def_string)
        if t == '':
            i = d  # default
            print(ask_string)
        else:
            try:
                i = int(t)
            except:
                print(error_string)
                i = 0
                continue
            if i <= 0:
                print(error_string)
    return i


if __name__ == "__main__":
    """Main che avvia un certo numero di simulazioni in parallelo (in modalità manuale o automatica)"""

    choice = ''
    schema = 'n'
    default = ['d', 'dati']
    labels_per_sims = []
    while choice not in ['d', 'D', 'g', 'G']:
        if mode == 'auto':
            choice = default[0]
        else:
            choice = input('\nVuoi raccogliere dati o avere una visualizzazione grafica? (d = dati, g = grafica): ')
        if choice not in ['d', 'D', 'g', 'G']:
            choice = default[0]
            print(f'\nUtilizzo la configurazione di default ({default[1]})')
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
    if mode != 'auto':
        diffSim = checkInput(4, f'\nInserire il numero di esecuzioni della simulazione: ',
                             f'\nUtilizzo default ({4}) numero di run diverse...',
                             '\nInserire un numero di simulazioni positivo!')
    else:
        print(f'\nEseguo {diffSim} simulazioni differenti...')
    hists_per_sims = []
    for i in range(0, num_measures):
        hists_per_sims.append([])
    for i in range(1, diffSim + 1):
        labels_per_sims.append(f'Sim. {i} ({numberOfVehicles[i - 1]} veicoli)')
        f = open(f"output_batch_{i}.txt", "w")
        if mode != 'auto':
            repeatSim = checkInput(10, f'\nInserire il numero di ripetizioni della simulazione {i}: ',
                                   f'\nUtilizzo default ({10}) numero di stesse run...',
                                   '\nInserire un numero di simulazioni positivo!')
        else:
            print(f'\nEseguo {repeatSim} simulazioni identiche in parallelo...')
        if mode != 'auto':
            numberOfVehicles[i - 1] = checkInput(50, f'\nInserire il numero di veicoli nella simulazione {i}: ',
                                                 f'\nUtilizzo default ({50}) veicoli...',
                                                 '\nInserire un numero di veicoli positivo!')
        else:
            print(f'\nUtilizzo {numberOfVehicles[i - 1]} veicoli...')
        pool = Pool(processes=repeatSim)
        pool_arr = []
        for j in range(0, repeatSim):
            pool_arr.append(pool.apply_async(main.run, (numberOfVehicles[i - 1], schema, sumoCmd)))
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
            output.writeMeasuresToFile(f, f'{i}:{j + 1}', numberOfVehicles[i - 1], ret[0], ret[1], ret[2], ret[3],
                                       ret[4], ret[5], ret[6], ret[7], ret[8], ret[9], ret[10], ret[11], ret[12])
            totalTimeArr.append(ret[0])
            meanHeadTimeArr.append(ret[1])
            varHeadTimeArr.append(ret[2])
            stDevHeadTimeArr.append(sqrt(ret[2]))
            maxHeadTimeArr.append(ret[3])
            meanTailTimeArr.append(ret[4])
            varTailTimeArr.append(ret[5])
            stDevTailTimeArr.append(sqrt(ret[5]))
            maxTailTimeArr.append(ret[6])
            meanSpeedArr.append(ret[7])
            maxSpeedArr.append(ret[8])
            meanTailLengthArr.append(ret[9])
            maxTailLengthArr.append(ret[10])
            nStoppedVehiclesArr.append(ret[11])
            meanThroughputArr.append(ret[12])
        f.close()
        hists_per_sims[0].append(round(sum(totalTimeArr) / len(totalTimeArr), 2))
        hists_per_sims[1].append(round(sum(meanHeadTimeArr) / len(meanHeadTimeArr), 2))
        hists_per_sims[2].append(round(sum(varHeadTimeArr) / len(varHeadTimeArr), 2))
        hists_per_sims[3].append(round(sum(stDevHeadTimeArr) / len(stDevHeadTimeArr), 2))
        hists_per_sims[4].append(round(sum(maxHeadTimeArr) / len(maxHeadTimeArr), 2))
        hists_per_sims[5].append(round(sum(meanTailTimeArr) / len(meanTailTimeArr), 2))
        hists_per_sims[6].append(round(sum(varTailTimeArr) / len(varTailTimeArr), 2))
        hists_per_sims[7].append(round(sum(stDevTailTimeArr) / len(stDevTailTimeArr), 2))
        hists_per_sims[8].append(round(sum(maxTailTimeArr) / len(maxTailTimeArr), 2))
        hists_per_sims[9].append(round(sum(meanSpeedArr) / len(meanSpeedArr), 2))
        hists_per_sims[10].append(round(sum(maxSpeedArr) / len(maxSpeedArr), 2))
        hists_per_sims[11].append(round(sum(meanTailLengthArr) / len(meanTailLengthArr), 2))
        hists_per_sims[12].append(round(sum(maxTailTimeArr) / len(maxTailTimeArr), 2))
        hists_per_sims[13].append(round(sum(nStoppedVehiclesArr) / len(nStoppedVehiclesArr), 2))
        hists_per_sims[14].append(round(sum(meanThroughputArr) / len(meanThroughputArr), 2))
        # f.write('\n----------------------------------------------------\n')
        # f.write(f'\nVALORI MEDI\n')
        # f.write('\n----------------------------------------------------\n')
        # f.write(f'\nTEMPO TOTALE DI SIMULAZIONE: {round(sum(totalTimeArr) / len(totalTimeArr))} step\n')
        # f.write(
        #     f'\nTEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(sum(meanHeadTimeArr) / len(meanHeadTimeArr), 2)} step\n')
        # f.write(
        #     f'\nVARIANZA DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(sum(varHeadTimeArr) / len(varHeadTimeArr), 2)} step\n')
        # f.write(
        #     f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(sum(stDevHeadTimeArr) / len(stDevHeadTimeArr), 2)} step\n')
        # f.write(
        #     f'\nTEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {round(sum(maxHeadTimeArr) / len(maxHeadTimeArr), 2)} step\n')
        # f.write(f'\nTEMPO MEDIO PASSATO IN CODA: {round(sum(meanTailTimeArr) / len(meanTailTimeArr), 2)} step\n')
        # f.write(
        #     f'\nVARIANZA DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(sum(varTailTimeArr) / len(varTailTimeArr), 2)} step\n')
        # f.write(
        #     f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(sum(stDevTailTimeArr) / len(stDevTailTimeArr), 2)} step\n')
        # f.write(f'\nTEMPO MASSIMO PASSATO IN CODA: {round(sum(maxTailTimeArr) / len(maxTailTimeArr), 2)} step\n')
        # f.write(f'\nVELOCITA MEDIA DEI VEICOLI: {round(sum(meanSpeedArr) / len(meanSpeedArr), 2)} m/s\n')
        # f.write(f'\nVELOCITA MASSIMA DEI VEICOLI: {round(sum(maxSpeedArr) / len(maxSpeedArr), 2)} m/s\n')
        # f.write(f'\nLUNGHEZZA MEDIA DELLE CODE: {round(sum(meanTailLengthArr) / len(meanTailLengthArr), 2)} auto\n')
        # f.write(f'\nLUNGHEZZA MASSIMA DELLE CODE: {round(sum(maxTailLengthArr) / len(maxTailLengthArr), 2)} auto\n')
        # f.write(
        #     f'\nNUMERO DI VEICOLI FERMI: {sum(nStoppedVehiclesArr) / len(nStoppedVehiclesArr)} ({round((sum(nStoppedVehiclesArr) / len(nStoppedVehiclesArr)) / numberOfVehicles[i - 1] * 100, 2)}%)\n')
        # f.write(f'\nTHROUGHPUT MEDIO: {round(sum(meanThroughputArr) / len(meanThroughputArr), 2)}\n\n')
        # f.close()

    output.histPerMeasures(hists_per_sims, labels_per_sims, period)