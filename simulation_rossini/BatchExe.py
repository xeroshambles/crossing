import BatchLib
import Traiettorie
from multiprocessing import Pool

direct = "~/SUMO/"  # percorso cartella

# apro i file dove scriverò le variazioni di valori delle metriche rispetto al caso base
f = open("Output/ferme.txt", "w")  # creo il file ferme.txt contenente percentuale di auto ferme
vm = open("Output/vel_med.txt", "w")  # creo il file vel_med contenente la velocità media delle auto presenti
cm = open("Output/code.txt", "w")  # creo il file contenente la coda più lunga e il numero medio di auto in coda (%)
t = open("Output/tempo.txt", "w")  # creo il file contenente il tempo impiegato per terminare la simulazione rispetto a non scrivere codice
t_coda = open("Output/t_in_coda.txt", "w")  # creo il file contenente il tempo medio passato in coda rispetto al tempo tot di simulazione
cons = open("Output/consumo.txt", "w")  # creo il file contenente il consumo medio e massimo rispetto al consumo in assenza di traffico (%)
f0 = open("Output0/ferme.txt")  # creo il file ferme.txt contenente percentuale di auto ferme
vm0 = open("Output0/vel_med.txt")  # creo il file vel_med contenente la velocità media delle auto presenti
cm0 = open("Output0/code.txt")  # creo il file contenente la coda più lunga e il numero medio di auto in coda (%)
t0 = open("Output0/tempo.txt")  # creo il file contenente il tempo impiegato per terminare la simulazione rispetto a non scrivere codice
t_coda0 = open("Output0/t_in_coda.txt")  # creo il file contenente il tempo medio passato in coda rispetto al tempo tot di simulazione
cons0 = open("Output0/consumo.txt")  # creo il file contenente il consumo medio e massimo rispetto al consumo in assenza di traffico (%)


# -------------------- VARIABILI MODIFICABILI -------------------- #

from_auto_test = 50  # (per la simulazione impostare a 10)
to_auto_test = 200  # (per la simulazione impostare a 100 o 200 se abbasatanza efficente)
step_auto_test = 50  # (per la simulazione impostare a 10)
prove_fissate_auto = 20  # (per la simulazione impostare a 10)
gui = False
n_porta_base = 5000
celle_per_lato = 20  # per protocolli basati sulla suddivisione matriciale dell'incrocio
secondi_di_sicurezza = 0.6

# ---------------------------------------------------------------- #

tempo_generazione = 43.2  # fissato
lines1 = f0.readlines()
lines2 = vm0.readlines()
lines3 = cm0.readlines()
lines4 = t0.readlines()
lines5 = t_coda0.readlines()
lines6 = cons0.readlines()

traiettorie_matrice = Traiettorie.run(n_porta_base, False, celle_per_lato)

for x in range(from_auto_test, to_auto_test + 1):
    # controllo se il numero di auto di test corrente è un multiplo di quello di input
    if x % step_auto_test == 0:
        f_t = 0.0
        vm_t = 0.0
        cm_t = 0.0
        cx_t = 0.0
        step_sim = 0.0
        t_med_coda = 0.0
        max_t_coda = 0.0
        consumo_max = 0.0
        consumo_med = 0.0
        n_auto = x
        n_port = n_porta_base
        pool = Pool(processes=prove_fissate_auto)
        pool_arr = []
        # eseguo un certo numero di prove per un numero di auto fissate
        for y in range(0, prove_fissate_auto):
            print("ESEGUO PROVA CON " + str(x) + " AUTO...\n")
            pool_arr.append(pool.apply_async(BatchLib.run,
                                             (n_port + x + y, n_auto, tempo_generazione, gui, celle_per_lato,
                                              traiettorie_matrice, secondi_di_sicurezza)))
        # salvo le metriche per ogni prova
        for y in range(0, prove_fissate_auto):
            ret = pool_arr[y].get()
            f_t += float(ret[0])
            vm_t += float(ret[1])
            cm_t += float(ret[2])
            cx_t += float(ret[3])
            step_sim += float(ret[4])
            max_t_coda += float(ret[5])
            t_med_coda += float(ret[6])
            consumo_max += float(ret[7])
            consumo_med += float(ret[8])
        # calcolo la media di tutte le metriche
        f_t = float(f_t) / float(prove_fissate_auto)
        vm_t = float(vm_t) / float(prove_fissate_auto)
        cm_t = float(cm_t) / float(prove_fissate_auto)
        cx_t = float(cx_t) / float(prove_fissate_auto)
        step_sim = float(step_sim) / float(prove_fissate_auto)
        max_t_coda = float(max_t_coda) / float(prove_fissate_auto)
        t_med_coda = float(t_med_coda) / float(prove_fissate_auto)
        consumo_max = float(consumo_max) / float(prove_fissate_auto)
        consumo_med = float(consumo_med) / float(prove_fissate_auto)
        indice_riga = 0
        # prendo l'indice di riga dove incontro il numero di auto di test corrente
        for c in range(0, 5):
            linea = lines1[c].split(" ")
            if linea[0].__contains__(str(x)):
                indice_riga = c
                break
        # salvo le metriche della simulazione base
        f_t0 = float((lines1[indice_riga].split(" "))[1])
        vm_t0 = float((lines2[indice_riga].split(" "))[1])
        cm_t0 = float((lines3[indice_riga].split(" "))[1])
        cx_t0 = float((lines3[indice_riga].split(" "))[2])
        step_sim0 = float((lines4[indice_riga].split(" "))[1])
        max_t_coda0 = float((lines5[indice_riga].split(" "))[1])
        t_med_coda0 = float((lines5[indice_riga].split(" "))[2])
        consumo_max0 = float((lines6[indice_riga].split(" "))[1])
        consumo_med0 = float((lines6[indice_riga].split(" "))[2])
        # calcolo i rapporti rispetto alla simulazione base
        f_t = round(float(f_t) / float(f_t0), 4)
        vm_t = round(float(vm_t) / float(vm_t0), 4)
        cm_t = round(float(cm_t) / float(cm_t0), 4)
        cx_t = round(float(cx_t) / float(cx_t0), 4)
        step_sim = round(float(step_sim) / float(step_sim0), 4)
        max_t_coda = round(float(max_t_coda) / float(max_t_coda0), 4)
        t_med_coda = round(float(t_med_coda) / float(t_med_coda0), 4)
        consumo_max = round(float(consumo_max) / float(consumo_max0), 4)
        consumo_med = round(float(consumo_med) / float(consumo_med0), 4)
        # sottraggo 1 per vedere le diminuzioni rispetto al caso base
        f_t = f_t - 1
        vm_t = vm_t - 1
        cm_t = cm_t - 1
        cx_t = cx_t - 1
        step_sim = step_sim - 1
        t_med_coda = t_med_coda - 1
        max_t_coda = max_t_coda - 1
        consumo_max = consumo_max - 1
        consumo_med = consumo_med - 1
        # converto i valori in stringhe per salvarli su file
        f_s = str(f_t)
        vm_s = str(vm_t)
        cm_s = str(cm_t)
        cx_s = str(cx_t)
        step_sim_s = str(step_sim)
        t_med_coda_s = str(t_med_coda)
        max_t_coda_s = str(max_t_coda)
        consumo_max_s = str(consumo_max)
        consumo_med_s = str(consumo_med)
        # scrivo le variazioni rispetto alla simulazione base sui file
        string_vett1 = vm_s.rsplit(".")
        if vm_t > 0:  # inserisco il segno + se non c'è
            vm_s = "+" + string_vett1[0] + "," + string_vett1[1]
        else:
            vm_s = string_vett1[0] + "," + string_vett1[1]
        vm.write(str(x) + " " + vm_s + "\n")

        string_vett1 = f_s.rsplit(".")
        if f_t > 0:  # inserisco il segno + se non c'è
            f_s = "+" + string_vett1[0] + "," + string_vett1[1]
        else:
            f_s = string_vett1[0] + "," + string_vett1[1]
        f.write(str(x) + " " + f_s + "\n")

        string_vett1 = cm_s.rsplit(".")
        string_vett2 = cx_s.rsplit(".")
        if cm_t > 0:  # inserisco il segno + se non c'è
            cm_s = "+" + string_vett1[0] + "," + string_vett1[1]
        else:
            cm_s = string_vett1[0] + "," + string_vett1[1]
        if cx_t > 0:  # inserisco il segno + se non c'è
            cx_s = "+" + string_vett2[0] + "," + string_vett2[1]
        else:
            cx_s = string_vett2[0] + "," + string_vett2[1]
        cm.write(str(x) + " " + cm_s + " " + cx_s + "\n")

        string_vett1 = step_sim_s.rsplit(".")
        if step_sim > 0:  # inserisco il segno + se non c'è
            step_sim_s = "+" + string_vett1[0] + "," + string_vett1[1]
        else:
            step_sim_s = string_vett1[0] + "," + string_vett1[1]
        t.write(str(x) + " " + step_sim_s + "\n")

        string_vett1 = max_t_coda_s.rsplit(".")
        string_vett2 = t_med_coda_s.rsplit(".")
        if max_t_coda > 0:  # inserisco il segno + se non c'è
            max_t_coda_s = "+" + string_vett1[0] + "," + string_vett1[1]
        else:
            max_t_coda_s = string_vett1[0] + "," + string_vett1[1]
        if t_med_coda > 0:  # inserisco il segno + se non c'è
            t_med_coda_s = "+" + string_vett2[0] + "," + string_vett2[1]
        else:
            t_med_coda_s = string_vett2[0] + "," + string_vett2[1]
        t_coda.write(str(x) + " " + max_t_coda_s + " " + t_med_coda_s + "\n")

        string_vett1 = consumo_max_s.rsplit(".")
        string_vett2 = consumo_med_s.rsplit(".")
        if consumo_max > 0:  # inserisco il segno + se non c'è
            consumo_max_s = "+" + string_vett1[0] + "," + string_vett1[1]
        else:
            consumo_max_s = string_vett1[0] + "," + string_vett1[1]
        if consumo_med > 0:  # inserisco il segno + se non c'è
            consumo_med_s = "+" + string_vett2[0] + "," + string_vett2[1]
        else:
            consumo_med_s = string_vett2[0] + "," + string_vett2[1]
        cons.write(str(x) + " " + consumo_max_s + " " + consumo_med_s + "\n")
# chiudo i file
t.close()
f.close()
cm.close()
vm.close()
t_coda.close()
cons.close()
t0.close()
f0.close()
cm0.close()
vm0.close()
t_coda0.close()
cons0.close()
print("FINE")
