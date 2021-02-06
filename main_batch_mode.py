import sys
import os
from math import sqrt
from multiprocessing import Process, Queue
import output
import importlib.util

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Dichiarare la variabile d'ambiente 'SUMO_HOME'")

from sumolib import checkBinary, miscutils  # noqa
import traci  # noqa

from reservation.traiettorie import Traiettorie


def main(project):
    """Main che avvia un certo numero di simulazioni in parallelo (in modalità manuale o automatica)"""

    mode = 'auto'  # stringa che imposta la modalità automatica per le simulazioni
    repeatSim = 10  # numero di volte per cui la stessa simulazione deve essere ripetuta
    numberOfVehicles = [50, 100, 200, 400]  # lista contenente il numero di veicoli per ogni simulazione diversa
    diffSim = len(numberOfVehicles)  # numero di simulazioni diverse che devono essere eseguite
    period = 10  # tempo di valutazione del throughput del sistema incrocio

    try:
        module = importlib.import_module(".main", package=project)
    except Exception:
        print("\nImpossibile trovare il progetto...")
        sys.exit(0)

    config_file = os.path.join(os.path.split(__file__)[0], project,
                               "intersection.sumocfg")  # file di configurazione della simulazione

    choice = module.checkChoice(['d', 'D', 'g', 'G'],
                         '\nVuoi una visualizzazione grafica o raccogliere dati? (g = grafica, d = dati): ',
                         "\nUtilizzo la modalità grafica come default...", '\nInserire un carattere tra d e g!', mode)

    sumoBinary = checkBinary('sumo') if choice in ['d', 'D'] else checkBinary('sumo-gui')

    sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"] if choice in ['d', 'D'] else \
        [sumoBinary, "-c", config_file, "--time-to-teleport", "-1", "-S", "-Q"]

    if project == "reservation":
        sumoCmd.append("--step-length")
        sumoCmd.append("0.025")

    schema = module.checkChoice(['s', 'S', 'n', 'N'],
                         '\nDesideri visualizzare le auto con uno schema di colori significativo? (s, n): ',
                         "\nUtilizzo lo schema significativo come default...",
                         '\nInserire un carattere tra s e n!', mode)

    diffSim = module.checkInput(4, f'\nInserire il numero di esecuzioni della simulazione: ',
                                f'\nUtilizzo come default 4 run diverse...',
                                '\nInserire un numero di simulazioni positivo!', mode,
                                f'\nEseguo {diffSim} simulazioni differenti...', diffSim)

    labels_per_sims = []

    measures = {}
    measures['total_time'] = []
    measures['total_time'].append({'label': 'Tempo totale (s)', 'color': '#DF1515', 'title': 'total_time',
                                   'values': []})
    measures['head_time'] = []
    measures['head_time'].append(
        {'label': 'Tempo medio in testa (s)', 'color': '#DF1515', 'title': 'mean_head_time', 'values': []})
    measures['head_time'].append(
        {'label': 'Deviazione standard tempo in testa (s)', 'color': '#1524DF', 'title': 'st_dev_head_time',
         'values': []})
    measures['head_time'].append(
        {'label': 'Massimo tempo in testa (s)', 'color': '#15DF1E', 'title': 'max_head_time', 'values': []})
    measures['tail_time'] = []
    measures['tail_time'].append(
        {'label': 'Tempo medio in coda (s)', 'color': '#DF1515', 'title': 'mean_tail_time', 'values': []})
    measures['tail_time'].append(
        {'label': 'Deviazione standard tempo in coda (s)', 'color': '#1524DF', 'title': 'st_dev_tail_time',
         'values': []})
    measures['tail_time'].append(
        {'label': 'Massimo tempo in coda (s)', 'color': '#15DF1E', 'title': 'max_tail_time', 'values': []})
    measures['speed'] = []
    measures['speed'].append(
        {'label': 'Velocità media (m/s)', 'color': '#DF1515', 'title': 'mean_speed', 'values': []})
    measures['speed'].append(
        {'label': 'Deviazione standard velocità (m/s)', 'color': '#1524DF', 'title': 'st_dev_speed',
         'values': []})
    measures['speed'].append(
        {'label': 'Massima velocità (m/s)', 'color': '#15DF1E', 'title': 'max_speed', 'values': []})
    measures['tail_length'] = []
    measures['tail_length'].append(
        {'label': 'Lunghezza media delle code', 'color': '#DF1515', 'title': 'mean_tail_length', 'values': []})
    measures['tail_length'].append(
        {'label': 'Deviazione standard lunghezza delle code', 'color': '#1524DF', 'title': 'st_dev_tail_length',
         'values': []})
    measures['tail_length'].append(
        {'label': 'Massima lunghezza delle code', 'color': '#15DF1E', 'title': 'max_tail_length', 'values': []})
    measures['stopped_vehicles'] = []
    measures['stopped_vehicles'].append({'label': 'Veicoli fermi', 'color': '#DF1515', 'title': 'stopped_vehicles',
                                         'values': []})
    measures['throughput'] = []
    measures['throughput'].append({'label': f'Throughput medio (% veicoli / {period} step', 'color': '#DF1515',
                                   'title': 'mean_throughput', 'values': []})

    dir = "output_batch_" + project

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

    if project == "reservation":
        print("\nCalcolo la matrice di celle a partire da tutte le traiettorie possibili...")
        traiettorie_matrice = Traiettorie.run(False, celle_per_lato)

    for i in range(0, diffSim):
        labels_per_sims.append(f'Sim. {i} ({numberOfVehicles[i]} veicoli)')

        output_file = os.path.join(path, f'batch_{i}.txt')
        f = open(output_file, "w")

        repeatSim = module.checkInput(10, f'\nInserire il numero di ripetizioni della simulazione {i}: ',
                                      f'\nUtilizzo come default 10 stesse run...',
                                      '\nInserire un numero di simulazioni positivo!', mode,
                                      f'\nEseguo {repeatSim} simulazioni identiche in parallelo...', repeatSim)

        numberOfVehicles[i] = module.checkInput(50, f'\nInserire il numero di veicoli nella simulazione {i}: ',
                                                f'\nUtilizzo default ({50}) veicoli...',
                                                '\nInserire un numero di veicoli positivo!', mode,
                                                f'\nUtilizzo {numberOfVehicles[i]} veicoli...', numberOfVehicles[i])

        procs = []
        queue = Queue()

        for j in range(0, repeatSim):
            if project == "reservation":
                p = Process(target=module.run, args=(numberOfVehicles[i], schema, sumoCmd, tempo_generazione,
                                                     celle_per_lato, traiettorie_matrice, secondi_di_sicurezza,
                                                     path, j, queue))
            elif project == "auctions":
                p = Process(target=module.run, args=(numberOfVehicles[i - 1], schema, sumoCmd, True, True,
                                                     1, path, j, queue))
            else:
                p = Process(target=module.run, args=(numberOfVehicles[i - 1], schema, sumoCmd, path,
                                                     j, queue))
            p.start()
            procs.append(p)
        for p in procs:
            p.join()

        totalTimeArr = []
        meanHeadTimeArr = []
        varHeadTimeArr = []
        stDevHeadTimeArr = []
        maxHeadTimeArr = []
        meanTailTimeArr = []
        varTailTimeArr = []
        stDevTailTimeArr = []
        maxTailTimeArr = []
        meanSpeedArr = []
        varSpeedArr = []
        stDevSpeedArr = []
        maxSpeedArr = []
        meanTailLengthArr = []
        varTailLengthArr = []
        stDevTailLengthArr = []
        maxTailLengthArr = []
        nStoppedVehiclesArr = []
        meanThroughputArr = []

        for j in range(0, repeatSim):

            ret = queue.get()

            output.writeMeasuresToFile(f, f'{i}:{j}', numberOfVehicles[i], ret)

            totalTimeArr.append(ret[0])
            meanHeadTimeArr.append(ret[1])
            varHeadTimeArr.append(ret[2])
            stDevHeadTimeArr.append(sqrt(ret[2]))
            maxHeadTimeArr.append(ret[3])
            meanTailTimeArr.append(ret[4])
            varTailTimeArr.append(ret[5])
            stDevTailTimeArr.append(sqrt(ret[5]))
            maxTailTimeArr.append(ret[6])
            meanSpeedArr.append(ret[7])
            varSpeedArr.append(ret[8])
            stDevSpeedArr.append(ret[8])
            maxSpeedArr.append(ret[9])
            meanTailLengthArr.append(ret[10])
            varTailLengthArr.append(ret[11])
            stDevTailLengthArr.append(ret[11])
            maxTailLengthArr.append(ret[12])
            nStoppedVehiclesArr.append(ret[13])
            meanThroughputArr.append(ret[14])

        measures['total_time'][0]['values'].append(round(sum(totalTimeArr) / len(totalTimeArr), 2))
        measures['head_time'][0]['values'].append(round(sum(meanHeadTimeArr) / len(meanHeadTimeArr), 2))
        measures['head_time'][1]['values'].append(round(sum(stDevHeadTimeArr) / len(stDevHeadTimeArr), 2))
        measures['head_time'][2]['values'].append(round(sum(maxHeadTimeArr) / len(maxHeadTimeArr), 2))
        measures['tail_time'][0]['values'].append(round(sum(meanTailTimeArr) / len(meanTailTimeArr), 2))
        measures['tail_time'][1]['values'].append(round(sum(stDevTailTimeArr) / len(stDevTailTimeArr), 2))
        measures['tail_time'][2]['values'].append(round(sum(maxTailTimeArr) / len(maxTailTimeArr), 2))
        measures['speed'][0]['values'].append(round(sum(meanSpeedArr) / len(meanSpeedArr), 2))
        measures['speed'][1]['values'].append(round(sum(stDevSpeedArr) / len(stDevSpeedArr), 2))
        measures['speed'][2]['values'].append(round(sum(maxSpeedArr) / len(maxSpeedArr), 2))
        measures['tail_length'][0]['values'].append(round(sum(meanTailLengthArr) / len(meanTailLengthArr), 2))
        measures['tail_length'][1]['values'].append(round(sum(stDevTailLengthArr) / len(stDevTailLengthArr), 2))
        measures['tail_length'][2]['values'].append(round(sum(maxTailLengthArr) / len(maxTailLengthArr), 2))
        measures['stopped_vehicles'][0]['values'].append(round(sum(nStoppedVehiclesArr) / len(nStoppedVehiclesArr), 2))
        measures['throughput'][0]['values'].append(round(sum(meanThroughputArr) / len(meanThroughputArr), 2))

        f.close()

    values = []
    labels = []
    titles = []
    colors = []
    arr = []
    for k in measures:
        arr.append(len(measures[k]))
        titles.append(k)
        for i in range(0, len(measures[k])):
            values.append(measures[k][i]['values'])
            labels.append(measures[k][i]['label'])
            colors.append(measures[k][i]['color'])

    output.histPerMeasures(values, labels, titles, colors, arr, labels_per_sims, path, project)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        project = sys.argv[1]
        if project:
            main(project)
    else:
        print("\nInserire un nome di progetto da eseguire...")
