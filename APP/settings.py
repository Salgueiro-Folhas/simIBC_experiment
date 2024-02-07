# HOST_IP_LAYER_0 = '10.84.240.82'
# HOST_IP_LAYER_0 = '192.168.0.111'
HOST_IP_LAYER_0 = '192.168.10.111'
DIF = 1 # difficulty (suffix = '0' * difficulty)
PoS_Sim_Time = 7 #second
SIM_MODE = "relayer" #7# "relayer" or "superrelayer"
IBC_MODE = "AtoB"
IBC_MULTI_HOP = 3 #1~6
REF_COUNT = 1000
LEADER_UPDATE_INTERVAL = 45 # How often to send a heartbeat [s]
LEADER_CHECK_INTERVAL =  60 # Loop interval at which the leader checks for failure [s]
FAILURE = False
CR_INTERVAL = 30 # multi-layer consensus interval[s]
RANDOM_NUM_LoWer = 14
RANDOM_NUM_Upper = 28
ALLOWABLE_TIME = 200 # HEART_BEAT[s]
tkinter_state = False # tkinter.
CR_STATE = True # conssensus.
LEADER_AGGREGATION = True # Does the leader aggregate?

MINIMUM_DOMAIN = 3 # Minimum number of nodes to start multi-layer consensus
NEW_CONNECTION = 20 # [s] NEW_CONNECTION
CONFIRMED_BLOCK = 3 # Blocks shared by definite block history intersections
REF_RECHECK = 1 # [s] 
MINING_BLOCK_CHECK = 5 # [s] 

HOST_PORT_LAYER_0_origin = 50050 # Port number of the 0th origin node
HOST_PORT_LAYER_1_origin = HOST_PORT_LAYER_0_origin + 1 # Port number of the 0th and subsequent origin node(Layer-1)

# Layer-1
CHECK_INTERVAL = 5 # Block nongeneration interval [s]
Random_CHECK_INTERVAL_FLAG = False # Block nongeneration interval
CHECK_INTERVAL_LIST = [1 ,15 ,30]
TRANSACTION = 'AD9B477B42B22CDF18B1335603D07378ACE83561D8398FBFC8DE94196C65D806'

