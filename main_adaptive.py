import sys
import os
import importlib.util
from multiprocessing import Process, Queue
from inpout import *
from config import *
from reservation import traiettorie

from sumolib import checkBinary

'''def trainFromCollectedMeasures():
    mes = evaluateMeasures()
    evaluation = {k: "" for k in mes}
    for main_step in mes:
        # solo th
        th = mes[main_step][-1]
        best_val = max(th['mean_values'])
        i = th['mean_values'].index(best_val)
        evaluation[main_step] = th['projects'][i]
    return evaluation
'''
def trainFromCollectedMeasures(intermediate_measures, main_steps):

    #mes = evaluateMeasures()
    evaluation = {i: "" for i in range(0, main_steps)}

    temp = {x: [-1 for t in range(0, main_steps)] for x in intermediate_measures}

    for p in intermediate_measures:

        for s in range(0, main_steps):
            sum = 0
            for repeat in intermediate_measures[p]:
                sum += repeat[s]
            if len(intermediate_measures[p]) > 0:
                mean = sum / len(intermediate_measures[p])
                temp[p][s] = mean
            else:
                temp[p][s] = 0
    index = 0
    for s in range(0, main_steps):

        best = max([temp[x][s] for x in temp])
        p = [temp[x][s] for x in temp].index(best)
        evaluation[s] = projects[p]
        index += 1
    return evaluation

def evaluateMeasures():
    mes = {}
    #print(f"group: {group_measures}\n")
    print(f"single: {single_measures}\n")
    for k in single_measures: # V SIMULAZIONE
        mes[k] = []
        for j in single_measures[k]: # V MISURA

            #print(f"    {j}\n")
            #print(f"single_measures[k]['Throughput medio']: {single_measures[k]['Throughput medio']}")
            #for q in single_measures[k][j]: # V PROGETTO
                #vals_per_repeat = q['values']
                #print(f"        {q}\n")
                #print(f"        val medio: {sum(vals_per_repeat) / len(vals_per_repeat)}\n")
            mes[k].append({"measure": j,
                        "projects" : [q['project'] for q in single_measures[k][j]],
                        "values" : [q['values'] for q in single_measures[k][j]],
                        "mean_values": [sum(q['values'])/len(q['values']) for q in single_measures[k][j]]})

        '''th_values = single_measures[k]['Throughput medio']
        for el in th_values:
            vals = el['values']
            print(f"        calcolo media di throuput di {el['project']}....\n")
            print(f"        val medio: {sum(vals) / len(vals)}\n")'''

        print(f"mes{k}: {mes}")
    return mes


if __name__ == "__main__":
    """Main che avvia un certo numero di simulazioni in parallelo (in modalità manuale o automatica)"""

    dir = f"outputs_{date.today().strftime('%d-%m-%Y')}"
    root = os.path.abspath(os.path.split(__file__)[0])
    path = os.path.join(root, dir)
    intermediate_measures = {}

    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except OSError:
            print(f"\nCreazione della cartella {path} fallita...")
            sys.exit(-1)

    print("\nCalcolo per la reservation la matrice di celle a partire da tutte le traiettorie possibili...")
    traiettorie_matrice = traiettorie.run(False, celle_per_lato)

    projs = checkChoice(projects,
                        '\nQuale progetto vuoi avviare? (classic_tls, classic_precedence, reservation, '
                        'precedence_with_auction): ', "\nUtilizzo il semaforo classico come default...",
                        '\nInserire un nome di progetto valido!',
                        mode, arr=True)

    for project in projs:
        intermediate_measures[project] = []
        project_label = projects_labels[projects.index(project)]

        try:
            module = importlib.import_module(".main", package=project)
        except Exception:
            print("\nImpossibile trovare il progetto...")
            sys.exit(-1)

        print(f"\nEseguo il progetto {project}...")

        config_file = os.path.join(os.path.split(__file__)[0], project,
                                   "intersection.sumocfg")  # file di configurazione della simulazione

        #default dati
        choice = checkChoice(['d', 'D', 'g', 'G'],
                             '\nVuoi raccogliere dati o avere una visualizzazione grafica? (g = grafica, '
                             'd = dati): ',
                             "\nUtilizzo la modalità dati come default...",
                             '\nInserire un carattere tra d e g!',
                             mode)

        '''
        #default grafica
        choice = checkChoice(['g', 'G', 'd', 'D'],
                             '\nVuoi raccogliere dati o avere una visualizzazione grafica? (g = grafica, '
                             'd = dati): ',
                             "\nUtilizzo la modalità dati come default...",
                             '\nInserire un carattere tra d e g!',
                             mode)
        '''

        sumoBinary = checkBinary('sumo') if choice in ['d', 'D'] else checkBinary('sumo-gui')

        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"] if choice in ['d', 'D'] else \
            [sumoBinary, "-c", config_file, "--time-to-teleport", "-1", "-S", "-Q"]

        sumoDict = {'classic_tls': sumoCmd,
                    'classic_precedence': sumoCmd,
                    'reservation': sumoCmd + ["--step-length", "0.050"],
                    'precedence_with_auction': sumoCmd}

        schema = ''
        if choice in ['g', 'G']:
            schema = checkChoice(['s', 'S', 'n', 'N'],
                                 '\nDesideri visualizzare le auto con uno schema di colori significativo? '
                                 '(s, n): ',
                                 "\nUtilizzo lo schema significativo come default...",
                                 '\nInserire un carattere tra s e n!', mode)

        diff = checkInput(diffSim, f'\nInserire il numero di simulazioni diverse: ',
                          f'\nUtilizzo come default {diffSim} run diverse...',
                          '\nInserire un numero di simulazioni positivo!', mode,
                          f'\nEseguo {diffSim} simulazioni differenti...', diffSim)

        dir = os.path.join(path, project)

        if not os.path.exists(dir):
            try:
                os.mkdir(dir)
            except OSError:
                print(f"\nCreazione della cartella {dir} fallita...")
                sys.exit(-1)

        for i in range(0, diff):

            output_file = os.path.join(dir, f'{i}.txt')
            f = open(output_file, "w")

            print(f'\nUtilizzo un set di {numberOfVehicles[i]} veicoli in {stepsSpawn} steps...')

            repeat = checkInput(repeatSim, f'\nInserire il numero di ripetizioni della simulazione {i}: ',
                                f'\nUtilizzo come default {repeatSim} stesse run...',
                                '\nInserire un numero di simulazioni positivo!', mode,
                                f'\nEseguo {repeatSim} simulazioni identiche in parallelo...', repeatSim,
                                max_inp=repeatSim)

            procs = []
            queue = Queue()

            for j in range(0, repeat):

                args = {
                    'classic_tls': (
                        numberOfVehicles[i], schema, sumoDict['classic_tls'], dir, j, queue, seeds[j]),
                    'classic_precedence': (
                        numberOfVehicles[i], schema, sumoDict['classic_precedence'], dir, j, queue, seeds[j]),
                    'reservation': (
                        numberOfVehicles[i], schema, sumoDict['reservation'], celle_per_lato,
                        traiettorie_matrice, secondi_di_sicurezza, dir, j, queue, seeds[j]),
                    'reservation_with_auction': (
                        numberOfVehicles[i], schema, sumoDict['reservation'], celle_per_lato,
                        traiettorie_matrice, secondi_di_sicurezza, dir, j, queue, seeds[j]),
                    'precedence_with_auction': (
                        numberOfVehicles[i], schema, sumoDict['precedence_with_auction'], simulationMode,
                        instantPay, dimensionOfGroups, dir, j, queue, seeds[j])
                }

                p = Process(target=module.run, args=args[project])
                p.start()
                procs.append(p)

            for p in procs:
                p.join()

            intermediate_measures = collectMeasures(queue, repeat, sum(numberOfVehicles[i]), group_measures, single_measures, groups, titles,
                            head_titles, labels, numberOfVehicles, project, f, i, intermediate_measures, adaptive=True)

            f.close()

        linesPerGroups(group_measures, groups, stepsSpawn, dir, project_label)

        clearMeasures(group_measures, groups, head_titles)

    linesPerMeasure(single_measures, labels, titles, colors, projects, projects_labels, numberOfVehicles, stepsSpawn,
                    path)

    train = trainFromCollectedMeasures(intermediate_measures, 4)
    print(f"train: {train}\n")
    print(f"intermediate_measures: {intermediate_measures}\n")


