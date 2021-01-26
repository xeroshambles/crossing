import numpy as np
import matplotlib.pyplot as plt
from datetime import date
from math import sqrt


def writeMeasuresToFile(f, i, numberOfVehicles, totalTime, meanHeadTime, varHeadTime, maxHeadTime, meanTailTime,
                        varTailTime, maxTailTime, meanSpeed, maxSpeed, meanTailLength, maxTailLength, nStoppedVehicles,
                        meanThroughput):
    f.write('----------------------------------------------------\n')
    f.write(f'\nSIMULAZIONE NUMERO {i}\n')
    f.write('\n----------------------------------------------------\n')
    f.write(f'\nNUMERO DI VEICOLI: {numberOfVehicles}\n')
    f.write(f'\nTEMPO TOTALE DI SIMULAZIONE: {totalTime} step\n')
    f.write(f'\nTEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(meanHeadTime, 2)} step\n')
    f.write(f'\nVARIANZA DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(varHeadTime, 2)} step\n')
    f.write(
        f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(sqrt(varHeadTime), 2)} step\n')
    f.write(f'\nTEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {maxHeadTime} step\n')
    f.write(f'\nTEMPO MEDIO PASSATO IN CODA: {round(meanTailTime, 2)} step\n')
    f.write(f'\nVARIANZA DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(varTailTime, 2)} step\n')
    f.write(
        f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(sqrt(varTailTime), 2)} step\n')
    f.write(f'\nTEMPO MASSIMO PASSATO IN CODA: {maxTailTime} step\n')
    f.write(f'\nVELOCITA MEDIA DEI VEICOLI: {round(meanSpeed, 2)} m/s\n')
    f.write(f'\nVELOCITA MASSIMA DEI VEICOLI: {round(maxSpeed, 2)} m/s\n')
    f.write(f'\nLUNGHEZZA MEDIA DELLE CODE: {round(meanTailLength, 2)} auto\n')
    f.write(f'\nLUNGHEZZA MASSIMA DELLE CODE: {round(maxTailLength, 2)} auto\n')
    f.write(
        f'\nNUMERO DI VEICOLI FERMI: {nStoppedVehicles} ({round(nStoppedVehicles / numberOfVehicles * 100, 2)}%)\n')
    f.write(f'\nTHROUGHPUT MEDIO: {round(meanThroughput, 2)}\n\n')


def histPerMeasures(hists_per_sims, labels_per_sims, period):
    """Mostro a schermo l'istogramma con le misure medie per ogni simulazione"""

    colors = ['#FF5733', '#FFF933', '#9FFF33', '#33FF3C', '#33FFC7', '#33A5FF', '#3340FF', '#9B33FF', '#E633FF',
              '#FF33B3', '#FF334D', '#486246', '#1E6153', '#D0D1E6', '#FF5733']
    labels = ['Tempo totale (s)', 'Tempo medio in testa (s)', 'Varianza tempo in testa (s)',
              'Deviazione standard tempo in ''testa (s)', 'Tempo massimo in testa (s)', 'Tempo medio in coda (s)',
              'Varianza tempo in coda (s)', 'Deviazione standard tempo in coda (s)', 'Tempo massimo in coda (s)',
              'Velocità media (m/s)', 'Velocità massima (m/s)', 'Lunghezza media delle code',
              'Lunghezza massima delle code', 'Numero di veicoli fermi', f'Throughput (% veicoli / {period} step']

    titles = ['total_time', 'mean_head_time', 'var_head_time',
              'st_dev_head_time', 'max_head_time', 'mean_tail_time',
              'var_tail_time', 'st_dev_tail_time', 'max_tail_time',
              'mean_speed', 'max_speed', 'mean_tail_length',
              'max_tail_length', 'num_stopped_vehicles', 'throughput']

    for i in range(0, len(hists_per_sims)):
        r = np.arange(len(hists_per_sims[i]))
        width = 0.01
        fig, ax = plt.subplots()
        rect = ax.bar(r, hists_per_sims[i], width, color=colors[i], label=labels[i])
        plt.ylabel("Valori")
        ax.set_xticks(r)
        ax.set_xticklabels(labels_per_sims)
        lgd = ax.legend(title='Legenda', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.savefig(titles[i] + '_' + date.today().strftime("%d-%m-%Y") + '.png', bbox_inches='tight')
