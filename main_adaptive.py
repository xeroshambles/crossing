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
            'precedence_with_comp_auction': (
                numberOfVehicles[i], schema, sumoDict['precedence_with_comp_auction'], dir, j, queue, seeds[j],
                simulationMode if simulationMode else not simulationMode, instantPay, dimensionOfGroups),
            'adaptive': (
                numberOfVehicles[i], schema, sumoDict['adaptive'], dir, j, queue, seeds[j],
                celle_per_lato, traiettorie_matrice, secondi_di_sicurezza,
                simulationMode, instantPay, dimensionOfGroups, train, spawn_configs[spawn_config]
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

    evaluations = {}
    for config in configs:
        evaluations[str(config)] = {}
        n_main_steps = len(config)
        intermediate_measures = intermediate_group_measures[str(config)]


        for spawn_config in spawn_configs:
            intermediate_measures_temp = intermediate_measures[spawn_config]
            evaluations[str(config)][spawn_config] = {}
            evaluations_temp = evaluations[str(config)][spawn_config]
            for m in range(0, len(training_comps)):
                evaluation = {i: "" for i in range(0, n_main_steps)}
                evaluations_temp[m] = {}
                temp = {x: [-1 for t in range(0, n_main_steps)] for x in intermediate_measures_temp[m]}
                for p in intermediate_measures_temp[m]:
                    for s in range(0, n_main_steps):
                        sum = 0
                        for repeat in intermediate_measures_temp[m][p]:
                                sum += repeat[s]
                        if len(intermediate_measures_temp[m][p]) > 0:
                            mean = sum / len(intermediate_measures_temp[m][p])
                            temp[p][s] = mean
                        else:
                            temp[p][s] = 0
                index = 0
                for s in range(0, n_main_steps):
                    if training_comps[m] == "min":
                        best = min([temp[x][s] for x in temp])
                    if training_comps[m] == "max":
                        best = max([temp[x][s] for x in temp])
                    p = [temp[x][s] for x in temp].index(best)
                    if [x for x in temp if temp[x][s] == 0] and s > 0:
                        evaluation[s] = evaluation[s - 1]
                    else:
                        evaluation[s] = projects[p]
                    index += 1
                evaluations_temp[m] = evaluation
    return evaluations


if __name__ == "__main__":
    """Main che avvia un certo numero di simulazioni in parallelo (in modalità manuale o automatica)"""

    dir = f"adaptive_{date.today().strftime('%d-%m-%Y')}"
    root = os.path.abspath(os.path.split(__file__)[0])
    path = os.path.join(root, dir)


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
                        'precedence_with_comp_auction): ', "\nUtilizzo il semaforo classico come default...",
                        '\nInserire un nome di progetto valido!',
                        mode, arr=True)


    sim = "adaptive"
    repeat_train = 1


    intermediate_group_measures = {}
    for project in projs:
        if project == "adaptive":
            train = False
            sims_per_main_step = trainFromCollectedMeasures(intermediate_measures, numberOfVehicles)
            repeat_train = len(titles)
        else:
            train = True
            sims_per_main_step = {0: project, 1: project, 2: project, 3: project}

        project_label = projects_labels[projs.index(project)]

        try:
            module = importlib.import_module(".main", package=sim)
        except Exception:
            print("\nImpossibile trovare il progetto...")
            sys.exit(-1)



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
                    'precedence_with_comp_auction': sumoCmd + ["--step-length", "0.25"],
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


        #for rt in range(0, repeat_train):
        for GGG in range(0, 1):
            rt = 13
            #rt = repeat_train - 1
            if project == "adaptive":
                print(f"\nTraining per misura {labels[rt]}")
                dir = os.path.join(path, f"adaptive_{titles[rt]}_training")

            else:
                dir = os.path.join(path, f"{project}")

            if not os.path.exists(dir):
                try:
                    os.mkdir(dir)
                except OSError:
                    print(f"\nCreazione della cartella {dir} fallita...")
                    sys.exit(-1)
            for spawn_config in spawn_configs:
                print(f"\nEseguo il progetto {project} {spawn_config} adattativo...")
                if project == "adaptive":
                    tf = open(os.path.join(path, f"{spawn_config}_training_sets.txt"), "a")
                    tf.write(f"{titles[rt]} : {sims_per_main_step[str(numberOfVehicles[i])][spawn_config][rt]}\n")
                    tf.close()
                for i in range(0, diff):
                    if str(numberOfVehicles[i]) not in intermediate_group_measures.keys():
                        intermediate_group_measures[str(numberOfVehicles[i])] = {}
                    if spawn_config not in intermediate_group_measures[str(numberOfVehicles[i])].keys():
                        intermediate_group_measures[str(numberOfVehicles[i])][spawn_config] = {}
                    intermediate_group_measures_temp = intermediate_group_measures[str(numberOfVehicles[i])][spawn_config]
                    for m in range(0, len(titles)):
                        if m not in intermediate_group_measures_temp.keys():
                            intermediate_group_measures_temp[m] = {}
                        intermediate_group_measures_temp[m][project] = []


                    repeat = checkInput(repeatSim, f'\nInserire il numero di ripetizioni della simulazione {i}: ',
                                        f'\nUtilizzo come default {repeatSim} stesse run...',
                                        '\nInserire un numero di simulazioni positivo!', mode,
                                        f'\nEseguo {repeatSim} simulazioni identiche in parallelo...', repeatSim,
                                        max_inp=repeatSim)

                    output_file = os.path.join(dir, f'{i}.txt')
                    f = open(output_file, "w")

                    queue = Queue()


                    print(f'\nUtilizzo un set di {numberOfVehicles[i]} veicoli in {stepsSpawn} steps...')

                    procs = []
                    if train:
                        queue = simulate(project=sim, procs=[], queue=queue, train=sims_per_main_step, i=i)
                    else:
                        queue = simulate(project=sim, procs=[], queue=queue, train=sims_per_main_step[str(numberOfVehicles[i])][spawn_config][rt], i=i)
                    intermediate_measures = collectMeasuresAdaptive(queue, repeat, sum(numberOfVehicles[i]), group_measures,
                                                            single_measures, groups, titles,
                                                            head_titles, labels, numberOfVehicles,
                                                            project, f, i, spawn_config, intermediate_group_measures, adaptive=True)

                    print(f"train: {sims_per_main_step}\n")
                    print(f"intermediate_measures: {intermediate_measures}\n")
                    #train = trainFromCollectedMeasures(intermediate_group_measures, numberOfVehicles)
                    f.close()

                #linesPerGroupsAdaptive(group_measures, groups, stepsSpawn, dir, project_label, len(numberOfVehicles[0]))

            clearMeasures(group_measures, groups, head_titles)
            if train == False:
                linesPerMeasureAdaptive(single_measures, labels, titles, colors, projects, projects_labels,
                                        numberOfVehicles, stepsSpawn,
                                        dir)

        #single_measures = {'[50, 100, 150, 200]' : {'Tempo totale (s)': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [201]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [201]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [200]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [201]}], 'Tempo medio in testa (s)': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[3.122448979591837, 3.3608247422680413, 1.3984962406015038, 0.1794871794871795]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[4.775510204081633, 3.917525773195876, 1.5426356589147288, 0.20512820512820512]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[0.42857142857142855, 1.1326530612244898, 0.8540145985401459, 0.17424242424242425]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[0.42857142857142855, 2.520408163265306, 1.7218045112781954, 0.16393442622950818]]}], 'Deviazione standard tempo in testa (s)': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[8.355940458217404, 10.106837092821433, 6.918363761555473, 1.8425891510996577]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[9.346537733130628, 10.085888992290148, 6.16568115142634, 2.209298382414164]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[1.2453996981544784, 2.7613873882896107, 1.9009799470039073, 0.8833151409322632]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[1.2453996981544784, 8.290921506397192, 7.77150509750724, 1.3389539331300193]]}], 'Massimo tempo in testa (s)': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[38, 42, 41, 20]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[36, 43, 39, 24]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[7, 18, 10, 8]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[7, 43, 42, 14]]}], 'Tempo medio in coda (s)': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[2.183673469387755, 12.206185567010309, 18.93233082706767, 7.3418803418803416]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[3.36734693877551, 12.536082474226804, 15.24031007751938, 7.05982905982906]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[0.2653061224489796, 1.5918367346938775, 3.021897810218978, 0.75]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[0.2653061224489796, 5.877551020408164, 17.157894736842106, 7.516393442622951]]}], 'Deviazione standard tempo in coda (s)': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[4.897619035807954, 14.541755126226407, 19.09186162430292, 7.718511872384697]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[7.07018424131678, 13.976461696731702, 11.97074935891356, 7.607116099770978]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[0.8517810920289464, 3.016406615710757, 3.9364794996127053, 1.8396928267973696]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[0.8517810920289464, 11.458234100260672, 16.493262285885855, 8.381511275124495]]}], 'Massimo tempo in coda (s)': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[20, 49, 65, 25]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[32, 49, 39, 25]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[4, 15, 15, 11]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[4, 39, 57, 26]]}], 'Velocità media (m/s)': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[7.096936320122203, 4.726500708585724, 7.441516006196384, 9.926042226892745]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[2.856625982339249, 1.959389814195945, 3.626654014161882, 4.182017145061912]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[5.052966808502291, 3.6382995515737466, 2.906272386345582, 3.429861104820443]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[5.052966808502291, 3.7007164177649177, 7.179539092679051, 9.788154164255737]]}], 'Deviazione standard velocità (m/s)': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[4.971585175284911, 5.40731745245313, 5.605137941669504, 4.790812665339744]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[2.7130624577645563, 2.1424188034617493, 2.8805350603748257, 2.9073590139118126]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[1.634847524757189, 1.7726066761096122, 1.6028112489968336, 1.7308311323820502]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[1.634847524757189, 3.506356560268834, 5.7302613338562045, 4.772156800083883]]}], 'Lunghezza media delle code': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[0.2816666666666667, 1.095, 3.1366666666666667, 4.336601307189543]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[0.36166666666666664, 1.4400000000000002, 3.105, 3.3758169934640514]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[0.05000000000000001, 0.2616666666666667, 0.66, 0.6183333333333333]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[0.05000000000000001, 0.2616666666666667, 2.6033333333333335, 4.1879084967320255]]}], 'Deviazione standard lunghezza delle code': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[0.5377396106749891, 1.526567500418286, 3.70161076049633, 5.137116655659525]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[0.3869933964409327, 1.656421846430834, 3.313348004662353, 3.0779924891483166]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[0.09073771725877466, 0.3728680135859813, 0.8468766143896052, 0.7395700703036115]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[0.09073771725877466, 0.3728680135859813, 2.885190153563925, 5.069651091520606]]}], 'Massima lunghezza delle code': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[6, 14, 25, 30]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[6, 16, 25, 20]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[3, 7, 10, 9]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[3, 7, 19, 26]]}], 'Veicoli fermi': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[16, 57, 81, 69]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[32, 81, 100, 77]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[13, 61, 88, 37]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[13, 64, 82, 70]]}], 'Throughput medio': [{'project': 'classic_precedence', 'color': '#DF1515', 'values': [[0.4473684210526316, 0.30158730158730157, 0.45161290322580644, 0.6590909090909091]]}, {'project': 'precedence_with_comp_auction', 'color': '#1524DF', 'values': [[0.2631578947368421, 0.16393442622950818, 0.2982456140350877, 0.32142857142857145]]}, {'project': 'reservation', 'color': '#15DF1E', 'values': [[0.5641025641025641, 0.4, 0.3170731707317073, 0.38461538461538464]]}, {'project': 'adaptive', 'color': '#FCFF33', 'values': [[0.5641025641025641, 0.4, 0.43283582089552236, 0.6666666666666666]]}]}}











