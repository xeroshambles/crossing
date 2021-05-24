import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from datetime import date
from config import output_redirection
from config_adaptive import training_comps, spawn_configs


def redirect_output(path, index, mode):
    """Funzione che redireziona l'output della simulazione"""

    if output_redirection:

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

    if title[:3] == 'max':
        return max(arr_measure)
    else:
        return round(sum(arr_measure) / len(arr_measure), 2)

def getValueFromList(title, arr_measure, steps):
    """Ritorna il massimo o la media della lista di valori a seconda del titolo"""
    ret = [0 for s in range(0, steps)]
    for s in range(0, steps):
        current_vals = [el[s] for el in arr_measure]
        if title[:3] == 'max':
            ret[s] = max(current_vals)
        else:
            ret[s] = round(sum(current_vals) / len(current_vals), 2)
    return ret

def clearMeasures(measures, groups, head_titles):
    """Pulisco il dizionario delle misure"""

    for i in range(0, len(groups)):
        count = 0
        while count < groups[i]:
            measures[head_titles[i]][count]['values'].clear()
            count += 1

def writeMeasuresToFileAdaptive(f, i, numberOfVehicles, ret, steps):
    """Salvo su file le misure effettuate"""

    f.write('----------------------------------------------------\n')
    f.write(f'\nSIMULAZIONE NUMERO {i}\n')
    f.write(f'\nNUMERO DI VEICOLI: {numberOfVehicles}\n')
    f.write(f'\nTEMPO TOTALE DI SIMULAZIONE: {ret[0]} step\n')
    for s in range(0, steps):
        f.write(f'\nMACRO STEP {s}\n')

        f.write(f'\n    TEMPO MEDIO PASSATO IN TESTA A UNA CORSIA: {round(ret[1][s], 2)} step\n')
        f.write(
            f'\n    DEVIAZIONE STANDARD DEL TEMPO PASSATO IN TESTA A UNA CORSIA: {round(ret[2][s], 2)} step\n')
        f.write(f'\n    TEMPO MASSIMO PASSATO IN TESTA A UNA CORSIA: {round(ret[3][s], 2)} step\n')
        f.write(f'\n    TEMPO MEDIO PASSATO IN CODA: {round(ret[4][s], 2)} step\n')
        f.write(
            f'\n    DEVIAZIONE STANDARD DEL TEMPO PASSATO IN CODA A UNA CORSIA: {round(ret[5][s], 2)} step\n')
        f.write(f'\n    TEMPO MASSIMO PASSATO IN CODA: {round(ret[6][s], 2)} step\n')
        f.write(f'\n    VELOCITA MEDIA DEI VEICOLI: {round(ret[7][s], 2)} m/s\n')
        f.write(f'\n    DEVIAZIONE STANDARD VELOCITA MEDIA DEI VEICOLI: {round(ret[8][s], 2)} m/s\n')
        f.write(f'\n    LUNGHEZZA MEDIA DELLE CODE: {round(ret[9][s], 2)} auto\n')
        f.write(f'\n    DEVIAZIONE STANDARD LUNGHEZZA DELLE CODE: {round(ret[10][s], 2)} m/s\n')
        f.write(f'\n    LUNGHEZZA MASSIMA DELLE CODE: {round(ret[11][s], 2)} auto\n')
        f.write(
            f'\n    NUMERO DI VEICOLI FERMI: {ret[12][s]} ({round(ret[12][s] / numberOfVehicles * 100, 2)}%)\n')
        f.write(f'\n    THROUGHPUT MEDIO: {round(ret[13][s], 2)}\n\n')

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


def collectMeasures(queue, repeat, numOfVehicles, group_measures, single_measures, groups, titles, head_titles,
                    labels, nums, project, f, i, intermediate_group_measures=None, adaptive=False):
    """Scrivo le misure delle simulazioni ripetute"""

    arr_titles = {k: [] for k in titles}

    arr_nums = {str(i): str(nums[i]) for i in range(0, len(nums))}
    for j in range(0, repeat):

        ret = queue.get()

        if adaptive:
            for m in range(0, len(training_comps)):
                print(f"valori intermedi sim {i}:{j} : {ret[m]}\n")
                intermediate_group_measures[arr_nums[str(i)]][m][project].append(ret[m])

        for k in range(0, len(arr_titles)):
            arr_titles[titles[k]].append(ret[k])

            for p in range(0, len(single_measures[arr_nums[str(i)]][labels[k]])):
                considered_project = single_measures[arr_nums[str(i)]][labels[k]][p]['project']
                if considered_project == project:
                    if len(single_measures[arr_nums[str(i)]][labels[k]][p]['values']) == repeat:
                        single_measures[arr_nums[str(i)]][labels[k]][p]['values'][0] = ret[k]
                    else:
                        single_measures[arr_nums[str(i)]][labels[k]][p]['values'].append(ret[k])
        if adaptive:
            writeMeasuresToFileAdaptive(f, f'{i}:{j}', numOfVehicles, ret, len(nums[i]))
        else:
            writeMeasuresToFile(f, f'{i}:{j}', numOfVehicles, ret)

    k = 0

    for g in range(0, len(groups)):
        count = 0
        while count < groups[g]:
            title = group_measures[head_titles[g]][count]['title']
            if isinstance(arr_titles[title][0], list):
                group_measures[head_titles[g]][count]['values'].append(getValueFromList(title, arr_titles[title], len(nums[i])))
            else:
                group_measures[head_titles[g]][count]['values'].append(getValue(title, arr_titles[title]))
            count += 1
            k += 1
    if adaptive:
        return intermediate_group_measures



def collectMeasuresAdaptive(queue, repeat, numOfVehicles, group_measures, single_measures, groups, titles, head_titles,
                    labels, nums, project, f, i, spawn_config, intermediate_group_measures=None, adaptive=False):
    """Scrivo le misure delle simulazioni ripetute per la fimulazione adattiva"""

    arr_titles = {k: [] for k in titles}

    arr_nums = {str(i): str(nums[i]) for i in range(0, len(nums))}
    for j in range(0, repeat):

        ret = queue.get()

        if adaptive:
            for m in range(0, len(training_comps)):
                print(f"valori intermedi sim {i}:{j} : {ret[m]}\n")
                intermediate_group_measures[arr_nums[str(i)]][spawn_config][m][project].append(ret[m])

        for k in range(0, len(arr_titles)):
            arr_titles[titles[k]].append(ret[k])
            for p in range(0, len(single_measures[arr_nums[str(i)]][spawn_config][labels[k]])):
                considered_project = single_measures[arr_nums[str(i)]][spawn_config][labels[k]][p]['project']
                if considered_project == project:
                    if len(single_measures[arr_nums[str(i)]][spawn_config][labels[k]][p]['values']) == repeat:
                        single_measures[arr_nums[str(i)]][spawn_config][labels[k]][p]['values'][j] = ret[k]
                    else:
                        single_measures[arr_nums[str(i)]][spawn_config][labels[k]][p]['values'].append(ret[k])
        if adaptive:
            writeMeasuresToFileAdaptive(f, f'{i}:{j}', numOfVehicles, ret, len(nums[i]))
        else:
            writeMeasuresToFile(f, f'{i}:{j}', numOfVehicles, ret)

    k = 0

    for g in range(0, len(groups)):
        count = 0
        while count < groups[g]:
            title = group_measures[head_titles[g]][count]['title']
            if isinstance(arr_titles[title][0], list):
                group_measures[head_titles[g]][count]['values'].append(getValueFromList(title, arr_titles[title], len(nums[i])))
            else:
                group_measures[head_titles[g]][count]['values'].append(getValue(title, arr_titles[title]))
            count += 1
            k += 1
    if adaptive:
        return intermediate_group_measures

def writeMeasuresToFileMulti(f, i, ret):
    """Salvo su file le misure effettuate"""

    f.write('----------------------------------------------------\n')
    f.write(f'\nSIMULAZIONE NUMERO {i}\n')
    f.write('\n----------------------------------------------------\n')
    f.write(f'\nNUMERO DI VEICOLI: {ret[0]}\n')

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
    f.write(f'\nTHROUGHPUT MEDIO: {round(ret[12], 2)}\n\n')


def collectMeasuresMulti(queue, repeat, single_measures, titles, labels, nums, project,
                         f, i):
    """Scrivo le misure delle simulazioni ripetute"""

    arr_titles = {k: [] for k in titles}

    arr_nums = {str(i): str(nums[i]) for i in range(0, len(nums))}

    for j in range(0, repeat):

        ret = queue.get()

        for k in range(0, len(arr_titles)):
            arr_titles[titles[k]].append(ret[k])

            for p in range(0, len(single_measures[arr_nums[str(i)]][labels[k]])):
                if single_measures[arr_nums[str(i)]][labels[k]][p]['project'] == project:
                    single_measures[arr_nums[str(i)]][labels[k]][p]['values'].append(ret[k])

        writeMeasuresToFileMulti(f, f'{i}:{j}', ret)


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


def autolabel(values, r, offset, ax):
    """Funzione per mettere il numero sopra la barra dell'istogramma"""

    i = 0

    for value in values:
        ax.annotate(f'{value}', xy=(r[i] + offset, value), xytext=(0, 3), textcoords="offset points", ha='center',
                    va='bottom')
        i += 1

def linesPerGroupsAdaptive(group_measures, groups, stepsSpawn, dir, project_label, steps):
    """Salvo su immagini gli istogrammi con le misure medie per ogni simulazione"""

    sims = []
    values = []
    labels = []
    titles = []
    colors = []

    for k in group_measures:
        if k == 'sims':
            sims = group_measures['sims']
            continue
        titles.append(k)
        for i in range(0, len(group_measures[k])):
            values.append(group_measures[k][i]['values'])
            labels.append(group_measures[k][i]['label'])
            colors.append(group_measures[k][i]['color'])

    for s in range(0, steps):
        j = 0
        for i in range(0, len(groups)):
            r = np.arange(len(values[i]))
            count = groups[i]
            fig, ax = plt.subplots()
            while count > 0:
                if isinstance(values[j][0], list):
                    ax.plot(r, values[j][0][s], color=colors[j], label=labels[j], lw=2, marker='s')
                else:
                    ax.plot(r, values[j], color=colors[j], label=labels[j], lw=2, marker='s')
                # autolabel(values[j], r, 0, ax)
                j += 1
                count -= 1
            ax.set_xticks(r)
            ax.set_title(project_label)
            ax.set_xticklabels([f'{round(sum(eval(sim)) / stepsSpawn)} veicoli / s' for sim in sims])
            ax.legend(title='Legenda', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            plt.savefig(dir + "/" + titles[i] + '_' + 'step' + str(s) + '_' + date.today().strftime("%d-%m-%Y") + '.png', bbox_inches='tight')
            plt.close(fig)

def linesPerGroups(group_measures, groups, stepsSpawn, dir, project_label):
    """Salvo su immagini gli istogrammi con le misure medie per ogni simulazione"""

    sims = []
    values = []
    labels = []
    titles = []
    colors = []

    for k in group_measures:
        if k == 'sims':
            sims = group_measures['sims']
            continue
        titles.append(k)
        for i in range(0, len(group_measures[k])):
            values.append(group_measures[k][i]['values'])
            labels.append(group_measures[k][i]['label'])
            colors.append(group_measures[k][i]['color'])

    j = 0

    for i in range(0, len(groups)):
        r = np.arange(len(values[i]))
        count = groups[i]
        fig, ax = plt.subplots()
        while count > 0:
            ax.plot(r, values[j], color=colors[j], label=labels[j], lw=2, marker='s')
            # autolabel(values[j], r, 0, ax)
            j += 1
            count -= 1
        ax.set_xticks(r)
        ax.set_title(project_label)
        ax.set_xticklabels([f'{round(sum(eval(sim)) / stepsSpawn)} veicoli / s' for sim in sims])
        ax.legend(title='Legenda', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.savefig(dir + "/" + titles[i] + '_' + date.today().strftime("%d-%m-%Y") + '.png', bbox_inches='tight')
        plt.close(fig)

def linesPerMeasure(single_measures, labels, titles, colors, projects, projects_labels, numberOfVehicles, stepsSpawn,
                    dir):
    """Salvo su immagini gli istogrammi con le misure medie per ogni simulazione"""

    values = []
    vehs = [str(i) for i in numberOfVehicles]

    i = 0

    for lab in labels:
        for k in single_measures:
            for z in range(0, len(projects)):
                values.append([])
                if len(single_measures[k][lab][z]['values']) > 0:
                    values[z].append(getValue(titles[i], single_measures[k][lab][z]['values']))
        r = np.arange(len(vehs))
        fig, ax = plt.subplots()
        for j in range(0, len(projects)):
            ax.plot(r, values[j], color=colors[j], label=projects_labels[j], lw=2, marker='s')
            # autolabel(values[j], r, 0, ax)
        ax.set_xticks(r)
        ax.set_title(lab)
        ax.set_xticklabels([f'{round(sum(eval(veh)) / stepsSpawn)} veicoli / s' for veh in vehs])
        ax.legend(title='Legenda', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.savefig(dir + "/" + titles[i] + "_" + date.today().strftime("%d-%m-%Y") + '.png',
                    bbox_inches='tight')
        plt.close(fig)

        i += 1

        values = []

def linesPerMeasureAdaptive(single_measures, labels, titles, colors, markers, projects, projects_labels, numberOfVehicles, stepsSpawn,
                    dir):
    """Salvo su immagini gli istogrammi con le misure medie per ogni simulazione"""


    vehs = [str(i) for i in numberOfVehicles]
    spawn_confs_names = [sb for sb in spawn_configs.keys()]
    i = 0

    for lab in labels:
        conf_index = 0 # [p0, p1,...     ]
        values = {sb: [] for sb in spawn_configs}
        for k in single_measures:
            for spawn_config in spawn_configs:
                for z in range(0, len(projects)):
                    values[spawn_config].append([])
                    if isinstance(single_measures[k][spawn_config][lab][z]['values'][0], list):
                        values[spawn_config][z] = getValueFromList(titles[i], single_measures[k][spawn_config][lab][z]['values'], len(numberOfVehicles[conf_index]))
                    else:
                        values[spawn_config][z].append(getValue(titles[i], single_measures[k][spawn_config][lab][z]['values']))
            conf_index += 1
        #for s in range(0, len(numberOfVehicles[0])):
        r = np.arange(len(values[spawn_confs_names[0]][0]))
        fig, axes = plt.subplots(len(spawn_configs), sharex=True, sharey=True)
        fig.suptitle(lab)
        sc_index = 0
        for spawn_config in spawn_configs:
            for j in range(0, len(projects)):
                if isinstance(values[spawn_config][j], list):
                    if (len(spawn_configs) == 1):
                        axes.plot(r, values[spawn_config][j], color=colors[j], label=projects_labels[j], lw=2,
                                            marker=markers[j])
                    else:
                        axes[sc_index].plot(r, values[spawn_config][j], color=colors[j], label=projects_labels[j], lw=2, marker=markers[j])
                else:
                    if (len(spawn_configs) == 1):
                        axes.plot(r, values[spawn_config][j], color=colors[j], label=projects_labels[j], lw=2,
                                            marker=markers[j])
                    else:
                        axes[sc_index].plot(r, values[spawn_config][j], color=colors[j], label=projects_labels[j], lw=2, marker=markers[j])
                # autolabel(values[j], r, 0, ax)
            if (len(spawn_configs) == 1):
                axes.set_xticks(r)
                axes.set_title(spawn_config)
            else:
                axes[sc_index].set_xticks(r)
                axes[sc_index].set_title(spawn_config)

            if len(values[spawn_confs_names[0]][0]) > 1:
                #x_labels = [f"{int(numberOfVehicles[0][s]/(stepsSpawn/len(numberOfVehicles[0])))} v / s" for s in range(0, len(numberOfVehicles[0]))]
                x_labels = [f"{int(numberOfVehicles[0][s] / (stepsSpawn / len(numberOfVehicles[0])))}" for s in
                            range(0, len(numberOfVehicles[0]))]
                if (len(spawn_configs) == 1):
                    axes.set_xticklabels(x_labels)
                else:
                    axes[sc_index].set_xticklabels(x_labels)#f'{round(sum(eval(veh)) / stepsSpawn)} veicoli / s' for veh in vehs])
            if (len(spawn_configs) == 1):
                axes.legend(title='Legend', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
                axes.set_ylabel(lab)
                axes.set_xlabel("vehicles spawned/sec")
            else:
                axes[sc_index].legend(title='Legend', bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
                axes[sc_index].set_ylabel(lab)
                axes[sc_index].set_xlabel("vehicles/sec")
            sc_index += 1
        plt.savefig(dir + "/" + titles[i] + "_" + date.today().strftime("%d-%m-%Y") + '.png',
                    bbox_inches='tight')
        plt.close(fig)

        i += 1

