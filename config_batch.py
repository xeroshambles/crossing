# Progetti: "classic_tls", "classic_precedence", "reservation", "auction"

mode = 'auto'  # stringa che imposta la modalità automatica per le simulazioni
repeatSim = 1  # numero di volte per cui la stessa simulazione deve essere ripetuta
numberOfVehicles = [50]  # lista contenente il numero di veicoli per ogni simulazione diversa
diffSim = len(numberOfVehicles)  # numero di simulazioni diverse che devono essere eseguite
seeds = [9001, 2, 350, 39, 78, 567, 1209, 465, 21, 987]  # seme iniziale
period = 10  # tempo di valutazione del throughput del sistema incrocio
projects = ["classic_tls", "classic_precedence", "reservation", "auction"]  # progetti da eseguire

labels = ['Tempo totale (s)', 'Tempo medio in testa (s)', 'Deviazione standard tempo in testa (s)',
          'Massimo tempo in testa (s)', 'Tempo medio in coda (s)', 'Deviazione standard tempo in coda (s)',
          'Massimo tempo in coda (s)', 'Velocità media (m/s)', 'Deviazione standard velocità (m/s)',
          'Lunghezza media delle code', 'Deviazione standard lunghezza delle code',
          'Massima lunghezza delle code', 'Veicoli fermi', f'Throughput medio (% veicoli / {period} step)']

colors = ['#DF1515', '#1524DF', '#15DF1E', '#DFDF15']

titles = ['total_time', 'mean_head_time', 'st_dev_head_time', 'max_head_time', 'mean_tail_time', 'st_dev_tail_time',
          'max_tail_time', 'mean_speed', 'st_dev_mean_speed', 'mean_tail_length', 'st_dev_tail_length',
          'max_tail_length', 'stopped_vehicles', 'mean_throughput']
