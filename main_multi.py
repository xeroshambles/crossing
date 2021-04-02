import importlib.util
from multiprocessing import Process, Queue
from inpout_multi import *
from config_multi import *
from reservation import traiettorie

from sumolib import checkBinary


if __name__ == "__main__":
    """Main che avvia un certo numero di simulazioni in parallelo (in modalità manuale o automatica)"""

    dir = f"outputs_multi_{date.today().strftime('%d-%m-%Y')}"
    root = os.path.abspath(os.path.split(__file__)[0])
    path = os.path.join(root, dir)

    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except OSError:
            print(f"\nCreazione della cartella {path} fallita...")
            sys.exit(-1)

    print("\nCalcolo per la reservation la matrice di celle a partire da tutte le traiettorie possibili...")
    matrixTrajectories = traiettorie.run(False, cellsPerSide)

    projs = checkChoice(projects_multi,
                        '\nQuale progetto vuoi avviare? (multi_classic_tls_classic_precedence, '
                        'multi_classic_precedence, multi_reservation_classic_precedence, '
                        'multi_comp_auction_classic_precedence, multi_coop_auction_classic_precedence): ',
                        "\nUtilizzo il semaforo classico come default...",
                        '\nInserire un nome di progetto valido!',
                        mode, arr=True)

    for project in projs:

        project_label = projects_labels_multi[projects_multi.index(project)]

        try:
            module = importlib.import_module(".main", package=project)
        except Exception:
            print("\nImpossibile trovare il progetto...")
            sys.exit(-1)

        print(f"\nEseguo il progetto {project}...")

        config_file = os.path.join(os.path.split(__file__)[0], project,
                                   "intersection.sumocfg")  # file di configurazione della simulazione

        choice = checkChoice(['d', 'D', 'g', 'G'],
                             '\nVuoi raccogliere dati o avere una visualizzazione grafica? (g = grafica, '
                             'd = dati): ',
                             "\nUtilizzo la modalità dati come default...",
                             '\nInserire un carattere tra d e g!',
                             mode)

        sumoBinary = checkBinary('sumo') if choice in ['d', 'D'] else checkBinary('sumo-gui')

        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"] if choice in ['d', 'D'] else \
            [sumoBinary, "-c", config_file, "--time-to-teleport", "-1", "-S", "-Q"]

        sumoDict = {'multi_classic_tls_classic_precedence': sumoCmd,
                    'multi_classic_precedence': sumoCmd,
                    'multi_reservation': sumoCmd + ['--step-length', '0.05'],
                    'multi_reservation_classic_precedence': sumoCmd + ['--step-length', '0.05'],
                    'multi_comp_auction': sumoCmd,
                    'multi_comp_auction_classic_precedence': sumoCmd,
                    'multi_coop_auction': sumoCmd,
                    'multi_coop_auction_classic_precedence': sumoCmd,
                    'multi_classic_precedence_classic_tls': sumoCmd,
                    'multi_classic_precedence_reservation': sumoCmd + ['--step-length', '0.05'],
                    'multi_classic_precedence_comp_auction': sumoCmd,
                    'multi_classic_precedence_coop_auction': sumoCmd}

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
                          f'\nEseguo {diffSim} scenari di traffico differenti...', diffSim)

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
                                f'\nEseguo {repeatSim} simulazioni in parallelo...', repeatSim,
                                max_inp=repeatSim)

            procs = []
            queue = Queue()

            for j in range(0, repeat):

                args = {
                    'multi_classic_tls_classic_precedence': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_classic_tls_classic_precedence'],
                        dir, j, queue, seeds[j]),
                    'multi_classic_precedence': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_classic_precedence'],
                        dir, j, queue, seeds[j]),
                    'multi_reservation': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_reservation'],
                        cellsPerSide, matrixTrajectories, securitySecs, dir, j, queue, seeds[j]),
                    'multi_reservation_classic_precedence': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_reservation_classic_precedence'],
                        cellsPerSide, matrixTrajectories, securitySecs, dir, j, queue, seeds[j]),
                    'multi_comp_auction': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_comp_auction'],
                        simulationMode if simulationMode else not simulationMode, instantPay, dimensionOfGroups, dir,
                        j, queue, seeds[j]),
                    'multi_comp_auction_classic_precedence': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_comp_auction_classic_precedence'],
                        simulationMode if simulationMode else not simulationMode, instantPay, dimensionOfGroups, dir,
                        j, queue, seeds[j]),
                    'multi_coop_auction': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_coop_auction'],
                        simulationMode if not simulationMode else not simulationMode, instantPay, dimensionOfGroups,
                        dir, j, queue, seeds[j]),
                    'multi_coop_auction_classic_precedence': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_coop_auction_classic_precedence'],
                        simulationMode if not simulationMode else not simulationMode, instantPay, dimensionOfGroups,
                        dir, j, queue, seeds[j]),
                    'multi_classic_precedence_classic_tls': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_classic_precedence_classic_tls'],
                        dir, j, queue, seeds[j]),
                    'multi_classic_precedence_reservation': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_classic_precedence_reservation'],
                        cellsPerSide, matrixTrajectories, securitySecs, dir, j, queue, seeds[j]),
                    'multi_classic_precedence_comp_auction': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_classic_precedence_comp_auction'],
                        simulationMode if simulationMode else not simulationMode, instantPay, dimensionOfGroups, dir,
                        j, queue, seeds[j]),
                    'multi_classic_precedence_coop_auction': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['multi_classic_precedence_coop_auction'],
                        simulationMode if not simulationMode else not simulationMode, instantPay, dimensionOfGroups,
                        dir, j, queue, seeds[j]),
                }

                p = Process(target=module.run, args=args[project])
                p.start()
                procs.append(p)

            for p in procs:
                p.join()

            collectMeasures(queue, repeat, group_measures_multi, single_measures_multi, groups_multi, titles_multi,
                            head_titles_multi, labels_multi, numberOfVehicles, divertedPercents, project, f, i)

            f.close()

        sims = []
        values = []
        labels = []
        titles = []
        colors = []

        for k in group_measures_multi:
            if k == 'sims':
                sims = group_measures_multi['sims']
                continue
            titles.append(k)
            for i in range(0, len(group_measures_multi[k])):
                if "tutti" in group_measures_multi[k][i]['label']:
                    if "Massima" in group_measures_multi[k][i]['label']:
                        maxs = [-1 for i in range(0, len(group_measures_multi[k][i]['values'][0]))]
                        for j in range(0, len(group_measures_multi[k][i]['values'])):
                            for h in range(0, len(group_measures_multi[k][i]['values'][j])):
                                if maxs[h] < group_measures_multi[k][i]['values'][j][h]:
                                    maxs[h] = group_measures_multi[k][i]['values'][j][h]
                        values.append(maxs)
                    else:
                        means = [0 for i in range(0, len(group_measures_multi[k][i]['values'][0]))]
                        for j in range(0, len(group_measures_multi[k][i]['values'])):
                            for h in range(0, len(group_measures_multi[k][i]['values'][j])):
                                means[h] += round(group_measures_multi[k][i]['values'][j][h] /
                                                  len(group_measures_multi[k][i]['values']), 2)
                        values.append(means)
                else:
                    values.append(group_measures_multi[k][i]['values'])
                labels.append(group_measures_multi[k][i]['label'])
                colors.append(group_measures_multi[k][i]['color'])

        linesPerGroups(sims, values, labels, titles, colors, groups_multi, stepsSpawn, dir, project_label)

        clearMeasures(group_measures_multi, groups_multi, head_titles_multi)

    linesPerMeasure(single_measures_multi, labels_multi, titles_multi, colors_multi, projects_multi,
                    projects_labels_multi, numberOfVehicles, stepsSpawn, path)
