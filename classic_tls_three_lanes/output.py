import numpy as np
import matplotlib.pyplot as plt
from datetime import date
from math import sqrt


def writeMeasuresToFile(f, i, numberOfVehicles, totalTime, meanHeadTime, varHeadTime, maxHeadTime, meanTailTime,
                        varTailTime, maxTailTime, meanSpeed, varSpeed, maxSpeed, meanTailLength, varTailLength,
                        maxTailLength, nStoppedVehicles, meanThroughput):
    """Salvo su un file le misure effettuate"""
    f.write('----------------------------------------------------\n')
    f.write(f'\nSIMULAZIONE NUMERO {i}\n')
    f.write('\n----------------------------------------------------\n')
    f.write(f'\nNUMERO DI VEICOLI: {numberOfVehicles}\n')
    f.write(f'\nTEMPO TOTALE DI SIMULAZIONE: {totalTime} step\n')
    f.write(f'\nTEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(meanHeadTime, 2)} step\n')
    f.write(
        f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(sqrt(varHeadTime), 2)} step\n')
    f.write(f'\nTEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {maxHeadTime} step\n')
    f.write(f'\nTEMPO MEDIO PASSATO IN CODA: {round(meanTailTime, 2)} step\n')
    f.write(
        f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(sqrt(varTailTime), 2)} step\n')
    f.write(f'\nTEMPO MASSIMO PASSATO IN CODA: {maxTailTime} step\n')
    f.write(f'\nVELOCITA MEDIA DEI VEICOLI: {round(meanSpeed, 2)} m/s\n')
    f.write(f'\nDEVIAZIONE STANDARD VELOCITA MEDIA DEI VEICOLI: {round(sqrt(varSpeed), 2)} m/s\n')
    f.write(f'\nVELOCITA MASSIMA DEI VEICOLI: {round(maxSpeed, 2)} m/s\n')
    f.write(f'\nLUNGHEZZA MEDIA DELLE CODE: {round(meanTailLength, 2)} auto\n')
    f.write(f'\nDEVIAZIONE STANDARD LUNGHEZZA DELLE CODE: {round(sqrt(varTailLength), 2)} m/s\n')
    f.write(f'\nLUNGHEZZA MASSIMA DELLE CODE: {round(maxTailLength, 2)} auto\n')
    f.write(
        f'\nNUMERO DI VEICOLI FERMI: {nStoppedVehicles} ({round(nStoppedVehicles / numberOfVehicles * 100, 2)}%)\n')
    f.write(f'\nTHROUGHPUT MEDIO: {round(meanThroughput, 2)}\n\n')


def autolabel(rects, ax):
    """Attach a text label above each bar in *rects*, displaying its height."""
    for rect in rects:
        height = rect.get_height()
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')


def histPerMeasures(values, labels, titles, colors, arr, labels_per_sims, path):
    """Salvo su immagine l'istogramma con le misure medie per ogni simulazione"""

    j = 0
    for i in range(0, len(arr)):
        sx = 0
        dx = 0
        c = arr[i]
        r = np.arange(len(values[i]))
        width = 0.01
        fig, ax = plt.subplots()
        # controllo se è pari
        if arr[i] % 2 == 0:
            c -= 2
            sx = -0.1
            dx = 0.1
            rect = ax.bar(r + sx, values[j], width, color=colors[j], label=labels[j])
            autolabel(rect, ax)
            j += 1
            rect = ax.bar(r + dx, values[j], width, color=colors[j], label=labels[j])
            autolabel(rect, ax)
            j += 1
        else:
            c -= 1
            rect = ax.bar(r, values[j], width, color=colors[j], label=labels[j])
            autolabel(rect, ax)
            j += 1
        for k in range(0, int(c / 2)):
            sx -= 0.2
            rect = ax.bar(r + sx, values[j], width, color=colors[j], label=labels[j])
            autolabel(rect, ax)
            j += 1
            dx += 0.2
            rect = ax.bar(r + dx, values[j], width, color=colors[j], label=labels[j])
            autolabel(rect, ax)
            j += 1
        plt.ylabel("Valori")
        ax.set_xticks(r)
        ax.set_xticklabels(labels_per_sims)
        ax.legend(title='Legenda', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.savefig(path + "/" + titles[i] + '_' + date.today().strftime("%d-%m-%Y") + '.png', bbox_inches='tight')
