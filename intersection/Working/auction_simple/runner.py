from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
import random

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa

TLS_ID = "4"
INTERSECTION_TIME = 2

Q = {}

LANE_NUMBERS = [0, 1, 2, 3]

LINKS = {
    "0": ("0_0", "5_0"),
    "1": ("2_0", "7_0"),
    "2": ("4_0", "1_0"),
    "3": ("6_0", "3_0"),
}


# initialize lane queues
def init_queues():
    for i in LANE_NUMBERS:
        Q[str(i)] = []


# check if a vehicle already made a bid
def check_bid(vehicle_id):
    for lane in Q:
        for el in Q[lane]:
            if el[0] == vehicle_id:
                return True
    return False


def take_bid(elem):
    return elem[4]


# get first vehicles from every lane and sort them based on the bid they made
def get_first_bids():
    top_vehicles = []
    for lane in Q:
        if len(Q[lane]) > 0:
            top_vehicles.append(Q[lane][0])
    return sorted(top_vehicles, key=take_bid, reverse=True)


# set signal light for the given lane
def set_traffic_light(lane_id, signal):
    for key in LINKS:
        if key == lane_id:
            traci.trafficlight.setLinkState(TLS_ID, int(key), signal)
        else:
            traci.trafficlight.setLinkState(TLS_ID, int(key), "r")


def run():
    step = 0
    pay = 0
    a = 1
    vehicle_bids = []
    """execute the TraCI control loop"""
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        # give random wallet to spawning vehicles
        vehicle_ids = traci.simulation.getDepartedIDList()
        for vehicle_id in vehicle_ids:
            traci.vehicle.setParameter(vehicle_id, "wallet", str(random.randint(0, 50)))
            print("ID: %s, WALLET: %s" % (vehicle_id, traci.vehicle.getParameter(vehicle_id, "wallet")))
        # vehicles approaching intersection
        for i in LANE_NUMBERS:
            # whether a vehicle enters in a detector
            if traci.inductionloop.getLastStepVehicleNumber(str(i)) > 0:
                vehicle_id = traci.inductionloop.getLastStepVehicleIDs(str(i))[0]
                # whether a vehicle has not made a bid
                if not check_bid(vehicle_id):
                    Q[str(i)].append([vehicle_id, str(i), INTERSECTION_TIME, traci.simulation.getTime(),
                                      random.randint(0, int(traci.vehicle.getParameter(vehicle_id, "wallet")))])
        # take first vehicle from each lane once
        if a:
            vehicle_bids = get_first_bids()
            # adjust vehicles' times
            for i in range(0, len(vehicle_bids)):
                if i == 0:
                    vehicle_bids[i][3] = traci.simulation.getTime()
                else:
                    vehicle_bids[i][3] = vehicle_bids[i - 1][3] + 2
            # if there is only one vehicle in the auction, it doesn't bid
            if len(vehicle_bids) > 1:
                pay = 1
        if len(vehicle_bids) > 0:
            a = 0
            # whether the vehicle is stopped and has payed
            if traci.vehicle.getSpeed(vehicle_bids[0][0]) <= 0.1 and pay:
                traci.vehicle.setParameter(vehicle_bids[0][0], "wallet",
                                           int(traci.vehicle.getParameter(vehicle_bids[0][0],
                                                                          "wallet")) -
                                           vehicle_bids[0][4])
                print("ID: %s, WALLET AFTER BID: %s" % (vehicle_bids[0][0],
                                                        traci.vehicle.getParameter(vehicle_bids[0][0], "wallet")))
            # whether the vehicle is crossing the intersection
            if traci.simulation.getTime() - vehicle_bids[0][3] <= vehicle_bids[0][2]:
                # set green signal
                set_traffic_light(vehicle_bids[0][1], "g")
            else:
                # set red signal
                set_traffic_light(vehicle_bids[0][1], "r")
                # delete vehicle from queue
                Q[str(vehicle_bids[0][1])].pop(0)
                vehicle_bids.pop(0)
                if len(vehicle_bids) == 0:
                    a = 1
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
    init_queues()
    traci.trafficlight.setPhase(TLS_ID, "0")
    run()
