# Variabili di configurazione comuni

mode = 'auto'  # stringa che imposta la modalità automatica ('auto') o manuale (qualsiasi stringa) per le simulazioni
# Numero di veicoli: [[50, 50, 50, 50], [100, 100, 100, 100], [150, 150, 150, 150], [200, 200, 200, 200]]
numberOfVehicles = [[50, 100, 150, 200]]
# lista contenente il numero di veicoli generati per ogni simulazione
stepsSpawn = 200  # numero di step entro cui generare tutti i veicoli della simulazione
numberOfSteps = 200  # numero di step entro cui ogni simulazione deve terminare
# Semi: [9001, 2, 350, 39, 78, 567, 1209, 465, 21, 987]
seeds = [9001, 2, 350, 39, 78, 567, 1209, 465, 21, 987]  # semi iniziali delle simulazioni
repeatSim = len(seeds)  # numero di volte per cui la stessa simulazione deve essere ripetuta
diffSim = len(numberOfVehicles)  # numero di simulazioni diverse che devono essere eseguite


config_file = "intersection.sumocfg"  # file di configurazione della simulazione
output_redirection = False  # variabile che redireziona l'output su file (True) o su terminale (False)
tempo_generazione = 50   # tempo di generazione dei veicoli
celle_per_lato = 20  # numero di celle per lato nel caso della reservation
secondi_di_sicurezza = 0.6  # soglia tra veicoli per la reservation
simulationMode = True  # asta competitiva (True) o cooperativa (False)
instantPay = True  # i veicoli pagano subito (True) o pagano solo i vincitori delle aste (False)
dimensionOfGroups = -1  # dimensione del gruppo degli sponsor (da 1 a 7 o -1 per una dimensione variabile)
m = 60
spawn_balancing = [33, 33, 34] #spawn dx, spawn c, spawn sx
# Variabili di configurazione per ogni simulazione (incrocio singolo)

# Progetti: ["classic_tls", "classic_precedence", "reservation", "precedence_with_auction_comp",
# "multi_auction_classic_tls"]
projects = ["classic_precedence", "precedence_with_auction_comp", "reservation", "adaptive"]
junction_id = 7  # id dell'incrocio
lanes = ['e02_07_0', 'e02_07_1', 'e02_07_2', 'e07_02_0', 'e07_02_1', 'e07_02_2',
         'e08_07_0', 'e08_07_1', 'e08_07_2', 'e07_08_0', 'e07_08_1', 'e07_08_2',
         'e12_07_0', 'e12_07_1', 'e12_07_2', 'e07_12_0', 'e07_12_1', 'e07_12_2',
         'e06_07_0', 'e06_07_1', 'e06_07_2', 'e07_06_0', 'e07_06_1', 'e07_06_2']  # lista dei nomi delle lane
lanes_ids = [0, 1, 2]  # lista degli id delle lanes nell'incrocio
node_ids = [2, 8, 12, 6]  # lista degli id dei nodi di partenza e di arrivo nell'incrocio

labels = ['Tempo totale (s)', 'Tempo medio in testa (s)', 'Deviazione standard tempo in testa (s)',
          'Massimo tempo in testa (s)', 'Tempo medio in coda (s)', 'Deviazione standard tempo in coda (s)',
          'Massimo tempo in coda (s)', 'Velocità media (m/s)', 'Deviazione standard velocità (m/s)',
          'Lunghezza media delle code', 'Deviazione standard lunghezza delle code',
          'Massima lunghezza delle code', 'Veicoli fermi', 'Throughput medio']

colors = ['#DF1515', '#1524DF', '#15DF1E', '#FCFF33']

head_titles = ['total_time', 'head_time', 'tail_time', 'speed', 'tail_length', 'stopped_vehicles', 'throughput']

titles = ['total_time', 'mean_head_time', 'st_dev_head_time', 'max_head_time', 'mean_tail_time', 'st_dev_tail_time',
          'max_tail_time', 'mean_speed', 'st_dev_mean_speed', 'mean_tail_length', 'st_dev_tail_length',
          'max_tail_length', 'stopped_vehicles', 'throughput']

projects_labels = []

for project in projects:
    if project == "classic_tls":
        projects_labels.append("Semaforo")
    elif project == "classic_precedence":
        projects_labels.append("Precedenza")
    elif project == "reservation":
        projects_labels.append("Prenotazione")
    if project == "precedence_with_auction_comp":
        projects_labels.append("Precedenza + asta competitiva")
    if project == "adaptive":
        projects_labels.append("Adattativo")

x_labels = [sum(vehicles) / len(vehicles) for vehicles in numberOfVehicles]

groups = [1, 3, 3, 2, 3, 1, 1]

labels_per_sims = []

group_measures = {}

group_measures['sims'] = [str(vehs) for vehs in numberOfVehicles]

i = 0
j = 0

for title in head_titles:
    k = 0
    group_measures[title] = []
    while k < groups[i]:
        group_measures[title].append({'label': labels[j], 'color': colors[k], 'title': titles[j], 'values': []})
        j += 1
        k += 1
    i += 1

single_measures = {}

for vehs in numberOfVehicles:
    single_measures[str(vehs)] = {}
    for i in range(0, len(labels)):
        single_measures[str(vehs)][labels[i]] = []
        for j in range(0, len(projects)):
            single_measures[str(vehs)][labels[i]].append({'project': projects[j], 'color': colors[j], 'values': []})
