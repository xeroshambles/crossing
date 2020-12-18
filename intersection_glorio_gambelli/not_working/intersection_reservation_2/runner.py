from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse

CONF_MATRIX = {
    "2to5_0": [],
    "2to5_1": ["3to5_1", "4to5_2", "1to5_1", "1to5_2"],
    "2to5_2": ["3to5_1", "3to5_2", "4to5_1", "1to5_2"],
    "3to5_0": [],
    "3to5_1": ["2to5_1", "2to5_2", "4to5_1", "1to5_2"],
    "3to5_2": ["2to5_2", "4to5_1", "4to5_2", "1to5_1"],
    "4to5_0": [],
    "4to5_1": ["2to5_2", "3to5_1", "3to5_2", "1to5_1"],
    "4to5_2": ["2to5_1", "3to5_2", "1to5_1", "1to5_2"],
    "1to5_0": [],
    "1to5_1": ["2to5_1", "3to5_2", "4to5_1", "4to5_2"],
    "1to5_2": ["2to5_1", "2to5_2", "3to5_1", "4to5_2"]
}

SUBSCRIPTIONS = {
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

EDGE_LENGTH = 86.4
STOP_DISTANCE = 60


def d(edges):
    return traci.simulation.getDistanceRoad(edges[0], EDGE_LENGTH, edges[1], EDGE_LENGTH)


# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa


def check_sub(vehicle_id):
    for k in SUBSCRIPTIONS:
        for el in SUBSCRIPTIONS[k]:
            if vehicle_id == el[0]:
                return True
    return False


def run():
    """execute the TraCI control loop"""
    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        # vehicles approaching intersection
        for i in range(0, 8):
            # whether a vehicle enters in a detector
            if traci.inductionloop.getLastStepVehicleNumber(str(i)) > 0:
                # get vehicle data
                vehicle_id = traci.inductionloop.getLastStepVehicleIDs(str(i))[0]
                if check_sub(vehicle_id):
                    break
                lane_id = traci.vehicle.getLaneID(vehicle_id)
                vehicle_speed = traci.vehicle.getSpeed(vehicle_id)
                waiting_time = 0
                # calculate the vehicle waiting time
                for conf_lane in CONF_MATRIX[lane_id]:
                    for sub in SUBSCRIPTIONS[conf_lane]:
                        waiting_time += sub[1]
                # modify vehicle speed
                if waiting_time != 0:
                    traci.vehicle.slowDown(vehicle_id, 6.95, waiting_time)
                # register subscription for the vehicle
                SUBSCRIPTIONS[lane_id].append((vehicle_id, waiting_time))
        # vehicles entering the intersection
        for i in range(8, 16):
            # whether a vehicle enters in a detector
            if traci.inductionloop.getLastStepVehicleNumber(str(i)) > 0:
                vehicle_id = traci.inductionloop.getLastStepVehicleIDs(str(i))[0]
                for k in SUBSCRIPTIONS:
                    for el in SUBSCRIPTIONS[k]:
                        # set vehicle max speed and remove vehicle subscription
                        if vehicle_id == el[0]:
                            traci.vehicle.setSpeed(vehicle_id, traci.vehicle.getMaxSpeed(vehicle_id))
                            SUBSCRIPTIONS[k].remove(el)
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
                             "--tripinfo-output", "tripinfo.xml", "--collision.mingap-factor", "0"])
    run()
