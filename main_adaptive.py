import sys
import os
import importlib.util
from multiprocessing import Process, Queue
from inpout import *
from utils import *
from config_adaptive import *
from reservation import traiettorie
from adaptive.main import adaptiveSimulation
import traci
from sumolib import checkBinary, miscutils

def parseString(s):
    """ Takes string and returns a list representation of it"""
    split = s.split(',')
    split[0] = split[0].replace('[', '')
    split[-1] = split[-1].replace(']', '')
    return split


def simulate(procs, queue, project, train, i, adapt=True):
    """ This function allows to simulate <repeat> times using <repeat> different seeds"""

    for j in range(0, repeat):

        args = {
            'classic_tls': (
                numberOfVehicles[i], schema, sumoDict['classic_tls'], dir, j, queue, seeds[j]),
            'classic_precedence': (
                numberOfVehicles[i], schema, sumoDict['classic_precedence'], dir, j, queue, seeds[j]),
            'reservation': (
                numberOfVehicles[i], schema, sumoDict['reservation'], dir, j, queue, seeds[j], celle_per_lato,
                traiettorie_matrice, secondi_di_sicurezza),
            'reservation_with_auction': (
                numberOfVehicles[i], schema, sumoDict['reservation'], dir, j, queue, seeds[j], celle_per_lato,
                traiettorie_matrice, secondi_di_sicurezza),
            'precedence_with_auction': (
                numberOfVehicles[i], schema, sumoDict['precedence_with_auction'], dir, j, queue, seeds[j],
                simulationMode, instantPay, dimensionOfGroups),
            'adaptive': (
                numberOfVehicles[i], schema, sumoDict['adaptive'], dir, j, queue, seeds[j],
                celle_per_lato, traiettorie_matrice, secondi_di_sicurezza,
                simulationMode, instantPay, dimensionOfGroups, train[str(numberOfVehicles[i])]
            )
        }
        if adapt:
            p = Process(target=module.adaptiveSimulation, args=args[project])
        else:
            p = Process(target=module.run, args=args[project])
        p.start()
        procs.append(p)
    for p in procs:
        p.join()

    return queue

def trainFromCollectedMeasures(intermediate_group_measures, configs):
    """ Permette di calcolare le misure medie di througput e di valutarle decidendo quale approccio sia migliore in ogni macro fase"""

    evaluations = {str(config): {} for config in configs}
    for config in configs:
        n_main_steps = len(config)
        intermediate_measures = intermediate_group_measures[str(config)]
        evaluation = {i: "" for i in range(0, n_main_steps)}

        temp = {x: [-1 for t in range(0, n_main_steps)] for x in intermediate_measures}

        for p in intermediate_measures:

            for s in range(0, n_main_steps):
                sum = 0
                for repeat in intermediate_measures[p]:
                    sum += repeat[s]
                if len(intermediate_measures[p]) > 0:
                    mean = sum / len(intermediate_measures[p])
                    temp[p][s] = mean
                else:
                    temp[p][s] = 0
        index = 0
        for s in range(0, n_main_steps):

            best = max([temp[x][s] for x in temp])
            p = [temp[x][s] for x in temp].index(best)
            if [x for x in temp if temp[x][s] == 0] and s > 0:
                evaluation[s] = evaluation[s - 1]
            else:
                evaluation[s] = projects[p]
            index += 1
        evaluations[str(config)] = evaluation
    return evaluations


if __name__ == "__main__":
    """Main che avvia un certo numero di simulazioni in parallelo (in modalità manuale o automatica)"""

    dir = f"outputs_{date.today().strftime('%d-%m-%Y')}_substeps"
    root = os.path.abspath(os.path.split(__file__)[0])
    path = os.path.join(root, dir)
    intermediate_group_measures = {}

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

    a = 0
    sim = "adaptive"
    for project in projs:
        if project == "adaptive":
            train = False
            #s = {'[50, 100, 150, 200]': {'reservation': [[0.6153846153846154, 0.5454545454545454, 0.4444444444444444, 0.32407407407407407]], 'classic_precedence': [[0.4473684210526316, 0.4594594594594595, 0.4891304347826087, 0.6]], 'precedence_with_auction': [[0.3684210526315789, 0.2894736842105263, 0.3010752688172043, 0.36363636363636365]]}}
            #sims_per_main_step = trainFromCollectedMeasures(s, numberOfVehicles)
            sims_per_main_step = trainFromCollectedMeasures(intermediate_group_measures, numberOfVehicles)
        else:
            train = True
            sims_per_main_step = {'[50, 100, 150, 200]': {0: project, 1: project, 2: project, 3: project}}

        project_label = projects_labels[projs.index(project)]

        try:
            module = importlib.import_module(".main", package=sim)
        except Exception:
            print("\nImpossibile trovare il progetto...")
            sys.exit(-1)

        print(f"\nEseguo il progetto {project} adattativo...")

        config_file = os.path.join(os.path.split(__file__)[0], sim,
                                   "intersection.sumocfg")  # file di configurazione della simulazione
        '''
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
        sumoBinary = checkBinary('sumo') if choice in ['d', 'D'] else checkBinary('sumo-gui')

        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"] if choice in ['d', 'D'] else \
            [sumoBinary, "-c", config_file, "--time-to-teleport", "-1", "-S", "-Q"]

        sumoDict = {'classic_tls': sumoCmd,
                    'classic_precedence': sumoCmd,
                    'reservation': sumoCmd + ["--step-length", "0.05"],
                    'precedence_with_auction': sumoCmd + ["--step-length", "0.25"],
                    'adaptive': sumoCmd + ["--step-length", "0.05"]}

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
            if str(numberOfVehicles[i]) not in intermediate_group_measures.keys():
                intermediate_group_measures[str(numberOfVehicles[i])] = {}
            intermediate_group_measures[str(numberOfVehicles[i])][project] = []

            repeat = checkInput(repeatSim, f'\nInserire il numero di ripetizioni della simulazione {i}: ',
                                f'\nUtilizzo come default {repeatSim} stesse run...',
                                '\nInserire un numero di simulazioni positivo!', mode,
                                f'\nEseguo {repeatSim} simulazioni identiche in parallelo...', repeatSim,
                                max_inp=repeatSim)

            output_file = os.path.join(dir, f'{i}.txt')
            f = open(output_file, "w")

            queue = Queue()


            print(f'\nUtilizzo un set di {numberOfVehicles[i]} veicoli in {stepsSpawn} steps...')

            #dummy_train = {'0': "reservation", '1': "precedence_with_auction", '2': "classic_precedence", '3': "reservation"}
            #dummy_train = {'0': "classic_precedence", '1': "reservation", '2': "precedence_with_auction",'3': "classic_precedence"}
            #dummy_train = {'0': "reservation", '1': "classic_precedence", '2': "precedence_with_auction",'3': "classic_precedence"}
            #dummy_train = {'0': "classic_precedence", '1': "precedence_with_auction", '2': "classic_precedence", '3': "classic_precedence"}
            #dummy_train = {'0': "reservation", '1': "classic_precedence", '2': "reservation",'3': "classic_precedence"}

            procs = []
            queue = simulate(project=sim, procs=[], queue=queue, train=sims_per_main_step, i=i)

            intermediate_group_measures = collectMeasures(queue, repeat, sum(numberOfVehicles[i]), group_measures,
                                                    single_measures, groups, titles,
                                                    head_titles, labels, numberOfVehicles,
                                                    project, f, i, intermediate_group_measures, adaptive=True)

            print(f"train: {sims_per_main_step}\n")
            #print(f"intermediate_measures: {intermediate_group_measures}\n")
            #train = trainFromCollectedMeasures(intermediate_group_measures, numberOfVehicles)
            f.close()

        linesPerGroupsAdaptive(group_measures, groups, stepsSpawn, dir, project_label, len(numberOfVehicles[0]))

        clearMeasures(group_measures, groups, head_titles)



    linesPerMeasureAdaptive(single_measures, labels, titles, colors, projects, projects_labels, numberOfVehicles, stepsSpawn,
                    path)









