from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
import random
import math

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa

DISTANCE = 60
INTERSECTION = 14.40
TLS_ID = "4"

QUEUE = []

LANES = ["0_0", "2_0", "4_0", "6_0"]

LANE_NUMBERS = [0, 1, 2, 3]

LINKS = {
    "0": ("0_0", "5_0"),
    "1": ("2_0", "7_0"),
    "2": ("4_0", "1_0"),
    "3": ("6_0", "3_0"),
}


# set signal light for the given lane
def set_traffic_light(lane_id, signal):
    for key in LINKS:
        if LINKS[key][0] == lane_id:
            traci.trafficlight.setLinkState(TLS_ID, int(key), signal)
        else:
            traci.trafficlight.setLinkState(TLS_ID, int(key), "r")


# make vehicle subscription
def make_subscription(vehicle_id, lane_id, time, vehicle_speed):
    for sub in QUEUE:
        if sub[0] == vehicle_id:
            return
    QUEUE.append([vehicle_id, lane_id, vehicle_speed, time, traci.simulation.getTime()])
    return


def reset_traffic_light():
    for key in LINKS:
        traci.trafficlight.setLinkState(TLS_ID, int(key), "r")


def run():
    """execute the TraCI control loop"""
    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        # randomize lanes
        random.shuffle(LANE_NUMBERS)
        # vehicles approaching intersection
        for i in LANE_NUMBERS:
            # whether a vehicle enters in a detector
            if traci.inductionloop.getLastStepVehicleNumber(str(i)) > 0:
                # get vehicle data
                vehicle_id = traci.inductionloop.getLastStepVehicleIDs(str(i))[0]
                lane_id = traci.vehicle.getLaneID(vehicle_id)
                vehicle_speed = traci.vehicle.getSpeed(vehicle_id)
                # calculate vehicle time
                time = math.ceil((DISTANCE + INTERSECTION) / vehicle_speed)
                # append subscription to queue
                make_subscription(vehicle_id, lane_id, time, vehicle_speed)
        if len(QUEUE) > 0:
            if traci.vehicle.getSpeed(QUEUE[0][0]) <= 0.1:
                QUEUE[0][3] = math.ceil(INTERSECTION / QUEUE[0][2])
                QUEUE[0][4] = traci.simulation.getTime()
            if traci.simulation.getTime() - QUEUE[0][4] <= QUEUE[0][3]:
                # set green signal
                set_traffic_light(QUEUE[0][1], "g")
            else:
                # set red signal
                if len(QUEUE) > 1 and QUEUE[1][1] != QUEUE[0][1]:
                    set_traffic_light(QUEUE[0][1], "r")
                # delete subscription from queue
                QUEUE.pop(0)
        else:
            reset_traffic_light()
        step += 1
    traci.close()
    sys.stdout.flush()


def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options


# this is the main entry point of this script
if __name__ == "__main__":
    options = get_options()

    # this script has been called from the command line. It will start sumo as a
    # server, then connect and run
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    # this is the normal way of using traci. sumo is started as a
    # subprocess and then the python script connects and runs
    traci.start([sumoBinary, "-c", "intersection.sumocfg",
                 "--tripinfo-output", "tripinfo.xml"])
    run()
