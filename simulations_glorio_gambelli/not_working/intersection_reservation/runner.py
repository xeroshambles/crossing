from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
import math
import random

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa

SUBSCRIPTIONS = []

QUEUES = {
    "2to5_0": [],
    "2to5_1": [],
    "2to5_2": [],
    "3to5_0": [],
    "3to5_1": [],
    "3to5_2": [],
    "4to5_0": [],
    "4to5_1": [],
    "4to5_2": [],
    "1to5_0": [],
    "1to5_1": [],
    "1to5_2": []
}

COLLISIONS = {
    "2to5_0": [],
    "2to5_1": ["D", "E", "H"],
    "2to5_2": ["A", "B"],
    "3to5_0": [],
    "3to5_1": ["A", "E", "F"],
    "3to5_2": ["B", "C"],
    "4to5_0": [],
    "4to5_1": ["B", "F", "G"],
    "4to5_2": ["C", "D"],
    "1to5_0": [],
    "1to5_1": ["C", "G", "H"],
    "1to5_2": ["D", "A"]
}

LANES = [
    "2to5_1",
    "2to5_2",
    "3to5_1",
    "3to5_2",
    "4to5_1",
    "4to5_2",
    "1to5_1",
    "1to5_2",
]

LANE_NUMBERS = [0, 1, 2, 3, 4, 5, 6, 7]

NODES = {
    "A": [0.00, 5.00],
    "B": [5.00, 0.00],
    "C": [0.00, -5.00],
    "D": [-5.00, 0.00],
    "E": [-5.00, 5.00],
    "F": [5.00, 5.00],
    "G": [5.00, -5.00],
    "H": [-5.00, -5.00]
}

LANES_POINTS = {
    "2to5_1": [[-5.00, 13.6], 1],
    "2to5_2": [[-1.50, 13.6], 1],
    "3to5_1": [[13.6, 5.0], 0],
    "3to5_2": [[13.6, 1.50], 0],
    "4to5_1": [[5.00, -13.6], 1],
    "4to5_2": [[1.50, -13.6], 1],
    "1to5_1": [[-13.6, -5.00], 0],
    "1to5_2": [[-13.6, -1.50], 0],
}

LINKS = {
    "0": [('2to5_0', '5to1_0', ':node5_0_0')],
    "1": [('2to5_1', '5to4_1', ':node5_1_0'), ('2to5_2', '5to3_2', ':node5_2_0')],
    "2": [('3to5_0', '5to2_0', ':node5_3_0')],
    "3": [('3to5_1', '5to1_1', ':node5_4_0'), ('3to5_2', '5to4_2', ':node5_5_0')],
    "4": [('4to5_0', '5to3_0', ':node5_6_0')],
    "5": [('4to5_1', '5to2_1', ':node5_7_0'), ('4to5_2', '5to1_2', ':node5_8_0')],
    "6": [('1to5_0', '5to4_0', ':node5_9_0')],
    "7": [('1to5_1', '5to3_1', ':node5_10_0'), ('1to5_2', '5to2_2', ':node5_11_0')]
}

GAP = 2
EDGE_LENGTH = 86.4
DISTANCE = 50
INTERSECTION_SPEED = 16.67
TLS_ID = "node5"


# add one step to the subscriptions window
def add_sub_step():
    SUBSCRIPTIONS.append({"A": {"2to5_2": None, "3to5_1": None, "1to5_2": None},
                          "B": {"2to5_2": None, "3to5_2": None, "4to5_1": None},
                          "C": {"3to5_2": None, "4to5_2": None, "1to5_1": None},
                          "D": {"2to5_1": None, "4to5_2": None, "1to5_2": None},
                          "E": {"2to5_1": None, "3to5_1": None},
                          "F": {"3to5_1": None, "4to5_1": None},
                          "G": {"4to5_1": None, "1to5_1": None},
                          "H": {"1to5_1": None, "2to5_1": None}
                          })

# remove first step from the subscriptions window
def remove_sub_step():
    SUBSCRIPTIONS.pop(0)


# compute distance between 2 points
def d(edges):
    return traci.simulation.getDistanceRoad(edges[0], EDGE_LENGTH, edges[1], EDGE_LENGTH)


# make a reservation for an incoming vehicle
def make_reservation(vehicle_id, lane_id):
    for coll in COLLISIONS[lane_id]:
        coord = NODES[coll]
        starting_point = LANES_POINTS[lane_id][0]
        vertical = LANES_POINTS[lane_id][1]
        start = coord
        start = [start[0] - GAP * (1 - vertical), start[1] - GAP * vertical]
        end = coord
        end = [end[0] - GAP * (1 - vertical), end[1] - GAP * vertical]
        starting_to_start = traci.simulation.getDistance2D(starting_point[0], starting_point[1], start[0], start[1])
        starting_to_end = traci.simulation.getDistance2D(starting_point[0], starting_point[1], end[0], end[1])
        time_to_start = math.floor(traci.simulation.getTime() + starting_to_start / INTERSECTION_SPEED)
        time_to_end = math.ceil(traci.simulation.getTime() + starting_to_end / INTERSECTION_SPEED)
        # reservation
        for time in range(time_to_start % 20, (time_to_end + 1) % 20):
            if SUBSCRIPTIONS[time][coll][lane_id] is not None:
                return False
        for time in range(time_to_start % 20, (time_to_end + 1) % 20):
            SUBSCRIPTIONS[time][coll][lane_id] = vehicle_id
        traci.vehicle.slowDown(vehicle_id, INTERSECTION_SPEED, time_to_start - traci.simulation.getTime())
        return True


def check_sub(vehicle_id, lane_id, collisions):
    for t in SUBSCRIPTIONS:
        for c in collisions:
            if t[c][lane_id]:
                for v in t[c][lane_id]:
                    if v == vehicle_id:
                        return True
    return False


# set signal light for the given lane
def set_traffic_light(lane_id, signal):
    for key in LINKS:
        for link in LINKS[key]:
            if link[0] == lane_id:
                traci.trafficlight.setLinkState(TLS_ID, int(key), signal)


def run():
    """execute the TraCI control loop"""
    # initialize subscriptions window for the first 20 steps
    for i in range(0, 20):
        add_sub_step()
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
                for vehicle_id in traci.inductionloop.getLastStepVehicleIDs(str(i)):
                    # vehicle_id = traci.inductionloop.getLastStepVehicleIDs(str(i))[0]
                    lane_id = traci.vehicle.getLaneID(vehicle_id)
                    vehicle_speed = traci.vehicle.getSpeed(vehicle_id)
                    # append vehicle in the lane queue
                    QUEUES[lane_id].append(vehicle_id)
                    first = QUEUES[lane_id][0]
                    # make vehicle reservation
                    if make_reservation(first, lane_id):
                        QUEUES[lane_id].pop(0)
                        # set green signal
                        set_traffic_light(lane_id, "G")
                    else:
                        traci.vehicle.slowDown(vehicle_id, 0, DISTANCE / vehicle_speed)
                        # set red signal
                        set_traffic_light(lane_id, "R")
        for i in range(8, 16):
            # whether a vehicle leaves the intersection
            if traci.inductionloop.getLastStepVehicleNumber(str(i)) > 0:
                vehicle_id = traci.inductionloop.getLastStepVehicleIDs(str(i))[0]
                # set normal vehicle speed
                traci.vehicle.setSpeed(vehicle_id, -1)
        step += 1
        # translate subscriptions window by 1 step
        add_sub_step()
        remove_sub_step()
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
                 "--tripinfo-output", "tripinfo.xml", "--collision.mingap-factor", "0"])
    run()
