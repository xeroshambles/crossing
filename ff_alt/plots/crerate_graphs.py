import matplotlib.pyplot as plt
import numpy as np
import os


directories_80 = [r'C:\Users\andca\Desktop\provaStop\risultati\num_veh_80_finali']

directories_150 = [r'C:\Users\andca\Desktop\provaStop\risultati\num_veh_150_finali']

# directories_80 = [r'C:\Users\andca\Desktop\provaStop\primi_risultati\num_veh_80']
#
# directories_150 = [r'C:\Users\andca\Desktop\provaStop\primi_risultati\num_veh_150']

directories_complete = [directories_80, directories_150]

results_total = {80: {}, 150: {}}
for directories in directories_complete:
    if directories_complete.index(directories) == 0:
        nVeh = 80
    else:
        nVeh = 150
    results = {}
    for dir in directories:
        for f in os.listdir(dir):
            # print(f)
            # results[f[8:-11]] = {'dim_1': {}, 'dim_5': {}, 'dim_-1': {}}
            if 'newT' in f:
                continue
            dim = f[-6:-4]
            if dim[0] == '-':
                dim = int(dim)
                name = f[8:-11]
            else:
                dim = int(dim[1])
                name = f[8:-10]
            # print(f)
            # print(name, dim)
            if name not in results:
                results[name] = {}
            results[name][dim] = {}
            file = open(f'{dir}\\{f}')
            # print(file.read())
            for line in file:
                print(line)
                if line != '\n' and ':' not in line:
                    break
                line = line.split(':')
                if line[0] not in ['\n', 'free lanes %', 'number of times in traffic %', 'not free passage %', '% ']:
                    if 'without 0' not in line[0] and '%' not in line[0]:
                        # print(line)
                        measure = line[0]
                        value = line[1].replace(' ', '').replace('\n', '')
                        # print(measure, value)
                        results[name][dim][measure] = float(value)
            file.close()
    results_total[nVeh] = results
# for k, v in results_total[80]['Competitive_approach_Only-Winners-Pay_(OWP)_Random_Routes'].items():
#     print(k, v)
# print()
# for k, v in results_total[150]['Competitive_approach_Only-Winners-Pay_(OWP)_Random_Routes'].items():
#     print(k, v)

width = 0.1
ind = 3 # numero di simulazioni per foto

for num_veh in [80, 150]:
    for sim_mode in results_total[num_veh].keys():
        # AVG WT
        avgJT = []  # Junction Time
        avgMGT = []  # Main Group Time
        avgTotT = []  # Total Time
        avgTT = []  # Traffic Time
        avgSGT = []  # Sponsor Group Time

        # StD WT
        stdDvJT = []  # Junction StD
        stdDvMGT = []  # Main Group StD
        stdDvTotT = []  # Total StD
        stdDvTT = []  # Traffic StD
        stdDvSGT = []  # Sponsor Group StD

        # Max WT
        maxJT = []  # Junction StD
        maxMGT = []  # Main Group StD
        maxTotT = []  # Total StD
        maxTT = []  # Traffic StD
        maxSGT = []  # Sponsor Group StD

        # Max WT
        minJT = []  # Junction StD
        minMGT = []  # Main Group StD
        minTotT = []  # Total StD
        minTT = []  # Traffic StD
        minSGT = []  # Sponsor Group StD

        # tag
        tag = []
        notComplete = False
        for i in [1, 5, -1]:
            if i not in results_total[num_veh][sim_mode]:
                notComplete = True
                break
        if not notComplete:
            for dim in [1, 5, -1]:#results_total[num_veh][sim_mode].keys():
                # AVG TJ, MGT & TOT T
                avgJT.append(results_total[num_veh][sim_mode][dim]['avgTJ'])
                avgMGT.append(results_total[num_veh][sim_mode][dim]['avgMGT'])
                avgTotT.append(results_total[num_veh][sim_mode][dim]['avgTotT'])
                # AVG TT & STG
                avgTT.append(results_total[num_veh][sim_mode][dim]['avgTT'])
                avgSGT.append(results_total[num_veh][sim_mode][dim]['avgSGT'])

                # StD TJ, MGT & TOT T
                stdDvJT.append(results_total[num_veh][sim_mode][dim]['stdDvTJ'])
                stdDvMGT.append(results_total[num_veh][sim_mode][dim]['stdDvMGT'])
                stdDvTotT.append(results_total[num_veh][sim_mode][dim]['stdDvTotT'])
                # StD TT & STG
                stdDvTT.append(results_total[num_veh][sim_mode][dim]['stdDvTT'])
                stdDvSGT.append(results_total[num_veh][sim_mode][dim]['stdDvSGT'])

                # Max TJ, MGT & TOT T
                maxJT.append(results_total[num_veh][sim_mode][dim]['maxTJ'])
                maxMGT.append(results_total[num_veh][sim_mode][dim]['maxMGT'])
                maxTotT.append(results_total[num_veh][sim_mode][dim]['maxTotT'])
                # Max TT & STG
                maxTT.append(results_total[num_veh][sim_mode][dim]['maxTT'])
                maxSGT.append(results_total[num_veh][sim_mode][dim]['maxSGT'])

                # Min TJ, MGT & TOT T
                minJT.append(results_total[num_veh][sim_mode][dim]['minTJ'])
                minMGT.append(results_total[num_veh][sim_mode][dim]['minMGT'])
                minTotT.append(results_total[num_veh][sim_mode][dim]['minTotT'])
                # Min TT & STG
                minTT.append(results_total[num_veh][sim_mode][dim]['minTT'])
                minSGT.append(results_total[num_veh][sim_mode][dim]['minSGT'])

                #tag
                tag.append(dim)

            width = 1
            # fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 4))
            fig, (ax2, ax3) = plt.subplots(1, 2, figsize=(12, 4))
            dim1 = [avgJT[0], maxJT[0], minJT[0], stdDvJT[0], avgMGT[0], maxMGT[0], minMGT[0], stdDvMGT[0],
                    avgTotT[0], maxTotT[0], minTotT[0], stdDvTotT[0], avgTT[0], maxTT[0], minTT[0], stdDvTT[0]]
            print(dim1)
            dim5 = [avgJT[1], maxJT[1], minJT[1], stdDvJT[1], avgMGT[1], maxMGT[1], minMGT[1], stdDvMGT[1],
                    avgTotT[1], maxTotT[1], minTotT[1], stdDvTotT[1], avgTT[1], maxTT[1], minTT[1], stdDvTT[1]]
            print(dim5)
            dimProp = [avgJT[2], maxJT[2], minJT[2], stdDvJT[2], avgMGT[2], maxMGT[2], minMGT[2], stdDvMGT[2],
                    avgTotT[2], maxTotT[2], minTotT[2], stdDvTotT[2], avgTT[2], maxTT[2], minTT[2], stdDvTT[2]]
            print(dimProp)
            # ax1.hist(dim1, bins=12, edgecolor='white', align='mid')
            # n = 0
            # ax1.bar(ind + width*n, dim1[0], width, color="#FF3B12", label='AvgJT')
            # n += 1.5
            # ax1.bar(ind + width*n, dim1[1], width, color="#FF603F", label='MaxJT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[2], width, color="#FF7558", label='MinJT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[3], width, color="#FF8268", label='StdDevJT')
            # n += 1.5
            #
            # ax1.bar(ind + width * n, dim1[12], width, color="#39E927", label='AvgTT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[13], width, color="#6DEE60", label='MaxTT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[14], width, color="#A0F098", label='MinTT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[15], width, color="#C2EDBE", label='StdDevTT')
            # n += 1.5
            #
            # ax1.bar(ind + width * n, dim1[4], width, color="#DE27FF", label='AvgMGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[5], width, color="#EB7FFF", label='MaxMGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[6], width, color="#F3B1FF", label='MinMGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[7], width, color="#FADDFF", label='StdDevMGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[8], width, color="#192AFF", label='AvgTotT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[9], width, color="#4956FF", label='MaxTotT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[10], width, color="#747EFE", label='MinTotT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[11], width, color="#A4AAFF", label='StdDevTotT')
            # ax1.set_xlabel('Dimensione 1')
            # ax1.set_ylabel('Time (s)')
            # ax1.tick_params(
            #     axis='x',  # changes apply to the x-axis
            #     which='both',  # both major and minor ticks are affected
            #     bottom=False,  # ticks along the bottom edge are off
            #     top=False,  # ticks along the top edge are off
            #     labelbottom=False)  # labels along the bottom edge are off
            # ax1.grid(axis='y')
            # ax1.set_axisbelow(True)

            # ax2.hist(dim5, edgecolor='white', align='mid')
            n = 0
            ax2.bar(ind + width * n, dim5[0], width, color="#FF3B12", label='AvgJT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[1], width, color="#FF603F", label='MaxJT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[2], width, color="#FF7558", label='MinJT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[3], width, color="#FF8268", label='StdDevJT')
            n += 1.5

            ax2.bar(ind + width * n, dim5[12], width, color="#39E927", label='AvgTT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[13], width, color="#6DEE60", label='MaxTT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[14], width, color="#A0F098", label='MinTT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[15], width, color="#C2EDBE", label='StdDevTT')
            n += 1.5

            ax2.bar(ind + width * n, dim5[4], width, color="#DE27FF", label='AvgMGT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[5], width, color="#EB7FFF", label='MaxMGT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[6], width, color="#F3B1FF", label='MinMGT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[7], width, color="#FADDFF", label='StdDevMGT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[8], width, color="#192AFF", label='AvgTotT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[9], width, color="#4956FF", label='MaxTotT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[10], width, color="#747EFE", label='MinTotT')
            n += 1.5
            ax2.bar(ind + width * n, dim5[11], width, color="#A4AAFF", label='StdDevTotT')
            ax2.set_xlabel('Dimensione 5')
            ax2.set_ylabel('Time (s)')
            ax2.tick_params(
                axis='x',  # changes apply to the x-axis
                which='both',  # both major and minor ticks are affected
                bottom=False,  # ticks along the bottom edge are off
                top=False,  # ticks along the top edge are off
                labelbottom=False)  # labels along the bottom edge are off
            ax2.grid(axis='y')
            ax2.set_axisbelow(True)

            # ax3.hist(dimProp, edgecolor='white', align='mid')
            n = 0
            ax3.bar(ind + width*n, dimProp[0], width, color="#FF3B12", label='AvgJT')
            n += 1.5
            ax3.bar(ind + width*n, dimProp[1], width, color="#FF603F", label='MaxJT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[2], width, color="#FF7558", label='MinJT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[3], width, color="#FF8268", label='StdDevJT')
            n += 1.5

            ax3.bar(ind + width * n, dimProp[12], width, color="#39E927", label='AvgTT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[13], width, color="#6DEE60", label='MaxTT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[14], width, color="#A0F098", label='MinTT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[15], width, color="#C2EDBE", label='StdDevTT')
            n += 1.5

            ax3.bar(ind + width * n, dimProp[4], width, color="#DE27FF", label='AvgMGT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[5], width, color="#EB7FFF", label='MaxMGT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[6], width, color="#F3B1FF", label='MinMGT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[7], width, color="#FADDFF", label='StdDevMGT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[8], width, color="#192AFF", label='AvgTotT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[9], width, color="#4956FF", label='MaxTotT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[10], width, color="#747EFE", label='MinTotT')
            n += 1.5
            ax3.bar(ind + width * n, dimProp[11], width, color="#A4AAFF", label='StdDevTotT')
            ax3.set_xlabel('Dimensione proporzionale')
            ax3.set_ylabel('Time (s)')
            lgd = ax3.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            ax3.tick_params(
                axis='x',  # changes apply to the x-axis
                which='both',  # both major and minor ticks are affected
                bottom=False,  # ticks along the bottom edge are off
                top=False,  # ticks along the top edge are off
                labelbottom=False)  # labels along the bottom edge are off
            ax3.grid(axis='y')
            ax3.set_axisbelow(True)

            plt.tight_layout()
            # plt.show()
            if num_veh == 80:
                plt.savefig(r'C:\Users\andca\Desktop\provaStop\plots\num_veh_80\complete_noDim1' + f'\{sim_mode}.png',
                            bbox_extra_artists=(lgd,), bbox_inches='tight')
            else:
                plt.savefig(r'C:\Users\andca\Desktop\provaStop\plots\num_veh_150\complete_noDim1' + f'\{sim_mode}.png',
                            bbox_extra_artists=(lgd,), bbox_inches='tight')
            plt.close()


            # width = 1
            # fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 4))
            # dim1 = [avgJT[0], maxJT[0], minJT[0], stdDvJT[0], avgMGT[0], maxMGT[0], minMGT[0], stdDvMGT[0],
            #         avgTotT[0], maxTotT[0], minTotT[0], stdDvTotT[0]]
            # print(dim1)
            # dim5 = [avgJT[1], maxJT[1], minJT[1], stdDvJT[1], avgMGT[1], maxMGT[1], minMGT[1], stdDvMGT[1],
            #         avgTotT[1], maxTotT[1], minTotT[1], stdDvTotT[1]]
            # print(dim5)
            # dimProp = [avgJT[2], maxJT[2], minJT[2], stdDvJT[2], avgMGT[2], maxMGT[2], minMGT[2], stdDvMGT[2],
            #         avgTotT[2], maxTotT[2], minTotT[2], stdDvTotT[2]]
            # print(dimProp)
            # # ax1.hist(dim1, bins=12, edgecolor='white', align='mid')
            # n = 0
            # ax1.bar(ind + width*n, dim1[0], width, color="#FF3B12", label='AvgTJ')
            # n += 1.5
            # ax1.bar(ind + width*n, dim1[1], width, color="#FF603F", label='MaxTJ')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[2], width, color="#FF7558", label='MinTJ')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[3], width, color="#FF8268", label='StdDevTJ')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[4], width, color="#DE27FF", label='AvgMGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[5], width, color="#EB7FFF", label='MaxMGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[6], width, color="#F3B1FF", label='MinMGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[7], width, color="#FADDFF", label='StdDevMGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[8], width, color="#192AFF", label='AvgTotT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[9], width, color="#4956FF", label='MaxTotT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[10], width, color="#747EFE", label='MinTotT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[11], width, color="#A4AAFF", label='StdDevTotT')
            # ax1.set_xlabel('Dimensione 1')
            # ax1.set_ylabel('Time (s)')
            # ax1.tick_params(
            #     axis='x',  # changes apply to the x-axis
            #     which='both',  # both major and minor ticks are affected
            #     bottom=False,  # ticks along the bottom edge are off
            #     top=False,  # ticks along the top edge are off
            #     labelbottom=False)  # labels along the bottom edge are off
            # ax1.grid(axis='y')
            # ax1.set_axisbelow(True)
            #
            # # ax2.hist(dim5, edgecolor='white', align='mid')
            # n = 0
            # ax2.bar(ind + width * n, dim5[0], width, color="#FF3B12", label='AvgTJ')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[1], width, color="#FF603F", label='MaxTJ')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[2], width, color="#FF7558", label='MinTJ')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[3], width, color="#FF8268", label='StdDevTJ')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[4], width, color="#DE27FF", label='AvgMGT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[5], width, color="#EB7FFF", label='MaxMGT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[6], width, color="#F3B1FF", label='MinMGT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[7], width, color="#FADDFF", label='StdDevMGT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[8], width, color="#192AFF", label='AvgTotT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[9], width, color="#4956FF", label='MaxTotT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[10], width, color="#747EFE", label='MinTotT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[11], width, color="#A4AAFF", label='StdDevTotT')
            # ax2.set_xlabel('Dimensione 5')
            # ax2.set_ylabel('Time (s)')
            # ax2.tick_params(
            #     axis='x',  # changes apply to the x-axis
            #     which='both',  # both major and minor ticks are affected
            #     bottom=False,  # ticks along the bottom edge are off
            #     top=False,  # ticks along the top edge are off
            #     labelbottom=False)  # labels along the bottom edge are off
            # ax2.grid(axis='y')
            # ax2.set_axisbelow(True)
            #
            # # ax3.hist(dimProp, edgecolor='white', align='mid')
            # n = 0
            # ax3.bar(ind + width*n, dimProp[0], width, color="#FF3B12", label='AvgTJ')
            # n += 1.5
            # ax3.bar(ind + width*n, dimProp[1], width, color="#FF603F", label='MaxTJ')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[2], width, color="#FF7558", label='MinTJ')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[3], width, color="#FF8268", label='StdDevTJ')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[4], width, color="#DE27FF", label='AvgMGT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[5], width, color="#EB7FFF", label='MaxMGT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[6], width, color="#F3B1FF", label='MinMGT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[7], width, color="#FADDFF", label='StdDevMGT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[8], width, color="#192AFF", label='AvgTotT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[9], width, color="#4956FF", label='MaxTotT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[10], width, color="#747EFE", label='MinTotT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[11], width, color="#A4AAFF", label='StdDevTotT')
            # ax3.set_xlabel('Dimensione proporzionale')
            # ax3.set_ylabel('Time (s)')
            # lgd = ax3.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            # ax3.tick_params(
            #     axis='x',  # changes apply to the x-axis
            #     which='both',  # both major and minor ticks are affected
            #     bottom=False,  # ticks along the bottom edge are off
            #     top=False,  # ticks along the top edge are off
            #     labelbottom=False)  # labels along the bottom edge are off
            # ax3.grid(axis='y')
            # ax3.set_axisbelow(True)
            #
            # plt.tight_layout()
            # # plt.show()
            # if num_veh == 110:
            #     plt.savefig(r'C:\Users\andca\Desktop\provaStop\plots\num_veh_110\junction' + f'\{sim_mode}.png',
            #                 bbox_extra_artists=(lgd,), bbox_inches='tight')
            # else:
            #     plt.savefig(r'C:\Users\andca\Desktop\provaStop\plots\num_veh_170\junction' + f'\{sim_mode}.png',
            #                 bbox_extra_artists=(lgd,), bbox_inches='tight')
            # plt.close()
            #
            #
            # fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 4))
            # dim1 = [avgTT[0], maxTT[0], minTT[0], stdDvTT[0], avgSGT[0], maxSGT[0], minSGT[0], stdDvSGT[0],
            #         avgTotT[0], maxTotT[0], minTotT[0], stdDvTotT[0]]
            # print(dim1)
            # dim5 = [avgTT[1], maxTT[1], minTT[1], stdDvTT[1], avgSGT[1], maxSGT[1], minSGT[1], stdDvSGT[1],
            #         avgTotT[1], maxTotT[1], minTotT[1], stdDvTotT[1]]
            # print(dim5)
            # dimProp = [avgTT[2], maxTT[2], minTT[2], stdDvTT[2], avgSGT[2], maxSGT[2], minSGT[2], stdDvSGT[2],
            #         avgTotT[2], maxTotT[2], minTotT[2], stdDvTotT[2]]
            # print(dimProp)
            # # ax1.hist(dim1, bins=12, edgecolor='white', align='mid')
            # n = 0
            # ax1.bar(ind + width*n, dim1[0], width, color="#C7D836", label='AvgTT')
            # n += 1.5
            # ax1.bar(ind + width*n, dim1[1], width, color="#D0E619", label='MaxTT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[2], width, color="#DBE966", label='MinTT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[3], width, color="#ECF78F", label='StdDevTT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[4], width, color="#39E927", label='AvgSGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[5], width, color="#6DEE60", label='MaxSGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[6], width, color="#A0F098", label='MinSGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[7], width, color="#C2EDBE", label='StdDevSGT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[8], width, color="#192AFF", label='AvgTotT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[9], width, color="#4956FF", label='MaxTotT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[10], width, color="#747EFE", label='MinTotT')
            # n += 1.5
            # ax1.bar(ind + width * n, dim1[11], width, color="#A4AAFF", label='StdDevTotT')
            # ax1.set_xlabel('Dimensione 1')
            # ax1.set_ylabel('Time (s)')
            # ax1.tick_params(
            #     axis='x',  # changes apply to the x-axis
            #     which='both',  # both major and minor ticks are affected
            #     bottom=False,  # ticks along the bottom edge are off
            #     top=False,  # ticks along the top edge are off
            #     labelbottom=False)  # labels along the bottom edge are off
            # ax1.grid(axis='y')
            # ax1.set_axisbelow(True)
            #
            # # ax2.hist(dim5, edgecolor='white', align='mid')
            # n = 0
            # ax2.bar(ind + width * n, dim5[0], width, color="#C7D836", label='AvgTT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[1], width, color="#D0E619", label='MaxTT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[2], width, color="#DBE966", label='MinTT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[3], width, color="#ECF78F", label='StdDevTT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[4], width, color="#39E927", label='AvgSGT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[5], width, color="#6DEE60", label='MaxSGT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[6], width, color="#A0F098", label='MinSGT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[7], width, color="#C2EDBE", label='StdDevSGT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[8], width, color="#192AFF", label='AvgTotT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[9], width, color="#4956FF", label='MaxTotT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[10], width, color="#747EFE", label='MinTotT')
            # n += 1.5
            # ax2.bar(ind + width * n, dim5[11], width, color="#A4AAFF", label='StdDevTotT')
            # ax2.set_xlabel('Dimensione 5')
            # ax2.set_ylabel('Time (s)')
            # ax2.tick_params(
            #     axis='x',  # changes apply to the x-axis
            #     which='both',  # both major and minor ticks are affected
            #     bottom=False,  # ticks along the bottom edge are off
            #     top=False,  # ticks along the top edge are off
            #     labelbottom=False)  # labels along the bottom edge are off
            # ax2.grid(axis='y')
            # ax2.set_axisbelow(True)
            #
            # # ax3.hist(dimProp, edgecolor='white', align='mid')
            # n = 0
            # ax3.bar(ind + width*n, dimProp[0], width, color="#C7D836", label='AvgTT')
            # n += 1.5
            # ax3.bar(ind + width*n, dimProp[1], width, color="#D0E619", label='MaxTT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[2], width, color="#DBE966", label='MinTT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[3], width, color="#ECF78F", label='StdDevTT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[4], width, color="#39E927", label='AvgSGT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[5], width, color="#6DEE60", label='MaxSGT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[6], width, color="#A0F098", label='MinSGT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[7], width, color="#C2EDBE", label='StdDevSGT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[8], width, color="#192AFF", label='AvgTotT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[9], width, color="#4956FF", label='MaxTotT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[10], width, color="#747EFE", label='MinTotT')
            # n += 1.5
            # ax3.bar(ind + width * n, dimProp[11], width, color="#A4AAFF", label='StdDevTotT')
            #
            # ax3.set_xlabel('Dimensione proporzionale')
            # ax3.set_ylabel('Time (s)')
            # lgd = ax3.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            # ax3.tick_params(
            #     axis='x',  # changes apply to the x-axis
            #     which='both',  # both major and minor ticks are affected
            #     bottom=False,  # ticks along the bottom edge are off
            #     top=False,  # ticks along the top edge are off
            #     labelbottom=False)  # labels along the bottom edge are off
            # ax3.grid(axis='y')
            # ax3.set_axisbelow(True)
            #
            # plt.tight_layout()
            # # plt.show()
            # if num_veh == 110:
            #     plt.savefig(r'C:\Users\andca\Desktop\provaStop\plots\num_veh_110\traffic' + f'\{sim_mode}.png',
            #                 bbox_extra_artists=(lgd,), bbox_inches='tight')
            # else:
            #     plt.savefig(r'C:\Users\andca\Desktop\provaStop\plots\num_veh_170\traffic' + f'\{sim_mode}.png',
            #                 bbox_extra_artists=(lgd,), bbox_inches='tight')
        # figCWT, axJT = plt.subplots()
        #
        # n = 0
        # for i in range(3):
        #     rectsJT = axJT.bar(ind + width*n, avgJT[i], width, color="#FF3B12")
        #     n += 1
        #     rectsMaxJT = axJT.bar(ind + width*n, maxJT[i], width, color="#FF603F")
        #     n += 1
        #     rectsMinJT = axJT.bar(ind + width * n, minJT[i], width, color="#FF7558")
        #     n += 1
        #     rectsStdDJT = axJT.bar(ind + width * n, stdDvJT[i], width, color="#FF8268")
        #     n += 1
        #     rectsMGT = axJT.bar(ind + width * n, avgMGT[i], width, color="#DE27FF")
        #     n += 1
        #     rectsMaxMGT = axJT.bar(ind + width * n, maxMGT[i], width, color="#EB7FFF")
        #     n += 1
        #     rectsMinMGT = axJT.bar(ind + width * n, minMGT[i], width, color="#F3B1FF")
        #     n += 1
        #     rectsStdDMGT = axJT.bar(ind + width * n, stdDvMGT[i], width, color="#FADDFF")
        #     n += 1
        #     rectsTotT = axJT.bar(ind + width * n, avgTotT[i], width, color="#192AFF")
        #     n += 1
        #     rectsMaxTotT = axJT.bar(ind + width * n, maxTotT[i], width, color="#4956FF")
        #     n += 1
        #     rectsMinTotT = axJT.bar(ind + width * n, minTotT[i], width, color="#747EFE")
        #     n += 1
        #     rectsStdDTotT = axJT.bar(ind + width * n, stdDvTotT[i], width, color="#A4AAFF")
        #     n += 3
        # plt.xticks([-1, 1, 5, 4])
        # plt.hist([avgJT, maxJT, minJT, stdDvJT,
        #           avgMGT, maxMGT, minMGT, stdDvMGT,
        #           avgJT, maxJT, minJT, stdDvJT], color=['#FF3B12', '#FF603F', '#FF7558', '#FF8268',
        #                                                 '#DE27FF', '#EB7FFF', '#F3B1FF', '#FADDFF',
        #                                                 '#192AFF', '#4956FF', '#747EFE', '#A4AAFF'
        #                                                 ], rwidth=0.9, align='left')
        # plt.hist([avgMGT, maxMGT, minMGT, stdDvMGT], color=['#DE27FF', '#EB7FFF', '#F3B1FF', '#FADDFF'])
        # plt.hist([avgJT, maxJT, minJT, stdDvJT], color=['#192AFF', '#4956FF', '#747EFE', '#A4AAFF'])


        # axJT.set_ylabel("Junction Waiting Times")
        # print(tag)
        #
        # axJT.set_title(f"{sim_mode}\nJunction times")
        # # axCWT.set_xticks(ind + width / 2)
        #
        # lgd = axJT.legend((rectsJT[0], rectsMaxJT[0], rectsMinJT[0], rectsStdDJT[0],
        #              rectsMGT[0], rectsMaxMGT[0], rectsMinMGT[0], rectsStdDMGT[0],
        #              rectsTotT[0], rectsMaxTotT[0], rectsMinTotT[0], rectsStdDTotT[0]),
        #              ('avg JT', 'Max JT', 'min JT', 'StdD JT',
        #               'avg MGT', 'Max MGT', 'min MGT', 'StdD MGT',
        #               'avg TotT', 'Max TotT', 'min TotT', 'StdD TotT'), loc='center left', bbox_to_anchor=(1, 0.5))
        #
        # plt.grid(True)
        # if num_veh == 80:
        #     plt.savefig(r'C:\Users\andca\Desktop\SUMO\provaStop\plots\num_veh_80\junction' + f'\{sim_mode}.png',
        #                 bbox_extra_artists=(lgd,), bbox_inches='tight')
        # else:
        #     plt.savefig(r'C:\Users\andca\Desktop\SUMO\provaStop\plots\num_veh_150\junction' + f'\{sim_mode}.png',
        #                 bbox_extra_artists=(lgd,), bbox_inches='tight')
        # # print("Plot saved as \"AverageWaitingTimeAtCrossings.png\"")
        #
        # # plt.show()
        # plt.close()
        #
        # figCWT, axTT = plt.subplots()
        # n = 0
        # for i in range(3):
        #     rectsTT = axTT.bar(ind + width * n, avgTT[i], width, color="#C7D836")
        #     n += 1
        #     rectsMaxTT = axTT.bar(ind + width * n, maxTT[i], width, color="#D0E619")
        #     n += 1
        #     rectsMinTT = axTT.bar(ind + width * n, minTT[i], width, color="#DBE966")
        #     n += 1
        #     rectsStdDTT = axTT.bar(ind + width * n, stdDvTT[i], width, color="#ECF78F")
        #     n += 1
        #     rectsSGT = axTT.bar(ind + width * n, avgSGT[i], width, color="#39E927")
        #     n += 1
        #     rectsMaxSGT = axTT.bar(ind + width * n, maxSGT[i], width, color="#6DEE60")
        #     n += 1
        #     rectsMinSGT = axTT.bar(ind + width * n, minSGT[i], width, color="#A0F098")
        #     n += 1
        #     rectsStdDSGT = axTT.bar(ind + width * n, stdDvSGT[i], width, color="#C2EDBE")
        #     n += 1
        #     rectsTotT = axTT.bar(ind + width * n, avgTotT[i], width, color="#192AFF")
        #     n += 1
        #     rectsMaxTotT = axTT.bar(ind + width * n, maxTotT[i], width, color="#4956FF")
        #     n += 1
        #     rectsMinTotT = axTT.bar(ind + width * n, minTotT[i], width, color="#747EFE")
        #     n += 1
        #     rectsStdDTotT = axTT.bar(ind + width * n, stdDvTotT[i], width, color="#A4AAFF")
        #     n += 3
        #
        # axTT.set_ylabel("Traffic Waiting Times")
        # print(tag)
        #
        # axTT.set_title(f"{sim_mode}\ntraffic times")
        # # axCWT.set_xticks(ind + width / 2)
        #
        # lgd = axTT.legend((rectsTT[0], rectsMaxTT[0], rectsMinTT[0], rectsStdDTT[0],
        #              rectsSGT[0], rectsMaxSGT[0], rectsMinSGT[0], rectsStdDSGT[0],
        #              rectsTotT[0], rectsMaxTotT[0], rectsMinTotT[0], rectsStdDTotT[0]),
        #             ('avg TT', 'Max TT', 'min TT', 'StdD TT',
        #              'avg SGT', 'Max SGT', 'min SGT', 'StdD SGT',
        #              'avg TotT', 'Max TotT', 'min TotT', 'StdD TotT'), loc='center left', bbox_to_anchor=(1, 0.5))
        #
        # plt.grid(True)
        # if num_veh == 80:
        #     plt.savefig(r'C:\Users\andca\Desktop\SUMO\provaStop\plots\num_veh_80\traffic' + f'\{sim_mode}.png',
        #                 bbox_extra_artists=(lgd,), bbox_inches='tight')
        # else:
        #     plt.savefig(r'C:\Users\andca\Desktop\SUMO\provaStop\plots\num_veh_150\traffic' + f'\{sim_mode}.png',
        #                 bbox_extra_artists=(lgd,), bbox_inches='tight')
        # # print("Plot saved as \"AverageWaitingTimeAtCrossings.png\"")
        #
        # plt.show()



# group1 = [1, 1, 1, 2, 2, 3, 4]
# group2 = [2, 2, 2, 1, 1, 3, 1, 4]
#
# # Create a stacked histogram here
# plt.hist([group1, group2],
#          bins=[1, 2, 3, 4, 5], rwidth=0.9, align="left")
#
# plt.legend(["Group 1", "Group 2"])
# plt.xticks([1, 2, 3, 4])
# plt.ylabel("Quantity")
# plt.xlabel("Value")
# plt.show()

