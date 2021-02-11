import sys
import os
import importlib
from datetime import date
from multiprocessing import Queue
import inpout
from config_no_batch import *
from reservation.traiettorie import Traiettorie

from sumolib import checkBinary

if __name__ == "__main__":
    """Main che avvia un certo numero di simulazioni in serie"""

    tempo_generazione = 43.2  # fissato
    celle_per_lato = 20  # per protocolli basati sulla suddivisione matriciale dell'incrocio
    secondi_di_sicurezza = 0.6

    project = inpout.checkChoice(['classic_tls', 'classic_precedence', 'reservation', 'auction'],
                                 '\nInserire il nome di un progetto (classic_tls, classic_precedence, '
                                 'reservation, auction): ', '\nUtilizzo il semaforo classico come '
                                                            'default...', '\nProgetto non esistente')

    if project == "reservation":
        print("\nCalcolo la matrice di celle a partire da tutte le traiettorie possibili...")
        traiettorie_matrice = Traiettorie.run(False, celle_per_lato)

    try:
        module = importlib.import_module(".main", package=project)
    except Exception:
        print('\nImpossibile trovare il progetto...')
        sys.exit(-1)

    config_file = os.path.join(os.path.split(__file__)[0], project, "intersection.sumocfg")  # file di configurazione
    # della simulazione

    choice = inpout.checkChoice(['g', 'G', 'd', 'D'],
                                '\nVuoi una visualizzazione grafica o raccogliere dati? (g = grafica, d = dati): ',
                                "\nUtilizzo la modalità grafica come default...",
                                '\nInserire un carattere tra d e g!')

    sumoBinary = checkBinary('sumo') if choice in ['d', 'D'] else checkBinary('sumo-gui')

    sumoCmd = [sumoBinary, "-c", config_file, "--time-to-teleport", "-1"] if choice in ['d', 'D'] else \
        [sumoBinary, "-c", config_file, "--time-to-teleport", "-1", "-S", "-Q"]

    if project == "reservation":
        sumoCmd.append("--step-length")
        sumoCmd.append("0.100")

    if choice in ['g', 'G']:
        schema = inpout.checkChoice(['s', 'S', 'n', 'N'],
                                    '\nDesideri visualizzare le auto con uno schema di colori significativo? '
                                    '(s, n): ',
                                    "\nUtilizzo lo schema significativo come default...",
                                    '\nInserire un carattere tra s e n!')
    else:
        schema = ''

    labels_per_sims = []

    numberOfSimulations = inpout.checkInput(1, '\nInserire il numero di simulazioni: ',
                                            f'\nUtilizzo una simulazione come default...',
                                            '\nInserire un numero di simulazioni positivo!')

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

    dir = "output_" + project + '_' + date.today().strftime('%d_%m_%Y')

    root = os.path.abspath(os.path.split(__file__)[0])
    path = os.path.join(root, dir)
    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except OSError:
            print(f"\nCreazione della cartella {path} fallita...")
            sys.exit(-1)

    output_file = os.path.join(path, f'no_batch.txt')
    f = open(output_file, "w")

    queue = Queue()

    for i in range(0, numberOfSimulations):

        numberOfVehicles = inpout.checkInput(50, f'\nInserire il numero di veicoli nella simulazione {i}: ',
                                             f'\nUtilizzo la simulazione {i} con 50 veicoli di default...',
                                             '\nInserire un numero di veicoli positivo!')

        labels_per_sims.append(f'{numberOfVehicles} veicoli')

        if project == "reservation":
            module.run(numberOfVehicles, schema, sumoCmd, tempo_generazione, celle_per_lato, traiettorie_matrice,
                       secondi_di_sicurezza, path, i, queue)

        elif project == "auction":
            choice = inpout.checkChoice(['s', 'S', 'n', 'N'],
                                        f'\nNella simulazione {i} si vuole un approccio competitivo o cooperativo? '
                                        f'(s = competitivo, n = cooperativo): ',
                                        '\nUtilizzo la modalità competitiva come default...',
                                        '\nInserire un carattere tra s e n!')

            simulationMode = True if choice in ['s', 'S'] else False

            choice = inpout.checkChoice(['s', 'S', 'n', 'N'],
                                        f'\nI veicoli nella simulazione {i} devono pagare subito? Altrimenti pagano '
                                        f'solo i vincitori delle aste (s = si, n = no): ',
                                        '\nUtilizzo il pagamento immediato come default...',
                                        '\nInserire un carattere tra s e n!')

            instantPay = True if choice in ['s', 'S'] else False

            choice = inpout.checkChoice([str(j) for j in range(1, 8)] + ['-1'],
                                        '\nQuale dimensione deve avere il numero di veicoli considerato? '
                                        'I gruppi possono avere una dimensione che va da 1 a 7, se si inserisce -1 '
                                        'si usa un numero di veicoli proporzionale: ',
                                        '\nUtilizzo come gruppo un numero di veicoli pari a 1...',
                                        '\nInserire un numero compreso tra 1 e 7 oppure -1! '
                                        )

            dimensionOfGroups = int(choice)

            module.run(numberOfVehicles, schema, sumoCmd, simulationMode, instantPay, dimensionOfGroups, path, i, queue)

        else:
            module.run(numberOfVehicles, schema, sumoCmd, path, i, queue)

        ret = queue.get()

        inpout.writeMeasuresToFile(f, i, numberOfVehicles, ret)

        measures['total_time'][0]['values'].append(round(ret[0], 2))
        measures['head_time'][0]['values'].append(round(ret[1], 2))
        measures['head_time'][1]['values'].append(round(ret[2], 2))
        measures['head_time'][2]['values'].append(round(ret[3], 2))
        measures['tail_time'][0]['values'].append(round(ret[4], 2))
        measures['tail_time'][1]['values'].append(round(ret[5], 2))
        measures['tail_time'][2]['values'].append(round(ret[6], 2))
        measures['speed'][0]['values'].append(round(ret[7], 2))
        measures['speed'][1]['values'].append(round(ret[8], 2))
        measures['tail_length'][0]['values'].append(round(ret[9], 2))
        measures['tail_length'][1]['values'].append(round(ret[10], 2))
        measures['tail_length'][2]['values'].append(round(ret[11], 2))
        measures['stopped_vehicles'][0]['values'].append(round(ret[12], 2))
        measures['throughput'][0]['values'].append(round(ret[13], 2))

    f.close()

    values = []
    labels = []
    titles = []
    colors = []
    groups = []
    for k in measures:
        groups.append(len(measures[k]))
        titles.append(k)
        for i in range(0, len(measures[k])):
            values.append(measures[k][i]['values'])
            labels.append(measures[k][i]['label'])
            colors.append(measures[k][i]['color'])

    inpout.linesPerMeasures(values, labels, titles, colors, groups, labels_per_sims, path)
