import sys
import os
import importlib.util
from multiprocessing import Process, Queue
from inpout import *
from config import *
from reservation import traiettorie

from sumolib import checkBinary

if __name__ == "__main__":
    """Main che avvia un certo numero di simulazioni in parallelo (in modalità manuale o automatica)"""

    dir = f"outputs_{date.today().strftime('%d-%m-%Y')}"
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
                        'auction): ', "\nUtilizzo il semaforo classico come default...",
                        '\nInserire un nome di progetto valido!',
                        mode, arr=True)

    for project in projs:

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

        sumoDict = {'classic_tls': sumoCmd,
                    'classic_precedence': sumoCmd,
                    'reservation': sumoCmd + ["--step-length", "0.050"],
                    'auction': sumoCmd}

        schema = ''
        if choice in ['g', 'G']:
            schema = checkChoice(['s', 'S', 'n', 'N'],
                                 '\nDesideri visualizzare le auto con uno schema di colori significativo? '
                                 '(s, n): ',
                                 "\nUtilizzo lo schema significativo come default...",
                                 '\nInserire un carattere tra s e n!', mode)

        diff = checkInput(diffSim, f'\nInserire il numero di simulazioni diverse: ',
                          f'\nUtilizzo come default 4 run diverse...',
                          '\nInserire un numero di simulazioni positivo!', mode,
                          f'\nEseguo {diffSim} simulazioni differenti...', diffSim, diffSim)

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

            print(f'\nUtilizzo un set di {numberOfVehicles[i]} veicoli in {numberOfSteps} steps...')

            repeat = checkInput(repeatSim, f'\nInserire il numero di ripetizioni della simulazione {i}: ',
                                f'\nUtilizzo come default 10 stesse run...',
                                '\nInserire un numero di simulazioni positivo!', mode,
                                f'\nEseguo {repeatSim} simulazioni identiche in parallelo...', repeatSim,
                                repeatSim)

            procs = []
            queue = Queue()

            for j in range(0, repeat):

                args = {'classic_tls': (
                    numberOfSteps, numberOfVehicles[i], schema, sumoDict['classic_tls'], dir, j, queue, seeds[j]),
                    'classic_precedence': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['classic_precedence'], dir, j,
                        queue, seeds[j]),
                    'reservation': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['reservation'], celle_per_lato,
                        traiettorie_matrice, secondi_di_sicurezza, dir, j, queue, seeds[j]),
                    'auction': (
                        numberOfSteps, numberOfVehicles[i], schema, sumoDict['auction'], True, True, -1, dir, j, queue,
                        seeds[j])}

                p = Process(target=module.run, args=args[project])
                p.start()
                procs.append(p)

            for p in procs:
                p.join()

            collectMeasures(queue, repeat, sum(numberOfVehicles[i]), line_measures, config_measures, groups, titles,
                            head_titles, labels, numberOfVehicles, project, f, i)

            f.close()

        linesPerMeasures(line_measures, groups, dir, project)

        clearMeasures(line_measures, groups, head_titles)

    linesPerConfig(config_measures, labels, titles, colors, projects, numberOfVehicles, path)
