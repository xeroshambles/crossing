import numpy as np
import matplotlib.pyplot as plt
from datetime import date


def getValue(title, measure_arr):
    """Ritorna il massimo o la media della lista di valori a seconda del titolo"""

    if title[:3] == 'max':
        return max(measure_arr)
    else:
        return round(sum(measure_arr) / len(measure_arr), 2)


def clearMeasures(measures, groups, head_titles):
    """Pulisco il dizionario delle misure"""

    for i in range(0, len(groups)):
        count = 0
        while count < groups[i]:
            measures[head_titles[i]][count]['values'].clear()
            count += 1


def writeMeasuresToFile(f, i, numberOfVehicles, ret):
    """Salvo su file le misure effettuate"""

    f.write('----------------------------------------------------\n')
    f.write(f'\nSIMULAZIONE NUMERO {i}\n')
    f.write('\n----------------------------------------------------\n')
    f.write(f'\nNUMERO DI VEICOLI: {numberOfVehicles}\n')

    f.write(f'\nTEMPO TOTALE DI SIMULAZIONE: {ret[0]} step\n')
    f.write(f'\nTEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(ret[1], 2)} step\n')
    f.write(
        f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(ret[2], 2)} step\n')
    f.write(f'\nTEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {round(ret[3], 2)} step\n')
    f.write(f'\nTEMPO MEDIO PASSATO IN CODA: {round(ret[4], 2)} step\n')
    f.write(
        f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(ret[5], 2)} step\n')
    f.write(f'\nTEMPO MASSIMO PASSATO IN CODA: {round(ret[6], 2)} step\n')
    f.write(f'\nVELOCITA MEDIA DEI VEICOLI: {round(ret[7], 2)} m/s\n')
    f.write(f'\nDEVIAZIONE STANDARD VELOCITA MEDIA DEI VEICOLI: {round(ret[8], 2)} m/s\n')
    f.write(f'\nLUNGHEZZA MEDIA DELLE CODE: {round(ret[9], 2)} auto\n')
    f.write(f'\nDEVIAZIONE STANDARD LUNGHEZZA DELLE CODE: {round(ret[10], 2)} m/s\n')
    f.write(f'\nLUNGHEZZA MASSIMA DELLE CODE: {round(ret[11], 2)} auto\n')
    f.write(
        f'\nNUMERO DI VEICOLI FERMI: {ret[12]} ({round(ret[12] / numberOfVehicles * 100, 2)}%)\n')
    f.write(f'\nTHROUGHPUT MEDIO: {round(ret[13], 2)}\n\n')


def collectMeasures(queue, repeat, numOfVehicles, line_measures, config_measures, groups, titles, head_titles,
                    labels, nums, project, f, i):
    """Scrivo le misure delle simulazioni ripetute"""

    arr = {k: [] for k in titles}

    arr2 = {str(i): str(nums[i]) for i in range(0, len(nums))}

    for j in range(0, repeat):

        ret = queue.get()

        for k in range(0, len(arr)):
            arr[titles[k]].append(ret[k])

            for p in range(0, len(config_measures[arr2[str(i)]][labels[k]])):
                if config_measures[arr2[str(i)]][labels[k]][p]['project'] == project:
                    config_measures[arr2[str(i)]][labels[k]][p]['values'].append(ret[k])

        writeMeasuresToFile(f, f'{i}:{j}', numOfVehicles, ret)

    k = 0

    for i in range(0, len(groups)):
        count = 0
        while count < groups[i]:
            title = line_measures[head_titles[i]][count]['title']
            line_measures[head_titles[i]][count]['values'].append(getValue(title, arr[title]))
            count += 1
            k += 1


def checkChoice(choices, inp, default, err, mode='', arr=False):
    "Funzione che verifica se le impostazioni del progetto sono corrette"

    choice = ''

    while choice not in choices:
        if mode == 'auto':
            if arr:
                choice = choices
            else:
                choice = choices[0]
                print(default)
            break
        else:
            choice = input(inp)
            if choice == '':
                if arr:
                    choice = [choices[0]]
                else:
                    choice = choices[0]
                print(default)
                break
            if choice not in choices:
                print(err)

    return choice


def checkInput(val, min_inp, default, err, mode='', ret='', value=0, max_inp=10000):
    """Funzione che verifica se l'input dell'utente è corretto"""

    if mode == 'auto':
        print(ret)
        return value

    i = 0

    while i <= 0:
        t = input(min_inp)
        if t == '':
            i = val
            print(default)
            break
        try:
            i = int(t)
        except:
            i = 0
            print(err)
            continue
        if i <= 0 or i >= max_inp:
            print(err)

    return i


def autolabel(values, r, offset, ax):
    """Funzione per mettere il numero sopra la barra dell'istogramma"""

    i = 0

    for value in values:
        ax.annotate(f'{value}', xy=(r[i] + offset, value), xytext=(0, 3), textcoords="offset points", ha='center',
                    va='bottom')
        i += 1


def linesPerMeasures(line_measures, groups, dir, project=''):
    """Salvo su immagini gli istogrammi con le misure medie per ogni simulazione"""

    sims = []
    values = []
    labels = []
    titles = []
    colors = []

    for k in line_measures:
        if k == 'sims':
            sims = line_measures['sims']
            continue
        titles.append(k)
        for i in range(0, len(line_measures[k])):
            values.append(line_measures[k][i]['values'])
            labels.append(line_measures[k][i]['label'])
            colors.append(line_measures[k][i]['color'])

    j = 0

    for i in range(0, len(groups)):
        r = np.arange(len(values[i]))
        count = groups[i]
        fig, ax = plt.subplots()
        while count > 0:
            ax.plot(r, values[j], color=colors[j], label=labels[j], lw=2, marker='s')
            autolabel(values[j], r, 0, ax)
            j += 1
            count -= 1
        plt.ylabel("Valori")
        ax.set_xticks(r)
        ax.set_title(project)
        ax.set_xticklabels(sims)
        ax.legend(title='Legenda', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.savefig(dir + "/" + titles[i] + '_' + date.today().strftime("%d-%m-%Y") + '.png', bbox_inches='tight')
        plt.close(fig)


def linesPerConfig(config_measures, labels, titles, colors, projects, numOfVehicles, dir):
    """Salvo su immagini gli istogrammi con le misure medie per ogni simulazione"""

    values = []
    vehs = [str(i) for i in numOfVehicles]

    i = 0

    for lab in labels:
        for k in config_measures:
            for z in range(0, len(projects)):
                values.append([])
                if len(config_measures[k][lab][z]['values']) > 0:
                    values[z].append(getValue(titles[i], config_measures[k][lab][z]['values']))
        r = np.arange(len(vehs))
        fig, ax = plt.subplots()
        for j in range(0, len(projects)):
            ax.plot(r, values[j], color=colors[j], label=projects[j], lw=2, marker='s')
            autolabel(values[j], r, 0, ax)
        plt.ylabel("Valori")
        ax.set_xticks(r)
        ax.set_title(lab)
        ax.set_xticklabels(vehs)
        ax.legend(title='Legenda', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.savefig(dir + "/" + titles[i] + "_" + date.today().strftime("%d-%m-%Y") + '.png',
                    bbox_inches='tight')
        plt.close(fig)

        i += 1

        values = []
