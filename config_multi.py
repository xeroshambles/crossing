# Variabili di configurazione comuni

mode = 'auto'  # stringa che imposta la modalità automatica ('auto') o manuale (qualsiasi stringa) per le simulazioni
# Numero di veicoli: [[25, 25, 25, 25], [50, 50, 50, 50], [75, 75, 75, 75], [100, 100, 100, 100]]
numberOfVehicles = [[25, 25, 25, 25], [50, 50, 50, 50], [75, 75, 75, 75], [100, 100, 100, 100]]
# lista contenente il numero di veicoli generati per ogni simulazione
# Percentuali di veicoli deviati sotto le quali considerare valida una simulazione:
# [0.38, 0.49, 0.55, 0.57] (precedenze esterne)
# [0.38, 0.48, 0.51, 0.51] (precedenze interne o precedenze + aste competitive)
# [0.38, 0.49, 0.56, 0.61] (precedenze + prenotazioni)
divertedPercents = [0.38, 0.49, 0.56, 0.61]
stepsSpawn = 100  # numero di step entro cui generare tutti i veicoli della simulazione
numberOfSteps = stepsSpawn + 100  # numero di step entro cui ogni simulazione deve terminare
# (sempre maggiore di stepsSpawn)
# Semi: [9001, 2, 350, 39, 78, 567, 1209, 465, 21, 987]
seeds = [9001, 2, 350, 39, 78, 567, 1209, 465, 21, 987]  # semi iniziali delle simulazioni
repeatSim = len(seeds)  # numero di volte per cui la stessa simulazione deve essere ripetuta
diffSim = len(numberOfVehicles)  # numero di simulazioni diverse che devono essere eseguite

configFile = "intersection.sumocfg"  # file di configurazione della simulazione
outputRedirection = True  # variabile che redireziona l'output su file (True) o su terminale (False)
cellsPerSide = 20  # numero di celle per lato nel caso della reservation
securitySecs = 0.6  # soglia tra veicoli per la reservation
simulationMode = True  # asta competitiva (True) o cooperativa (False)
instantPay = True  # i veicoli pagano subito (True) o pagano solo i vincitori delle aste (False)
dimensionOfGroups = 5  # dimensione del gruppo degli sponsor (da 1 a 7 o -1 per una dimensione variabile)

# Variabili di configurazione per ogni simulazione (più incroci)

# Progetti:
# ["multi_classic_tls_classic_precedence", "multi_classic_precedence",
# "multi_reservation_classic_precedence", "multi_comp_auction_classic_precedence",
# "multi_coop_auction_classic_precedence"]
# ["multi_classic_precedence_classic_tls", "multi_classic_precedence"
# "multi_classic_precedence_reservation", "multi_classic_precedence_comp_auction",
# "multi_classic_precedence_coop_auction"]
# ["multi_classic_precedence", "multi_comp_auction_classic_precedence", "multi_classic_precedence_comp_auction",
# "multi_comp_auction"]
# ["multi_classic_precedence", "multi_coop_auction_classic_precedence", "multi_classic_precedence_coop_auction",
# "multi_coop_auction"]
projects_multi = ["multi_classic_precedence", "multi_classic_precedence_reservation",
                  "multi_reservation_classic_precedence", "multi_classic_precedence_comp_auction",
                  "multi_comp_auction_classic_precedence", "multi_reservation"]
external_north_junctions_ids = [26, 27, 28, 29, 30]
external_east_junctions_ids = [55, 60, 65, 70, 75]
external_south_junctions_ids = [46, 47, 48, 49, 50]
external_west_junctions_ids = [51, 56, 61, 66, 71]
vertex_junctions_ids = [1, 5, 21, 25]  # id degli incroci ai vertici
lateral_junctions_ids = [2, 3, 4, 6, 10, 11, 15, 16, 20, 22, 23, 24]  # id degli incroci laterali
central_junctions_ids = [7, 8, 9, 12, 13, 14, 17, 18, 19]  # id degli incroci centrali
routeMode = True  # generazione delle route dei veicoli in modo statico (True) o dinamico (False)

markers = ['s', '^', 'o', 'D', 'P', '*']

labels_multi = ['Mean trip time (s)', 'Standard deviation trip time (s)',
                'Max trip time (s)', 'Mean leader time (s)',
                'Standard deviation leader time (s)', 'Max leader time (s)', 'Mean tail time (s)',
                'Standard deviation tail time (s)', 'Max tail time (s)', 'Mean speed (m/s)',
                'Standard deviation speed (m/s)', 'Mean tails length',
                'Standard deviation tails length', 'Max tails length', 'Mean throughput',
                'Mean diverted vehicles', 'Mean tails length (all crossings)',
                'Standard deviation tails length (all crossings)',
                'Max tails length (all crossings)', 'Mean throughput (all crossings)']

colors_multi = ['#DF1515', '#1524DF', '#15DF1E', '#FCFF33', 'FF33E6', '#33FFE3']

head_titles_multi = ['trip_time', 'head_time', 'tail_time', 'speed', 'tail_length', 'throughput', 'diverted_vehicles',
                     'tail_lengths', 'throughputs']

titles_multi = ['mean_trip_time', 'st_dev_trip_time', 'max_trip_time', 'mean_head_time', 'st_dev_head_time',
                'max_head_time', 'mean_tail_time', 'st_dev_tail_time', 'max_tail_time', 'mean_speed',
                'st_dev_mean_speed', 'mean_tail_length', 'st_dev_tail_length', 'max_tail_length',
                'mean_throughput', 'mean_diverted_vehicles', 'mean_tail_length_all', 'st_dev_tail_length_all',
                'max_tail_length_all', 'mean_throughput_all']

groups_multi = [3, 3, 3, 2, 3, 1, 1, 3, 1]

projects_labels_multi = []

for project in projects_multi:
    if project == "multi_classic_tls_classic_precedence":
        projects_labels_multi.append("External precedences, internal traffic lights")
    if project == "multi_classic_precedence_classic_tls":
        projects_labels_multi.append("External traffic lights, internal precedences")
    if project == "multi_classic_precedence":
        projects_labels_multi.append("Only precedences")
    if project == "multi_reservation":
        projects_labels_multi.append("Only reservations")
    if project == "multi_reservation_classic_precedence":
        projects_labels_multi.append("External precedences, internal reservations")
    if project == "multi_classic_precedence_reservation":
        projects_labels_multi.append("External reservations, internal precedences")
    if project == "multi_comp_auction":
        projects_labels_multi.append("Only competitive auctions")
    if project == "multi_comp_auction_classic_precedence":
        projects_labels_multi.append("External precedences, internal competitive auctions")
    if project == "multi_classic_precedence_comp_auction":
        projects_labels_multi.append("External competitive auctions, internal precedences")
    if project == "multi_coop_auction":
        projects_labels_multi.append("Only cooperative auctions")
    if project == "multi_coop_auction_classic_precedence":
        projects_labels_multi.append("External precedences, internal cooperative auctions")
    if project == "multi_classic_precedence_coop_auction":
        projects_labels_multi.append("External cooperative auctions, internal precedences")

group_measures_multi = {}

group_measures_multi['sims'] = [str(vehs) for vehs in numberOfVehicles]

i = 0
j = 0

for title in head_titles_multi:
    k = 0
    group_measures_multi[title] = []
    while k < groups_multi[i]:
        group_measures_multi[title].append({'label': labels_multi[j], 'color': colors_multi[k],
                                            'title': titles_multi[j], 'values': []})
        j += 1
        k += 1
    i += 1

single_measures_multi = {}

for vehs in numberOfVehicles:
    single_measures_multi[str(vehs)] = {}
    for i in range(0, len(labels_multi)):
        single_measures_multi[str(vehs)][labels_multi[i]] = []
        for j in range(0, len(projects_multi)):
            single_measures_multi[str(vehs)][labels_multi[i]].append({'project': projects_multi[j],
                                                                      'color': colors_multi[j], 'values': []})
