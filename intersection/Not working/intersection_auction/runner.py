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


def reset_traffic_light():
    for key in LINKS:
        traci.trafficlight.setLinkState(TLS_ID, int(key), "r")


def create_new_auction(vehicle_id, lane_id, vehicle_speed, auction_end, intersection_time):
    vehicles = []
    lanes = []
    speeds = []
    bids = []
    vehicles.append(vehicle_id)
    lanes.append(lane_id)
    speeds.append(vehicle_speed)
    bids.append(random.randint(0, int(traci.vehicle.getParameter(vehicle_id, "wallet"))))
    QUEUE.append([traci.simulation.getTime(), auction_end, intersection_time, vehicles, lanes, speeds, bids])
    # [auction_start, auction_end, intersection_time, [list of vehicles], [list of lanes],
    # [list of speeds], [list of bids]]


def append_vehicle_to_auction(vehicle_id, lane_id, vehicle_speed, intersection_time):
    QUEUE[-1][2] += intersection_time
    QUEUE[-1][3].append(vehicle_id)
    QUEUE[-1][4].append(lane_id)
    QUEUE[-1][5].append(vehicle_speed)
    QUEUE[-1][6].append(random.randint(0, int(traci.vehicle.getParameter(vehicle_id, "wallet"))))


def run():
    """execute the TraCI control loop"""
    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        # give random wallet to spawning vehicles
        vehicle_ids = traci.simulation.getDepartedIDList()
        for vehicle_id in vehicle_ids:
            traci.vehicle.setParameter(vehicle_id, "wallet", str(random.randint(0, 50)))
        # vehicles approaching intersection
        for i in LANE_NUMBERS:
            # whether a vehicle enters in a detector
            if traci.inductionloop.getLastStepVehicleNumber(str(i)) > 0:
                # get vehicle data
                vehicle_id = traci.inductionloop.getLastStepVehicleIDs(str(i))[0]
                lane_id = traci.vehicle.getLaneID(vehicle_id)
                vehicle_speed = traci.vehicle.getSpeed(vehicle_id)
                auction_end = traci.simulation.getTime() + math.ceil(DISTANCE / vehicle_speed)
                intersection_time = math.ceil(INTERSECTION / vehicle_speed)
                if len(QUEUE) == 0:
                    create_new_auction(vehicle_id, lane_id, vehicle_speed,
                                       auction_end, intersection_time)
                else:
                    previous_auction_end = QUEUE[-1][1]
                    previous_intersection_end = QUEUE[-1][2]
                    previous_auction_vehicles = QUEUE[-1][3]
                    if len(previous_auction_vehicles) == 4 or auction_end > previous_auction_end:
                        create_new_auction(vehicle_id, lane_id, vehicle_speed,
                                           previous_auction_end + previous_intersection_end, intersection_time)
                    else:
                        append_vehicle_to_auction(vehicle_id, lane_id, vehicle_speed, intersection_time)
        if len(QUEUE) > 0:
            # actual auction parameters
            now = QUEUE[0][1]
            vehicles = QUEUE[0][3]
            lanes = QUEUE[0][4]
            speeds = QUEUE[0][5]
            bids = QUEUE[0][6]
            if len(vehicles) > 0:
                winner = bids.index(max(bids))
                winner_lane = lanes[winner]
                time_to_leave_crossing = math.ceil(now + INTERSECTION / speeds[winner])
                if traci.simulation.getTime() < time_to_leave_crossing:
                    set_traffic_light(winner_lane, "g")
                else:
                    print(QUEUE)
                    vehicles.pop(winner)
                    lanes.pop(winner)
                    speeds.pop(winner)
                    bids.pop(winner)
                    set_traffic_light(winner_lane, "r")
                    now = traci.simulation.getTime()
            else:
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
