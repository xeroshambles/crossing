import sys
import os
import main
from math import sqrt
from multiprocessing import Pool
import matplotlib.pyplot as plt
import numpy as np

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Dichiarare la variabile d'ambiente 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa

config_file = "intersection.sumocfg"
mode = 'auto'
repeatSim = 10
numberOfVehicles = [50, 100, 200, 500]
diffSim = len(numberOfVehicles)
num_measures = 15


def checkInput(d, def_string, ask_string, error_string):
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
    return i


def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')


if __name__ == "__main__":
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
            f.write('----------------------------------------------------\n')
            f.write(f'\nSIMULAZIONE NUMERO {i}:{j + 1}\n')
            f.write('\n----------------------------------------------------\n')
            f.write(f'\nNUMERO DI VEICOLI: {numberOfVehicles[i - 1]}\n')
            f.write(f'\nTEMPO TOTALE DI SIMULAZIONE: {ret[0]} step\n')
            totalTimeArr.append(ret[0])
            f.write(f'\nTEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(ret[1], 2)} step\n')
            meanHeadTimeArr.append(ret[1])
            f.write(f'\nVARIANZA DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(ret[2], 2)} step\n')
            varHeadTimeArr.append(ret[2])
            f.write(
                f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(sqrt(ret[2]), 2)} step\n')
            stDevHeadTimeArr.append(sqrt(ret[2]))
            f.write(f'\nTEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {ret[3]} step\n')
            maxHeadTimeArr.append(ret[3])
            f.write(f'\nTEMPO MEDIO PASSATO IN CODA: {round(ret[4], 2)} step\n')
            meanTailTimeArr.append(ret[4])
            f.write(f'\nVARIANZA DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(ret[5], 2)} step\n')
            varTailTimeArr.append(ret[5])
            f.write(
                f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(sqrt(ret[5]), 2)} step\n')
            stDevTailTimeArr.append(sqrt(ret[5]))
            f.write(f'\nTEMPO MASSIMO PASSATO IN CODA: {ret[6]} step\n')
            maxTailTimeArr.append(ret[6])
            f.write(f'\nVELOCITA MEDIA DEI VEICOLI: {round(ret[7], 2)} m/s\n')
            meanSpeedArr.append(ret[7])
            f.write(f'\nVELOCITA MASSIMA DEI VEICOLI: {round(ret[8], 2)} m/s\n')
            maxSpeedArr.append(ret[8])
            f.write(f'\nLUNGHEZZA MEDIA DELLE CODE: {round(ret[9], 2)} auto\n')
            meanTailLengthArr.append(ret[9])
            f.write(f'\nLUNGHEZZA MASSIMA DELLE CODE: {round(ret[10], 2)} auto\n')
            maxTailLengthArr.append(ret[10])
            f.write(f'\nNUMERO DI VEICOLI FERMI: {ret[11]} ({round(ret[11] / numberOfVehicles[i - 1] * 100, 2)}%)\n')
            nStoppedVehiclesArr.append(ret[11])
            f.write(f'\nTHROUGHPUT MEDIO: {round(ret[12], 2)}\n\n')
            meanThroughputArr.append(ret[12])
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
        f.close()

    """Mostro a schermo l'istogramma con le misure medie per ogni simulazione"""
    r = np.arange(len(hists_per_sims[0]))
    width = 0.01
    fig, ax = plt.subplots()
    rect1 = ax.bar(r - 7 * width, hists_per_sims[0], width, color='#FF5733', label='Tempo totale (s)')
    rect2 = ax.bar(r - 6 * width, hists_per_sims[1], width, color='#FFF933', label='Tempo medio in testa (s)')
    rect3 = ax.bar(r - 5 * width, hists_per_sims[2], width, color='#9FFF33', label='Varianza tempo in testa (s)')
    rect4 = ax.bar(r - 4 * width, hists_per_sims[3], width, color='#33FF3C', label='Deviazione standard tempo in '
                                                                                   'testa (s)')
    rect5 = ax.bar(r - 3 * width, hists_per_sims[4], width, color='#33FFC7', label='Tempo massimo in testa (s)')
    rect6 = ax.bar(r - 2 * width, hists_per_sims[5], width, color='#33A5FF', label='Tempo medio in coda (s)')
    rect7 = ax.bar(r - width, hists_per_sims[6], width, color='#3340FF', label='Varianza tempo in coda (s)')
    rect8 = ax.bar(r, hists_per_sims[7], width, color='#9B33FF', label='Deviazione standard tempo in coda (s)')
    rect9 = ax.bar(r + width, hists_per_sims[8], width, color='#E633FF', label='Tempo massimo in coda (s)')
    rect10 = ax.bar(r + 2 * width, hists_per_sims[9], width, color='#FF33B3', label='Velocità media (m/s)')
    rect11 = ax.bar(r + 3 * width, hists_per_sims[10], width, color='#FF334D', label='Velocità massima (m/s)')
    rect12 = ax.bar(r + 4 * width, hists_per_sims[11], width, color='#486246', label='Lunghezza media delle code')
    rect13 = ax.bar(r + 5 * width, hists_per_sims[12], width, color='#1E6153', label='Lunghezza massima delle code')
    rect14 = ax.bar(r + 6 * width, hists_per_sims[13], width, color='#D0D1E6', label='Numero di veicoli fermi')
    rect15 = ax.bar(r + 7 * width, hists_per_sims[14], width, color='#3F170D', label='Throughput medio (veicoli/s)')
    ax.set_title('Valori medi delle simulazioni effettuate')
    ax.set_xticks(r)
    ax.set_xticklabels(labels_per_sims)
    lgd = ax.legend(title='Legenda', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.savefig('results.png', bbox_inches='tight')
