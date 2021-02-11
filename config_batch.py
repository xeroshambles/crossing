# Progetti: "classic_tls", "classic_precedence", "reservation", "auction"

mode = 'auto'  # stringa che imposta la modalità automatica per le simulazioni
repeatSim = 10  # numero di volte per cui la stessa simulazione deve essere ripetuta
numberOfVehicles = [50, 100, 150, 200]  # lista contenente il numero di veicoli per ogni simulazione diversa
diffSim = len(numberOfVehicles)  # numero di simulazioni diverse che devono essere eseguite
seeds = [9001, 2, 350, 39, 78, 567, 1209, 465, 21, 987]  # seme iniziale
projects = ["classic_tls", "classic_precedence", "reservation", "auction"]  # progetti da eseguire
