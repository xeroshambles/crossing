import sys
import os
from math import sqrt
from multiprocessing import Pool
import output
import importlib.util

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Dichiarare la variabile d'ambiente 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa


def main(project):
    """Main che avvia un certo numero di simulazioni in parallelo (in modalità manuale o automatica)"""

    mode = 'auto'  # stringa che imposta la modalità automatica per le simulazioni
    repeatSim = 10  # numero di volte per cui la stessa simulazione deve essere ripetuta
    numberOfVehicles = [50, 100, 200, 500]  # lista contenente il numero di veicoli per ogni simulazione diversa
    diffSim = len(numberOfVehicles)  # numero di simulazioni diverse che devono essere eseguite
    period = 10  # tempo di valutazione del throughput del sistema incrocio

    try:
        module = importlib.import_module(".main", package=project)
    except Exception:
        print("\nImpossibile trovare il progetto...")
        sys.exit(0)

    config_file = os.path.join(os.path.split(__file__)[0], project,
                               "intersection.sumocfg")  # file di configurazione della simulazione
    choice = ''
    schema = 'n'
    default = ['d', 'dati']
    labels_per_sims = []
    while choice not in ['d', 'D', 'g', 'G']:
        if mode == 'auto':
            choice = default[0]
        else:
            choice = input('\nVuoi raccogliere dati o avere una visualizzazione grafica? (d = dati, g = grafica): ')
        if choice not in ['d', 'D', 'g', 'G']:
            choice = default[0]
            print(f'\nUtilizzo la configurazione di default ({default[1]})')
    if choice in ['d', 'D']:
        sumoBinary = checkBinary('sumo')
        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"]
    else:
        sumoBinary = checkBinary('sumo-gui')
        sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1", "-S", "-Q"]
        choice = ''
        while choice not in ['s', 'S', 'n', 'N']:
            choice = input('\nDesideri visualizzare le auto con uno schema di colori significativo? (s, n): ')
            if choice not in ['s', 'S', 'n', 'N']:
                print('\nInserire un carattere tra s e n!')
        schema = choice
    if mode != 'auto':
        diffSim = module.checkInput(4, f'\nInserire il numero di esecuzioni della simulazione: ',
                                    f'\nUtilizzo default ({4}) numero di run diverse...',
                                    '\nInserire un numero di simulazioni positivo!')
    else:
        print(f'\nEseguo {diffSim} simulazioni differenti...')

    measures = {}
    measures['total_time'] = []
    measures['total_time'].append({'label': 'Tempo totale (s)', 'color': '#E6390D', 'title': 'total_time',
                                   'values': []})
    measures['head_time'] = []
    measures['head_time'].append(
        {'label': 'Tempo medio in testa (s)', 'color': '#E6390D', 'title': 'mean_head_time', 'values': []})
    measures['head_time'].append(
        {'label': 'Deviazione standard tempo in testa (s)', 'color': '#0D14E6', 'title': 'st_dev_head_time',
         'values': []})
    measures['head_time'].append(
        {'label': 'Massimo tempo in testa (s)', 'color': '#10E60D', 'title': 'max_head_time', 'values': []})
    measures['tail_time'] = []
    measures['tail_time'].append(
        {'label': 'Tempo medio in coda (s)', 'color': '#E6390D', 'title': 'mean_tail_time', 'values': []})
    measures['tail_time'].append(
        {'label': 'Deviazione standard tempo in coda (s)', 'color': '#0D14E6', 'title': 'st_dev_tail_time',
         'values': []})
    measures['tail_time'].append(
        {'label': 'Massimo tempo in coda (s)', 'color': '#10E60D', 'title': 'max_tail_time', 'values': []})
    measures['speed'] = []
    measures['speed'].append(
        {'label': 'Velocità media (m/s)', 'color': '#E6390D', 'title': 'mean_speed', 'values': []})
    measures['speed'].append(
        {'label': 'Deviazione standard velocità (m/s)', 'color': '#0D14E6', 'title': 'st_dev_speed',
         'values': []})
    measures['speed'].append(
        {'label': 'Massima velocità (m/s)', 'color': '#10E60D', 'title': 'max_speed', 'values': []})
    measures['tail_length'] = []
    measures['tail_length'].append(
        {'label': 'Lunghezza media delle code', 'color': '#E6390D', 'title': 'mean_tail_length', 'values': []})
    measures['tail_length'].append(
        {'label': 'Deviazione standard lunghezza delle code', 'color': '#0D14E6', 'title': 'st_dev_tail_length',
         'values': []})
    measures['tail_length'].append(
        {'label': 'Massima lunghezza delle code', 'color': '#10E60D', 'title': 'max_tail_length', 'values': []})
    measures['stopped_vehicles'] = []
    measures['stopped_vehicles'].append({'label': 'Veicoli fermi', 'color': '#E6390D', 'title': 'stopped_vehicles',
                                         'values': []})
    measures['throughput'] = []
    measures['throughput'].append({'label': f'Throughput medio (% veicoli / {period} step', 'color': '#E6390D',
                                   'title': 'mean_throughput', 'values': []})

    root = os.path.abspath(os.path.split(__file__)[0])
    path = os.path.join(root, "output_batch_" + project)
    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except OSError:
            print("Creation of the directory %s failed..." % path)

    for i in range(1, diffSim + 1):
        labels_per_sims.append(f'Sim. {i} ({numberOfVehicles[i - 1]} veicoli)')
        output_file = os.path.join(path, f'batch_{i}.txt')
        f = open(output_file, "w")
        if mode != 'auto':
            repeatSim = module.checkInput(10, f'\nInserire il numero di ripetizioni della simulazione {i}: ',
                                          f'\nUtilizzo default ({10}) numero di stesse run...',
                                          '\nInserire un numero di simulazioni positivo!')
        else:
            print(f'\nEseguo {repeatSim} simulazioni identiche in parallelo...')
        if mode != 'auto':
            numberOfVehicles[i - 1] = module.checkInput(50, f'\nInserire il numero di veicoli nella simulazione {i}: ',
                                                        f'\nUtilizzo default ({50}) veicoli...',
                                                        '\nInserire un numero di veicoli positivo!')
        else:
            print(f'\nUtilizzo {numberOfVehicles[i - 1]} veicoli...')
        pool = Pool(processes=repeatSim)
        pool_arr = []
        for j in range(0, repeatSim):
            pool_arr.append(pool.apply_async(module.run, (numberOfVehicles[i - 1], schema, sumoCmd)))
        pool.close()
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
            ret = pool_arr[j].get()

            output.writeMeasuresToFile(f, f'{i}:{j + 1}', numberOfVehicles[i - 1], ret[0], ret[1], ret[2], ret[3],
                                       ret[4], ret[5], ret[6], ret[7], ret[8], ret[9], ret[10], ret[11], ret[12],
                                       ret[13], ret[14])

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
        measures['tail_length'][2]['values'].append(round(sum(maxTailTimeArr) / len(maxTailTimeArr), 2))
        measures['stopped_vehicles'][0]['values'].append(round(sum(nStoppedVehiclesArr) / len(nStoppedVehiclesArr), 2))
        measures['throughput'][0]['values'].append(round(sum(meanThroughputArr) / len(meanThroughputArr), 2))

        f.close()
    # print(f"Throughputs: {measures['throughput'][0]['values']}")
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

    output.histPerMeasures(values, labels, titles, colors, arr, labels_per_sims, path)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        project = sys.argv[1]
        if project:
            main(project)
    else:
        print("\nInserire un nome di progetto da eseguire...")