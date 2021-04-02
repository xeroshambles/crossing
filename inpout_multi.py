import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from datetime import date
from config_multi import *


def redirectOutput(path, index, mode):
    """Funzione che redireziona l'output della simulazione"""

    if outputRedirection:

        origin_stdout = sys.stdout

        origin_stderr = sys.stderr

        if mode:

            dir = os.path.join(path, 'terminals')

            if not os.path.exists(dir):
                try:
                    os.mkdir(dir)
                except OSError:
                    print(f"\nCreazione della cartella {dir} fallita...")
                    sys.exit(-1)

            sys.stdout = open(os.path.join(dir, f"{index}.txt"), "w")

            sys.stderr = open(os.path.join(dir, f"{index}.txt"), "w")

        else:

            sys.stdout = origin_stdout

            sys.stderr = origin_stderr


def getValue(title, arr_measure):
    """Ritorna il massimo o la media della lista di valori a seconda del titolo"""

    if title[:3] == 'max' and title[-3:] != 'all':
        return max(arr_measure)
    elif title[-3:] == 'all':
        return arr_measure[0]
    else:
        return round(sum(arr_measure) / len(arr_measure), 2)


def clearMeasures(measures, groups, head_titles):
    """Pulisco il dizionario delle misure"""

    for i in range(0, len(groups)):
        count = 0
        while count < groups[i]:
            measures[head_titles[i]][count]['values'].clear()
            count += 1


def writeMeasuresToFile(f, i, ret):
    """Salvo su file le misure effettuate"""

    f.write('----------------------------------------------------\n')
    f.write(f'\nSIMULAZIONE NUMERO {i}\n')
    f.write('\n----------------------------------------------------\n')
    f.write(f'\nTEMPO DI PERCORRENZA MEDIO: {round(ret[0], 2)}\n')
    f.write(f'\nDEVIAZIONE STANDARD DEL TEMPO DI PERCORRENZA: {round(ret[1], 2)}\n')
    f.write(f'\nMASSIMO TEMPO DI PERCORRENZA: {round(ret[2], 2)}\n')
    f.write(f'\nTEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(ret[3], 2)} step\n')
    f.write(
        f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(ret[4], 2)} step\n')
    f.write(f'\nTEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {round(ret[5], 2)} step\n')
    f.write(f'\nTEMPO MEDIO PASSATO IN CODA: {round(ret[6], 2)} step\n')
    f.write(
        f'\nDEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(ret[7], 2)} step\n')
    f.write(f'\nTEMPO MASSIMO PASSATO IN CODA: {round(ret[8], 2)} step\n')
    f.write(f'\nVELOCITA MEDIA DEI VEICOLI: {round(ret[9], 2)} m/s\n')
    f.write(f'\nDEVIAZIONE STANDARD VELOCITA MEDIA DEI VEICOLI: {round(ret[10], 2)} m/s\n')
    f.write(f'\nLUNGHEZZA MEDIA DELLE CODE: {round(ret[11], 2)} auto\n')
    f.write(f'\nDEVIAZIONE STANDARD LUNGHEZZA DELLE CODE: {round(ret[12], 2)} auto\n')
    f.write(f'\nLUNGHEZZA MASSIMA DELLE CODE: {round(ret[13], 2)} auto\n')
    f.write(f'\nTHROUGHPUT MEDIO: {round(ret[14], 2)}\n')
    f.write(f'\nNUMERO DI VEICOLI DEVIATI: {round(ret[15], 2)}\n')
    f.write(f'\nLUNGHEZZA MEDIA DELLE CODE (PIU INCROCI): {ret[16]} auto\n')
    f.write(f'\nDEVIAZIONE STANDARD LUNGHEZZA DELLE CODE (PIU INCROCI): {ret[17]} auto\n')
    f.write(f'\nLUNGHEZZA MASSIMA DELLE CODE (PIU INCROCI): {ret[18]} auto\n')
    f.write(f'\nTHROUGHPUT MEDI (PIU INCROCI): {ret[19]}\n\n')


def collectMeasures(queue, repeat, group_measures, single_measures, groups, titles, head_titles,
                    labels, nums, divPercs, project, f, i):
    """Scrivo le misure delle simulazioni ripetute"""

    arr_titles = {k: [] for k in titles}

    arr_nums = {str(i): str(nums[i]) for i in range(0, len(nums))}

    for j in range(0, repeat):

        ret = queue.get()

        # if ret[15] / sum(nums[i]) > divPercs[i]:
        #     continue

        for k in range(0, len(arr_titles)):

            arr_titles[titles[k]].append(ret[k])

            if k <= len(arr_titles) - 5:

                for p in range(0, len(single_measures[arr_nums[str(i)]][labels[k]])):
                    if single_measures[arr_nums[str(i)]][labels[k]][p]['project'] == project:
                        single_measures[arr_nums[str(i)]][labels[k]][p]['values'].append(ret[k])

        writeMeasuresToFile(f, f'{i}:{j}', ret)

    k = 0

    for i in range(0, len(groups)):
        count = 0
        while count < groups[i]:
            title = group_measures[head_titles[i]][count]['title']
            group_measures[head_titles[i]][count]['values'].append(getValue(title, arr_titles[title]))
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


def checkInput(val, inp, default, err, mode='', auto_ret='', auto_value=0, min_inp=0, max_inp=10000):
    """Funzione che verifica se l'input dell'utente è corretto"""

    if mode == 'auto':
        print(auto_ret)
        return auto_value

    i = 0

    while i <= 0:
        t = input(inp)
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
        if i <= min_inp or i >= max_inp:
            print(err)

    return i


def autoLabel(values, r, offset, ax):
    """Funzione per mettere il numero sopra la barra dell'istogramma"""

    i = 0

    for value in values:
        ax.annotate(f'{value}', xy=(r[i] + offset, value), xytext=(0, 3), textcoords="offset points", ha='center',
                    va='bottom')
        i += 1


def linesPerGroups(sims, values, labels, titles, colors, groups, stepsSpawn, dir, project_label):
    """Salvo su immagini le misure di un progetto per ogni scenario di traffico"""

    j = 0

    for i in range(0, len(groups)):
        r = np.arange(len(values[j]))
        count = groups[i]
        fig, ax = plt.subplots()
        while count > 0:
            if i > len(groups) - 3:
                width = 0.1
                offset = width / 2
                if count % 2 == 0:
                    ax.bar(r + offset, values[j], width, color=colors[j], label=labels[j])
                    j += 1
                    count -= 1
                    ax.bar(r - offset, values[j], width, color=colors[j], label=labels[j])
                else:
                    offset = 0
                    ax.bar(r + offset, values[j], width, color=colors[j], label=labels[j])
                    offset -= width
            else:
                ax.plot(r, values[j], color=colors[j], label=labels[j], lw=2, marker='s')
            # autolabel(values[j], r, 0, ax)
            j += 1
            count -= 1
        ax.set_xticks(r)
        ax.set_title(project_label)
        if i > len(groups) - 3:
            ax.set_xticklabels([f'I{incr}' for incr in range(1, 26)])
        else:
            ax.set_xticklabels([f'{round(sum(eval(sim)) / stepsSpawn)} veicoli / s' for sim in sims])
        ax.legend(title='Legenda', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.savefig(dir + "/" + titles[i] + '_' + date.today().strftime("%d-%m-%Y") + '.png', bbox_inches='tight')
        plt.close(fig)


def linesPerMeasure(single_measures, labels, titles, colors, projects, projects_labels, numberOfVehicles, stepsSpawn,
                    dir):
    """Salvo su immagini le misure di tutti i progetti per ogni scenario di traffico"""

    values = []
    vehs = [str(i) for i in numberOfVehicles]

    i = 0

    for lab in labels:
        if "tutti" in lab:
            break
        for k in single_measures:
            for z in range(0, len(projects)):
                values.append([])
                if len(single_measures[k][lab][z]['values']) > 0:
                    values[z].append(getValue(titles[i], single_measures[k][lab][z]['values']))
        r = np.arange(len(vehs))
        fig, ax = plt.subplots()
        for j in range(0, len(projects)):
            ax.plot(r, values[j], color=colors[j], label=projects_labels[j], lw=2, marker='s')
            # autoLabel(values[j], r, 0, ax)
        ax.set_xticks(r)
        ax.set_title(lab)
        ax.set_xticklabels([f'{round(sum(eval(veh)) / stepsSpawn)} veicoli / s' for veh in vehs])
        ax.legend(title='Legenda', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.savefig(dir + "/" + titles[i] + "_" + date.today().strftime("%d-%m-%Y") + '.png',
                    bbox_inches='tight')
        plt.close(fig)

        i += 1

        values = []
