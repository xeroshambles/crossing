import matplotlib.pyplot as plt
import numpy as np


ind = 4 # numero di simulazioni per foto
width = 0.2
labels = ['COMP + OWP + SR + 80V', 'COOP + AVP + SR + 80V', 'COMP + OWP + SR + 150V', 'COOP + AVP + SR + 150V']
x = np.arange(len(labels))  # the label locations
fig, ax1 = plt.subplots()
comp80 = [35.80071174377224, 37.82397053019339, 37.826741480771865]
coop80 = [40.382010295312924, 41.412561897315605, 39.29189405031279]
comp150 = [14.04660321627830, 20.30617283950617, 14.190012180267967]
coop150 = [23.41547277936963, 25.082114063899674, 20.466508411600785]

dim1 = [35.80071174377224, 40.382010295312924, 14.04660321627830, 23.41547277936963]
dim5 = [37.82397053019339, 41.412561897315605, 20.30617283950617, 25.082114063899674]
dimP = [35.792906644924585, 39.29189405031279, 14.190012180267967, 20.466508411600785]


# ax1.hist(dim1, bins=12, edgecolor='white', align='mid')
# n = 0
# rects1 = ax1.bar(x - 4*width/3, dim1, width, color="#EC9A1A", label='Dimensione 1')
# n += 1.5
rects2 = ax1.bar(x, dim5, width, color="#F5B553", label='Dimensione 5')
# n += 1.5
rects3 = ax1.bar(x + 4*width/3, dimP, width, color="#F5CE91", label='Dimensione Proporzionale')

ax1.set_xticks(x)
ax1.set_xticklabels(labels, rotation=20, ha='right')
# ax1.set_xlabel('Dimensione 1')
ax1.set_ylabel('% corsie libere')
ax1.legend()
# ax1.tick_params(
#     axis='x',  # changes apply to the x-axis
#     which='both',  # both major and minor ticks are affected
#     bottom=False,  # ticks along the bottom edge are off
#     top=False,  # ticks along the top edge are off
#     labelbottom=False)  # labels along the bottom edge are off
ax1.grid(axis='y')
ax1.set_axisbelow(True)

plt.tight_layout()
plt.savefig(r'C:\Users\andca\Desktop\freeLanes_new.png')
# plt.show()
