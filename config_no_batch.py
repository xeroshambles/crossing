config_file = "intersection.sumocfg"  # file di configurazione della simulazione
junction_id = 7  # id dell'incrocio
lanes = []  # lista dei nomi delle lane
lanes_ids = [0, 1, 2]  # lista degli id delle lanes nell'incrocio
node_ids = [2, 8, 12, 6]  # lista degli id dei nodi di partenza e di arrivo nell'incrocio
period = 10  # tempo di valutazione del throughput del sistema incrocio
seed = 9001  # seme iniziale
tempo_generazione = 43.2  # tempo di generazione dei veicoli

"""Con questo ciclo inizializzo i nomi delle lane"""

for i in node_ids:
    for lane in lanes_ids:
        lanes.append(f'e{"0" if i < 12 else ""}{i}_0{junction_id}_{lane}')
        lanes.append(f'e0{junction_id}_{"0" if i < 12 else ""}{i}_{lane}')

labels = ['Tempo totale (s)', 'Tempo medio in testa (s)', 'Deviazione standard tempo in testa (s)',
              'Massimo tempo in testa (s)', 'Tempo medio in coda (s)', 'Deviazione standard tempo in coda (s)',
              'Massimo tempo in coda (s)', 'Velocità media (m/s)', 'Deviazione standard velocità (m/s)',
              'Lunghezza media delle code', 'Deviazione standard lunghezza delle code',
              'Massima lunghezza delle code', 'Veicoli fermi', f'Throughput medio (% veicoli / {period} step)']

colors = ['#DF1515', '#1524DF', '#15DF1E']

titles = ['total_time', 'mean_head_time', 'st_dev_head_time', 'max_head_time', 'mean_tail_time', 'st_dev_tail_time',
          'max_tail_time', 'mean_speed', 'st_dev_mean_speed', 'mean_tail_length', 'st_dev_tail_length',
          'max_tail_length', 'stopped_vehicles', 'mean_throughput']
