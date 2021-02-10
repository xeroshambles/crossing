import sys
import os
from math import sqrt
from multiprocessing import Process, Queue
from datetime import date
import importlib.util
import inpout
from config_batch import *
from reservation.traiettorie import Traiettorie

from sumolib import checkBinary

if __name__ == "__main__":
    """Main che avvia un certo numero di simulazioni in parallelo (in modalità manuale o automatica)"""

    dir = f"outputs_batch_{date.today().strftime('%d_%m_%Y')}"
    root = os.path.abspath(os.path.split(__file__)[0])
    path = os.path.join(root, dir)

    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except OSError:
            print(f"\nCreazione della cartella {path} fallita...")

    tempo_generazione = 43.2  # fissato
    celle_per_lato = 20  # per protocolli basati sulla suddivisione matriciale dell'incrocio
    secondi_di_sicurezza = 0.6

    for project in projects:

        try:
            module = importlib.import_module(".main", package=project)
        except Exception:
            print("\nImpossibile trovare il progetto...")
            sys.exit(0)

        print(f"\nEseguo progetto {project}...")

        if project == "reservation":
            print("\nCalcolo la matrice di celle a partire da tutte le traiettorie possibili...")
            traiettorie_matrice = Traiettorie.run(False, celle_per_lato)

        config_file = os.path.join(os.path.split(__file__)[0], project,
                                   "intersection.sumocfg")  # file di configurazione della simulazione

        choice = inpout.checkChoice(['d', 'D', 'g', 'G'],
                                       '\nVuoi una visualizzazione grafica o raccogliere dati? (g = grafica, '
                                       'd = dati): ',
                                       "\nUtilizzo la modalità dati come default...",
                                       '\nInserire un carattere tra d e g!',
                                    mode)

        sumoBinary = checkBinary('sumo') if choice in ['d', 'D'] else checkBinary('sumo-gui')

        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"] if choice in ['d', 'D'] else \
            [sumoBinary, "-c", config_file, "--time-to-teleport", "-1", "-S", "-Q"]

        if project == "reservation":
            sumoCmd.append("--step-length")
            sumoCmd.append("0.100")

        schema = ''
        if choice in ['g', 'G']:
            schema = inpout.checkChoice(['s', 'S', 'n', 'N'],
                                           '\nDesideri visualizzare le auto con uno schema di colori significativo? '
                                           '(s, n): ',
                                           "\nUtilizzo lo schema significativo come default...",
                                           '\nInserire un carattere tra s e n!', mode)

        diffSim = inpout.checkInput(4, f'\nInserire il numero di esecuzioni della simulazione: ',
                                       f'\nUtilizzo come default 4 run diverse...',
                                       '\nInserire un numero di simulazioni positivo!', mode,
                                       f'\nEseguo {diffSim} simulazioni differenti...', diffSim)

        labels_per_sims = []

        measures = {}

        measures['total_time'] = []
        measures['total_time'].append({'label': labels[0], 'color': colors[0], 'title': titles[0], 'values': []})
        measures['head_time'] = []
        measures['head_time'].append({'label': labels[1], 'color': colors[0], 'title': titles[1], 'values': []})
        measures['head_time'].append({'label': labels[2], 'color': colors[1], 'title': titles[2], 'values': []})
        measures['head_time'].append({'label': labels[3], 'color': colors[2], 'title': titles[3], 'values': []})
        measures['tail_time'] = []
        measures['tail_time'].append({'label': labels[4], 'color': colors[0], 'title': titles[4], 'values': []})
        measures['tail_time'].append({'label': labels[5], 'color': colors[1], 'title': titles[5], 'values': []})
        measures['tail_time'].append({'label': labels[6], 'color': colors[2], 'title': titles[6], 'values': []})
        measures['speed'] = []
        measures['speed'].append({'label': labels[7], 'color': colors[0], 'title': titles[7], 'values': []})
        measures['speed'].append({'label': labels[8], 'color': colors[1], 'title': titles[8], 'values': []})
        measures['tail_length'] = []
        measures['tail_length'].append({'label': labels[9], 'color': colors[0], 'title': titles[9], 'values': []})
        measures['tail_length'].append({'label': labels[10], 'color': colors[1], 'title': titles[10], 'values': []})
        measures['tail_length'].append({'label': labels[11], 'color': colors[2], 'title': titles[11], 'values': []})
        measures['stopped_vehicles'] = []
        measures['stopped_vehicles'].append({'label': labels[12], 'color': colors[0], 'title': titles[12],
                                             'values': []})
        measures['throughput'] = []
        measures['throughput'].append({'label': labels[13], 'color': colors[0], 'title': titles[13], 'values': []})

        dir = os.path.join(path, project)

        if not os.path.exists(dir):
            try:
                os.mkdir(dir)
            except OSError:
                print(f"\nCreazione della cartella {dir} fallita...")

        for i in range(0, diffSim):

            labels_per_sims.append(f'{numberOfVehicles[i]} veicoli')

            output_file = os.path.join(dir, f'batch_{i}.txt')
            f = open(output_file, "w")

            repeatSim = inpout.checkInput(10, f'\nInserire il numero di ripetizioni della simulazione {i}: ',
                                             f'\nUtilizzo come default 10 stesse run...',
                                             '\nInserire un numero di simulazioni positivo!', mode,
                                             f'\nEseguo {repeatSim} simulazioni identiche in parallelo...', repeatSim)

            numberOfVehicles[i] = inpout.checkInput(50, f'\nInserire il numero di veicoli nella simulazione {i}: ',
                                                       f'\nUtilizzo default ({50}) veicoli...',
                                                       '\nInserire un numero di veicoli positivo!', mode,
                                                       f'\nUtilizzo {numberOfVehicles[i]} veicoli...',
                                                    numberOfVehicles[i])

            procs = []
            queue = Queue()

            for j in range(0, repeatSim):
                if project == "reservation":
                    p = Process(target=module.run, args=(numberOfVehicles[i], schema, sumoCmd, tempo_generazione,
                                                         celle_per_lato, traiettorie_matrice, secondi_di_sicurezza,
                                                         dir, j, queue))
                elif project == "auction":
                    p = Process(target=module.run, args=(numberOfVehicles[i], schema, sumoCmd, False, True,
                                                         -1, dir, j, queue))
                else:
                    p = Process(target=module.run, args=(numberOfVehicles[i], schema, sumoCmd, dir,
                                                         j, queue))
                p.start()
                procs.append(p)

            for p in procs:
                p.join()

            totalTime = []
            meanHeadTime = []
            stDevHeadTime = []
            maxHeadTime = []
            meanTailTime = []
            stDevTailTime = []
            maxTailTime = []
            meanSpeed = []
            stDevSpeed = []
            meanTailLength = []
            stDevTailLength = []
            maxTailLength = []
            stoppedVehicles = []
            meanThroughput = []

            for j in range(0, repeatSim):
                ret = queue.get()

                inpout.writeMeasuresToFile(f, f'{i}:{j}', numberOfVehicles[i], ret)

                totalTime.append(ret[0])
                meanHeadTime.append(ret[1])
                stDevHeadTime.append(sqrt(ret[2]))
                maxHeadTime.append(ret[3])
                meanTailTime.append(ret[4])
                stDevTailTime.append(sqrt(ret[5]))
                maxTailTime.append(ret[6])
                meanSpeed.append(ret[7])
                stDevSpeed.append(sqrt(ret[8]))
                meanTailLength.append(ret[9])
                stDevTailLength.append(sqrt(ret[10]))
                maxTailLength.append(ret[11])
                stoppedVehicles.append(ret[12])
                meanThroughput.append(ret[13])

            measures['total_time'][0]['values'].append(round(sum(totalTime) / len(totalTime), 2))
            measures['head_time'][0]['values'].append(round(sum(meanHeadTime) / len(meanHeadTime), 2))
            measures['head_time'][1]['values'].append(round(sum(stDevHeadTime) / len(stDevHeadTime), 2))
            measures['head_time'][2]['values'].append(round(sum(maxHeadTime) / len(maxHeadTime), 2))
            measures['tail_time'][0]['values'].append(round(sum(meanTailTime) / len(meanTailTime), 2))
            measures['tail_time'][1]['values'].append(round(sum(stDevTailTime) / len(stDevTailTime), 2))
            measures['tail_time'][2]['values'].append(round(sum(maxTailTime) / len(maxTailTime), 2))
            measures['speed'][0]['values'].append(round(sum(meanSpeed) / len(meanSpeed), 2))
            measures['speed'][1]['values'].append(round(sum(stDevSpeed) / len(stDevSpeed), 2))
            measures['tail_length'][0]['values'].append(round(sum(meanTailLength) / len(meanTailLength), 2))
            measures['tail_length'][1]['values'].append(round(sum(stDevTailLength) / len(stDevTailLength), 2))
            measures['tail_length'][2]['values'].append(max(maxTailLength))
            measures['stopped_vehicles'][0]['values'].append(round(sum(stoppedVehicles) / len(stoppedVehicles), 2))
            measures['throughput'][0]['values'].append(round(sum(meanThroughput) / len(meanThroughput), 2))

            f.close()

        values = []
        lab = []
        ttl = []
        col = []
        grp = []

        for k in measures:
            grp.append(len(measures[k]))
            ttl.append(k)
            for i in range(0, len(measures[k])):
                values.append(measures[k][i]['values'])
                lab.append(measures[k][i]['label'])
                col.append(measures[k][i]['color'])

        inpout.linesPerMeasures(values, lab, ttl, col, grp, labels_per_sims, dir, project)
