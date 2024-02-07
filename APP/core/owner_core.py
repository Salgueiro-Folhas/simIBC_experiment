import time
import socket, threading, json
import copy
from time import sleep
import numpy as np
import hashlib
import logging
import datetime
from datetime import datetime, timedelta
import tkinter as tk
from settings import *

from signature.generate_sigunature import DigitalSignature
from signature.generate_sigunature import CheckDigitalSignature
from blockchain.blockchain_manager import BlockchainManager
from window.generate_window import MainWindow
from p2p.connection_manager_4owner import ConnectionManager4Owner
from p2p.my_protocol_message_handler import MyProtocolMessageHandler
from p2p.owner_node_list import OwnerCoreNodeList
from p2p.message_manager import (
	MSG_REQUEST_CROSS_REFERENCE,
	MSG_ACCEPT_CROSS_REFFERENCE,
	LEADER_AGGREGATION_START_CROSS_REFFERENCE,
	MSG_CROSS_REFFERENCE_LEADER_AGGREGATION,
	REQUEST_POW,
	MSG_CROSS_REFFERENCE,
	START_CROSS_REFFERENCE,
	COMPLETE_CROSS_REFERENCE,
	MSG_IBC_START,
	MSG_IBC_SEND,
	MSG_IBC_FIN,
	MSG_IBC_RECEIVE,
	MSG_IBC_NEXT_CHAIN1,
	MSG_IBC_NEXT_CHAIN2,
	MSG_IBC_NEXT_CHAIN3,
	MSG_IBC_NEXT_CHAIN4,
	MSG_IBC_NEXT_CHAIN5,
	MSG_IBC_NEXT_CHAIN6,
	RAFT_CANDIDATE_LEADER,
	U_RAFT_FOLLOWER,
	IM_RAFT_LEADER,
	RAFT_HEARTBEAT,
)

from cross_reference.cross_reference_manager import CrossReferenceManager
# from cross_reference.ibc_manager import IBCManager
# from cross_reference.cross_reference_resistance import CrossReferenceResistance

STATE_INIT = 0
STATE_STANDBY = 1
STATE_CONNECTED_TO_NETWORK = 2
STATE_SHUTTING_DOWN = 3

class OwnerCore(object):

	def __init__(self, my_port = 50082, owner_node_host=None, owner_node_port=None  ):
		self.server_state = STATE_INIT
		print('Initializing owner server...')
		self.my_ip = self.__get_myip()
		print('Server IP address is set to ... ', self.my_ip)
		self.my_port = my_port
		self.cm = ConnectionManager4Owner(self.my_ip, self.my_port, self.__handle_message, self )
		self.mpmh = MyProtocolMessageHandler()
		self.owner_node_host = owner_node_host
		self.owner_node_port = owner_node_port
		self.gs = DigitalSignature()
		self.ww = MainWindow(self.my_port)
		self.bmc = BlockchainManager()
		self.create_log()
		self.tkinter_state = tkinter_state #tkinter
		self.Raft_initial()
		self.CR_initial()
		self.Experiment_initial()
		logging.debug('debug_msg : END __init__')

	def CR_initial(self):
		self.CR_Last_stamp = time.time()
		self.AC = 0
		self.Accept_list = [] #Accept Count
		self.Ccount = 0 
		self.Send_list = []
		self.REcount = 0
		self.RE_Send_list = []
		self.check_count = None
		self.previous_cross_sig = []
		self.CR_INTERVAL = CR_INTERVAL
		self.CR_state = CR_STATE
		self.IBC_send_list = []
		logging.debug('debug_msg : END CR_initial')
		self.IBC_MODE = IBC_MODE
		self.IBC_multihop = IBC_MULTI_HOP
		self.P_msg = None
		self.P_msg_to_peer = self.get_nx_peer()

	def Raft_initial(self):
		self.Raft_Voting = 0
		self.Voting_Result = []
		self.Candidate = False
		self.Raft_timer = 0		
		self.CR_count = 0
		self.Raft_Leader_state = None
		self.Raft_Voting_state = False
		self.Leader_C = 0
		self.Lastping_leader = 0 
		self.Last_Heartbeat_time()
		logging.debug('debug_msg : END Raft_initial')

	def Experiment_initial(self):
		self.Phase1_list = []
		self.Phase3_list = []
		self.overtime_c = 0
		self.overtime_flag = False
		logging.debug('debug_msg : END CR_Experiment_initial')
		self.inter_list = []

	def start(self, crm = None, ibc = None ):
		self.server_state = STATE_STANDBY
		self.cm.start()

		if SIM_MODE == "superrelayer":#7#
			self.crm = crm
			print("!!!!!!!! __init__(crm) !!!!!!!!")#7#

		elif SIM_MODE == "relayer":
			self.ibc = ibc
			print("!!!!!!!! __init__(ibc) !!!!!!!!")#7#

		else:
			print("!!!!!!!! CAUTION !!!!!!!!")#7#

		self.Raft_Leader_state = True#if
		self.Raft_Leader_loop() #7#モードによって起動するの仕方を変える必要あり。

	def window(self):
		if tkinter_state == True:
			self.ww.generate_genesis_window()

		else:
			logging.debug('debug_msg : Tkinter off')
			pass

	def create_log(self):
		try:
			file_name = "logging/raft_status" + str(self.my_port) + ".log"
			formatter = '%(asctime)s: %(message)s'
			logging.basicConfig(format=formatter, filename= file_name, level = logging.INFO)
			
		except:
			file_name = "APP/logging/raft_status" + str(self.my_port) + ".log"
			formatter = '%(asctime)s: %(message)s'
			logging.basicConfig(format=formatter, filename= file_name, level = logging.INFO)

	def join_DMnetwork(self):
		logging.info('debug_msg : join_DMnetwork')
		if self.owner_node_host != None:
			logging.info('debug_msg : join_DMnetwork')
		
			self.server_state = STATE_CONNECTED_TO_NETWORK
			self.cm.join_DMnetwork(self.owner_node_host, self.owner_node_port)
			self.Raft_Leader_state = False
			logging.debug('Raft_Leader_state:' + str(self.Raft_Leader_state))
			self.Raft_Follower_loop()

		else:
			print('This server is running as Genesis Owner Node...')
			logging.info('This server is running as Genesis Owner Node...')
			self.Raft_Leader_state = True
			self.Raft_Leader_loop()

	def Last_Heartbeat_time(self):
		print("Last_Heartbeat_time")
		self.Last_Heartbeat = time.time()
		print("Last_Heartbeat is ",self.Last_Heartbeat)
		print(datetime.fromtimestamp(self.Last_Heartbeat))

	def Time_judge_is_Follower(self):
		self.Follower_time = time.time()
		if  self.Follower_time < self.Last_Heartbeat + ALLOWABLE_TIME:
			print("Renew_Last_Heartbeat", float(self.Last_Heartbeat + ALLOWABLE_TIME ))
			print("Last_Heartbeat",self.Last_Heartbeat)
			print("self.Raft_Voting_state", self.Raft_Voting_state)
			self.Raft_Follower_side = threading.Timer(LEADER_CHECK_INTERVAL, self.Time_judge_is_Follower)
			self.Raft_Follower_side.start()

		else:
			print("Renew_Last_Heartbeat", float(self.Last_Heartbeat + ALLOWABLE_TIME))
			print("Last_Heartbeat", self.Last_Heartbeat)
			print("Follower_time is ", self.Follower_time)
			logging.info('debug_msg : Candidate')
			print("self.Raft_Voting_state", self.Raft_Voting_state)
			self.Raft_Candidate_Leader()

	def shutdown(self):
		self.server_state = STATE_SHUTTING_DOWN
		print('Shutdown server...')
		self.cm.connection_close()

	def Raft_Follower_loop(self):
		logging.info('debug_msg : Follower_loop')
		print("000000000000000000000000Follower_loop000000000000000000000000")
		self.Time_judge_is_Follower()
		
	def Raft_Leader_loop(self):
		CR_stamp = time.time()
		logging.info('1111111111111111111111111Leader_loop1111111111111111111111111')
		print("1111111111111111111111111Leader_loop1111111111111111111111111")
		# if SIM_MODE == "relayer":
		# 	print("&&&")
		# 	print("&&&")
		# 	print("CR_loop")
		# 	print("&&&")
		# 	print("&&&")
		# 	print("&&&")
		# 	logging.info("CR_loop")
		# 	rng = np.random.default_rng()
		# 	inter = rng.integers(14, 28)
		# 	self.inter_list.append(inter)
		# 	self.Leader_loop = threading.Timer(inter, self.CR_loop())
		# 	print("!!!!!!!!!!!!!!!!!!!!次の周期は", inter)
		# 	self.Leader_loop.start()
		# 	self.Raft_timer_for_Leader()
		# else :
		if self.ww.Break_state == True:
			self.Leader_broken()

		else:
			if SIM_MODE == "relayer":
				rng = np.random.default_rng()
				inter = rng.integers(RANDOM_NUM_LoWer, RANDOM_NUM_Upper)
				self.inter_list.append(inter)
				self.Leader_loop = threading.Timer(inter, self.CR_loop())
				print("!!!!!!!!!!!!!!!!!!!!次の周期は", inter)
				self.Leader_loop = threading.Timer(inter, self.Raft_timer_for_Leader)
				self.Leader_loop.start()
			else :
				self.Leader_loop = threading.Timer(LEADER_UPDATE_INTERVAL, self.Raft_timer_for_Leader)
				self.Leader_loop.start()

		logging.debug("CR_check_stamp" + str(CR_stamp))
		logging.debug("self.CR_Last_stamp" + str(self.CR_Last_stamp))

		if self.CR_INTERVAL < CR_stamp - self.CR_Last_stamp :
			logging.info("CR_loop")
			self.CR_loop()

		else :
			logging.info("Last consensus is" + str(CR_INTERVAL))

	def Leader_broken(self):
		logging.debug('break down. sleep(10000000)' + str(self.my_port))
		while True:
			sleep(5)
			if self.ww.Break_state == False:
				self.Raft_Leader_state = False
				self.Raft_Follower_loop()

	def Raft_reset(self):
		self.Voting_Result = []
		self.Raft_Voting = 0
		self.Candidate = False
		self.Raft_Voting_state = False
		self.Leader_C = 0
		
	def Send_heartbeat(self):
		logging.info("Send_heartbeat")
		if self.Raft_Leader_state == True:
			self.Lastping_leader = time.time()

		else :
			logging.debug('Not a leader...')

	def Raft_timer_for_Leader(self):
		RenewLastping_Leader = time.time()
		if self.Raft_Leader_state == True:
			if RenewLastping_Leader - self.Lastping_leader > 5:
				new_message = self.cm.get_message_text(RAFT_HEARTBEAT)
				self.cm.send_msg_to_all_owner_peer(new_message)
				logging.info("Continuation of leadership" + str(self.my_ip) + "," + str(self.my_port))
				print("Continuation of leadership")			
				self.Raft_Leader_loop()

			else:
				print("Last ping within 5 s")
				logging.info('Last ping within 5 s')
				self.Raft_Leader_loop()

		else :
			print("Leader rights are gone. Or voting mode")
			logging.debug('Leader rights are gone. Or voting mode')

	def Raft_Candidate_Leader(self):
		logging.debug('candidate for leader' + str(self.my_ip) + "," + str(self.my_port))
		print("candidate for leader")
		if self.Raft_Voting_state == True:
			print("voting mode.")
			self.Candidate = False
			logging('voting mode.')
			print("Follower")
			self.Raft_Follower_loop()

		else:
			self.Raft_Voting_state = True
			print("voting mode.")
			new_message = self.cm.get_message_text(RAFT_CANDIDATE_LEADER)
			self.cm.send_msg_to_all_owner_peer(new_message)
			logging.debug('RAFT_CANDIDATE_LEADER')

	def CR_loop(self):
		logging.info('CR_loop')
		if SIM_MODE == "superrelayer":#7#
			n = self.crm.ref_block_number
			logging.info("block num : " + str(n))
			if self.CR_state == True:
				if self.cm.adding_timer + NEW_CONNECTION < time.time():
					self.CR_Last_stamp = time.time()
					if len(self.cm.owner_node_set.get_list()) > MINIMUM_DOMAIN:
						self.CR_count += 1
						self.request_cross_reference()
						logging.debug(str(self.CR_count))
						
					else:
						logging.debug(str(len(self.cm.owner_node_set.get_list())))
						
				else:
					logging.debug("New connection is" + str(NEW_CONNECTION) + "s") 
					print("")

			else:
				print("Not making an consensus for a reason.")
				logging('Not making an consensus for a reason.')
    
		elif SIM_MODE == "relayer":#7#
			n = self.ibc.ref_block_number
			logging.info("block num : " + str(n))
			print("CR_loopのIBCやで")
			if self.CR_state == True:
				if self.cm.adding_timer + NEW_CONNECTION < time.time():
					self.CR_Last_stamp = time.time()
					if len(self.cm.owner_node_set.get_list()) > MINIMUM_DOMAIN:
						self.CR_count += 1
						self.ibc.time_start_IBC()
						self.request_cross_ibc() #7#
						logging.debug(str(self.CR_count))
						print("ここ終わってないやで")
						
					else:
						logging.debug(str(len(self.cm.owner_node_set.get_list())))
						
				else:
					logging.debug("New connection is" + str(NEW_CONNECTION) + "s") 
					print("New connection is" + str(NEW_CONNECTION) + "s")

			else:
				print("Not making an consensus for a reason.")
				logging.debug('Not making an consensus for a reason.')


		else:
			print("SIM_MODEが設定されていません。")


#-----------------------------------------------------------------------------------------------------------------------------------------
	def request_cross_reference(self):
		self.crm.time_start_phase1()
		self.check_count = 11
		print(" ============= Phase1 start =============")
		self.crm.inc += 1
		print("start_request_cross_reference")
		self.Send_heartbeat()
		if LEADER_AGGREGATION == True:
			self.cross_reference_reset()
		new_message = self.cm.get_message_text(MSG_REQUEST_CROSS_REFERENCE)
		self.cm.send_msg_to_all_owner_peer(new_message)

	def start_cross_reference(self):
		print("start_request_cross_reference")
		block_l = json.dumps(self.crm.block_ref())
		block_msg = self._get_hash_sha256(block_l)
		self.crm.add_cross_reference(block_msg)
		self.crm.myblock_in = True
		new_message = self.cm.get_message_text(MSG_CROSS_REFFERENCE, json.dumps(block_msg, sort_keys = True ,ensure_ascii = False))
		print("============= start_request_cross_reference =============")
		logging.info("============= start_request_cross_reference =============")
		self.Send_heartbeat()
		self.cm.send_msg_to_all_owner_peer(new_message)

	def cross_sig(self, cre):
		cross_sig = self.gs.add_public_key(cre)
		return cross_sig

	def _get_hash_sha256(self, message):
		return hashlib.sha256(message.encode()).hexdigest()

	def complete_cross_block(self, msg):
		logging.info("complete_cross_block()")
		if LEADER_AGGREGATION == True:
			new_message = self.cm.get_message_text(COMPLETE_CROSS_REFERENCE, msg)
			self.Send_heartbeat()
			self.cm.send_msg_to_all_owner_peer(new_message)
			
		else:
			self.cross_reference_reset()
			new_message = self.cm.get_message_text(COMPLETE_CROSS_REFERENCE, msg)
			self.Send_heartbeat()
			self.cm.send_msg_to_all_owner_peer(new_message)
		
	def cross_reference_reset(self):
		print("cross_reference_ALL RESET")
		print("refresh crossre ference pool")
		self.crm.clear_cross_reference()
		print( "refresh crossre ference pool")
		logging.debug("clear self.crm.cross_reference is" + str(self.crm.cross_reference))
		self.AC = 0 # Reset
		self.Ccount = 0
		self.REcount = 0
		# self.crm.flag = False
		self.crm.myblock_in = False
		logging.info("cross_reference_reset is ok----Full-Reset")
		print("ok----Full-Reset")

	def myblock_in_check(self):
		logging.debug("myblock_in_check")
		if self.crm.myblock_in == True: 
			msg = self.crm.hysteresis_sig()
			self.crm.set_new_cross_reference(msg)
			print(" ============= Phase2 start =============")
			logging.debug("myblock_in_check")
			if LEADER_AGGREGATION == True:
				self.cross_reference_reset()
				new_message = self.cm.get_message_text(REQUEST_POW, msg)
				self.Send_heartbeat()
				self.cm.send_msg_to_all_owner_peer(new_message)
				
			else:
				complete = threading.Timer(30, self.complete_cross_block(msg))
				complete.start()
				return 0

		else:
			recheck = threading.Timer(REF_RECHECK, self.myblock_in_check)
			recheck.start()	
			return 1

#7#  ============= IBC ============= 

	def request_cross_ibc(self):
		self.check_count = 11
		print(" ============= IBC_Phase1 start_IBC =============")
		self.ibc.inc += 1
		print("start_request_cross_ibc")
		self.Send_heartbeat()
		self.cross_ibc_reset()
		Current_IBC_list = str(copy.deepcopy(self.cm.owner_node_set.get_list())).strip("}").strip("{").split('), ')
		block_info = self.ibc_block_info() #55# "block_info"
		msg = {
			block_info:Current_IBC_list
		}
		new_message = self.cm.get_message_text(MSG_IBC_START, msg) #7#
		if IBC_MODE == "AtoN":
			peer = self.get_nx_peer()
			print(type(peer))
		else :
			peer = self.confirm_ibc_address(Current_IBC_list)
			print(" =========== confirm_ibc_address(Current_IBC_list) =========== ", peer)
		self.cm.send_msg(peer ,new_message, delay = False)
		
	def confirm_ibc_address(self, confirm_IBC_list):
		print(" =============================== ", len(confirm_IBC_list))
		print(" =============================== ", confirm_IBC_list)
		print(" =============================== ", len(confirm_IBC_list))
		print(" =============================== ", confirm_IBC_list)		
		x = 1
		peer = confirm_IBC_list[-x].strip( ).strip("(").strip(")]").replace("'", "").split(", ")
		print(" =============================== ")
		if str(self.my_port) in peer:
			x = 2
			print(" =========== WARNING =========== " ,self.my_port)
			print(" =========== WARNING =========== " ,peer)
			peer = confirm_IBC_list[-x].strip( ).strip("(").strip(")]").replace("'", "").split(", ")
			
		if str(self.owner_node_port) in peer:
			x = 3
			print(" =========== WARNING =========== " ,self.my_port)
			print(" =========== WARNING =========== " ,peer)
			peer = confirm_IBC_list[-x].strip( ).strip("(").strip(")]").replace("'", "").split(", ")
		print(" =============================== ", x)
		
		return peer

	def start_ibc(self): #7#
		print("============= start_request_cross_ibc =============")
		logging.info("============= start_request_cross_ibc =============")
		new_message = self.cm.get_message_text(MSG_IBC_SEND, json.dumps(str(self.my_port), sort_keys = True ,ensure_ascii = False))
		# self.Send_heartbeat()
		# self.cm.send_msg()

	# def start_cross_ibc(self):#7#
	# 	print("start_request_cross_ibc")
	# 	block_l = json.dumps(self.crm.block_ref())
	# 	# block_msg = self._get_hash_sha256(block_l)
	# 	# self.crm.add_cross_reference(block_msg)
	# 	# self.crm.myblock_in = True
	# 	new_message = self.cm.get_message_text(MSG_, json.dumps(block_l, sort_keys = True ,ensure_ascii = False))
	# 	print("============= start_request_cross_ibc =============")
	# 	logging.info("============= start_request_cross_ibc =============")
	# 	self.Send_heartbeat()
	# 	self.cm.send_msg_to_all_owner_peer(new_message)

	def ibc_block_info(self): #↓取得：https://atomscan.com/transactions/85A8BBB7D2DE5AC8519EEDCD6A989F179CE3BAE70D22833D4BFB06B7AAEE29BA
		block_info = {
			"@type": "/ibc.core.channel.v1.MsgAcknowledgement",
			"packet": {
				"sequence": "86100",
				"source_port": "transfer",
				"source_channel": "channel-220",
				"destination_port": "transfer",
				"destination_channel": "channel-1",
				"data": "eyJhbW91bnQiOiIxMTAzIiwiZGVub20iOiJ1YXRvbSIsInJlY2VpdmVyIjoiaW5qMXlubTl3ZGtyMmg2N2tqZnpmMHVtOWozdWU5ZHA1bnY4ajdtNnF6Iiwic2VuZGVyIjoiY29zbW9zMWVtajltZ2V4NTY1YXQwaDBmampoODQ5dWo5c3E5NW53Y3lycHFlIn0=",
				"timeout_height": {
				"revision_number": "0",
				"revision_height": "0"
				},
				"timeout_timestamp": "1705772979000000000"
			},
			"acknowledgement": "eyJyZXN1bHQiOiJBUT09In0=",
			"proof_acked": "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",
			"proof_height": {
				"revision_number": "1",
				"revision_height": "57981024"
			},
			"signer": "cosmos1l267dmlmprhu4p5aqslf50f495vjqlg3a52yjt",
			"amount": {
				"amount": 1103,
				"denom": "uatom"
			}
			}
		return str(block_info)

	def current_crossref(self, msg):
		self.crm.add_cross_reference(msg)

	def current_IBC(self, msg):
		self.ibc.add_IBC(msg)

	def ibc_in_my_block(self, ibc_block, peer_list):
		print("============= ibc_in_my_block =============")
		print("============= ibc_in_my_block =============", ibc_block)
		print("============= ibc_in_my_block =============", type(ibc_block))
		print("============= ibc_in_my_block =============", peer_list)
		print("============= ibc_in_my_block =============", type(peer_list))
		self.ibc.in_block(ibc_block, peer_list)

	def myibcblock_in_check(self):
		print("============= (((!!!))) =============", self.ibc.myblock_in)
		if self.ibc.myblock_in == True:
			self.send_NEXT_IBC()
			self.cross_ibc_reset()
		else:
			AAA = threading.Timer(0.1, self.myibcblock_in_check)
			AAA.start()
      
	def send_NEXT_IBC(self):
		if IBC_MODE == "AtoB":
			peer = (self.owner_node_host, self.owner_node_port)
			print("PPPPPPPPPPPPPPP", peer)
			print("PPPPPPPPPPPPPPP", peer)
			new_message = self.cm.get_message_text(MSG_IBC_FIN) #7#
			self.cm.send_msg(peer ,new_message, delay = False)
			
		else :
			print("=")
			print("=")
			print(self.ibc.cross_IBC)
			print(self.ibc.path_list)
			print("=")
			print("=")
			print(self.ibc.cross_IBC[:])
			print(self.ibc.path_list[:])
			print(type(self.ibc.cross_IBC[:]))
			print(type(self.ibc.path_list[:]))
			print("=")
			print("=")
			print("=")
			print("=")
			print(str(self.ibc.path_list[:]))
			print("=")
			block_onfo = self.ibc.cross_IBC[:]
			IBC_path_list = self.ibc.path_list[:]
			msg = self.ibc_block_info()
			# msg = {
			# 	str(block_onfo):str(IBC_path_list)
			# }
			print("AAAAAAAA self.IBC_MODE AAAAAAAA", self.IBC_MODE)
			if self.IBC_MODE == "AtoC":
				peer = (self.owner_node_host, self.owner_node_port)
				print("PPPPPPPPPPPPPPP", peer)
				print("PPPPPPPPPPPPPPP", peer)
				new_message = self.cm.get_message_text(MSG_IBC_FIN, msg) #7#
				self.cm.send_msg(peer ,new_message, delay = False)

			elif self.IBC_MODE == "AtoN":
				print("#####")
				print("#####")
				print("ここまで来てる？", self.P_msg_to_peer)
				print("ここまで来てる？", type(self.P_msg_to_peer))
				print("#####")
				print("#####")
				new_message = self.cm.get_message_text(self.P_msg, msg) #7#
				self.cm.send_msg(self.P_msg_to_peer ,new_message, delay = False)

			else:
				new_message = self.cm.get_message_text(MSG_IBC_NEXT_CHAIN, msg) #7#
				self.cm.send_msg(self.nx_peer ,new_message, delay = False)

	def cross_ibc_reset(self): #7#
		print("cross_reference_ALL RESET")
		print("refresh crossre ference pool")
		self.ibc.clear_IBC() #cross_reference()←変更
		# ここがCRのたびにリセットされているな
		print( "refresh crossre ference pool")
		logging.debug("clear self.crm.cross_reference is" + str(self.ibc.cross_IBC))
		self.AC = 0 # Reset
		self.Ccount = 0
		self.REcount = 0
		# self.crm.flag = False
		self.ibc.myblock_in = False
		logging.info("cross_reference_reset is ok----Full-Reset")
		print("ok----Full-Reset")

	def get_nx_peer(self):
		print("get_address")
		owner_node = copy.deepcopy(self.cm.owner_node_set.get_list())
		target_address = self.my_port + 2
		for C_peer_address in owner_node:
			if target_address in  C_peer_address:
				print("=")
				print("=")
				print("=")
				print("= 次回送り先が確定 =", C_peer_address)
				print("=")
				print("=")
				print("=")
				return C_peer_address

	def __handle_message(self, msg, is_owner, peer=None):
		if self.ww.Break_state == True:
			logging.debug("break down")
			pass

		elif msg[2] == MSG_REQUEST_CROSS_REFERENCE:
			self.crm.time_start_phase1()
			self.cross_reference_reset()
			print("cross_reference_ALL RESET")
			print("refresh crossre ference pool")
			logging.debug('MSG_REQUEST_CROSS_REFERENCE:')
			print("MSG_REQUEST_CROSS_REFERENCE:")
			new_message = self.cm.get_message_text(MSG_ACCEPT_CROSS_REFFERENCE)
			self.cm.send_msg(peer, new_message, delay = False) 

		elif msg[2] == MSG_ACCEPT_CROSS_REFFERENCE: 
			logging.debug('MSG_ACCEPT_CROSS_REFFERENCE')
			print("MSG_ACCEPT_CROSS_REFFERENCE")
			print("self.o_list.get_list = ", self.cm.owner_node_set.get_list())

			if self.AC == 0:
				self.AC = 1
				self.Accept_list = copy.deepcopy(self.cm.owner_node_set.get_list())
				if peer in self.Accept_list:
					self.Accept_list.remove(peer)
			elif self.AC >= 1:
				if peer in self.Accept_list:
					self.Accept_list.remove(peer)
			else:
				pass

			if len(self.Accept_list) == 1: #Accept Count
				print("ok----------------------------ACCEPT_CROSS_REFERENCE")
				print("SEND_START")
				self.check_count = 22

				if LEADER_AGGREGATION == True:
					block_l = json.dumps(self.crm.block_ref())
					block_msg_M = self._get_hash_sha256(block_l)
					c = self.gs.compute_digital_signature(block_msg_M)
					logging.debug('self.gs.get_private_key' + str(c))
					logging.debug('block_msg' + str(block_l))
					msg_d = {
						c + "__PORT(" + str(self.my_port) + ")":block_msg_M + "__(Block_Hash)"
					}
					logging.debug("block_hash" + str(msg_d))
					self.current_crossref(msg_d)
					
					logging.debug("self.crm.cross_reference is :" + str(self.crm.cross_reference))
					
					new_message = self.cm.get_message_text(LEADER_AGGREGATION_START_CROSS_REFFERENCE)
					self.cm.send_msg_to_all_owner_peer(new_message)
					self.Send_heartbeat()
					
				else:
					new_message = self.cm.get_message_text(START_CROSS_REFFERENCE)
					self.cm.send_msg_to_all_owner_peer(new_message)
					self.Send_heartbeat()
					print("accept next")
					self.start_cross_reference()

		elif msg[2] == START_CROSS_REFFERENCE: 
			logging.info(START_CROSS_REFFERENCE)
			print("START_CROSS_REFFERENCE")
			if LEADER_AGGREGATION == False:
				self.start_cross_reference()

			else:
				logging.debug("Modes in which failing leaders aggregate")

		elif msg[2] == MSG_CROSS_REFFERENCE_LEADER_AGGREGATION: 
			logging.info('MSG_CROSS_REFFERENCE_LEADER_AGGREGATION @' + str(peer))

			msg_loads = json.loads(msg[4])

			print("HASH:" ,msg_loads)	

			if self.Ccount == 0:
				self.Ccount = 1
				self.Send_list = copy.deepcopy(self.cm.owner_node_set.get_list())
				logging.debug("sendlist is" + str(self.Send_list))
				
				if peer in self.Send_list:
					self.Send_list.remove(peer)
					self.current_crossref(msg_loads)
					logging.critical("A-1")
				else:
					logging.critical("A-2")
					pass
			elif self.Ccount >= 1:
				if peer in self.Send_list:
					self.Send_list.remove(peer)
					self.current_crossref(msg_loads)
					logging.critical("B-1")
				else:
					logging.critical("B-2")
					pass
			else:
				logging.critical("C")
				pass

			if len(self.Send_list) == 1:
				logging.debug("CROSS_REFERENCE_ACCEPT_ALL_NODE")
				msg = self.crm.hysteresis_sig()
				logging.debug("msg is :" + str(type(msg)))
				self.crm.set_new_cross_reference(msg)
				print("self.reference", self.crm.reference)
				print("============== type ==============" + str(type(self.crm.reference)))
				logging.debug("self.reference" + str(self.crm.reference))
				logging.debug("======= type =======" + str(type(self.crm.reference)))
				block_msg_C = self.crm.get_reference_pool()
				print("block_msg_C", block_msg_C)
				print("block_msg_C", type(block_msg_C))
				logging.debug("block_msg_C" + str(block_msg_C))
				logging.debug("======= type =======" + str(type(block_msg_C)))
				new_message = self.cm.get_message_text(REQUEST_POW, json.dumps(block_msg_C, sort_keys = True ,ensure_ascii = False))
				logging.info("REQUEST_POW")
				self.cm.send_msg_to_all_owner_peer(new_message)
				print("============= self.crm.time_stop_phase1() =============")
				phase1_time = self.crm.time_stop_phase1()
				self.crm.phase1_list.append(phase1_time)
				print("self.crm.Phase1_list", self.crm.phase1_list)
				print(" ============= Phase2 start =============")
				
		elif msg[2] == REQUEST_POW:
			print("REQUEST_POW")
			logging.debug("REQUEST_POW == msg[4] ==" + str(type(msg[4])))
			msg_loads = json.loads(msg[4])
			logging.debug("msg_loads is " + str( msg_loads))
			logging.debug("msg_loads is type is" + str(type(msg_loads)))
			self.crm.cross_reference = eval(msg_loads)
			msg = self.crm.hysteresis_sig()
			logging.debug("=================== msg is =================== 1 : " + str(msg))			
			self.crm.set_new_cross_reference(msg)
			# print("msg is : " + str(type(msg)))
			phase1_time = self.crm.time_stop_phase1()
			self.crm.phase1_list.append(phase1_time)
			print("phase1 time is :", phase1_time)
			logging.debug("=================== msg is =================== 1: " + str(type(msg)))
			print(" ============= Phase2 start ============= ")
			logging.info(" ============= Phase2 start ============= ")

			
		elif msg[2] == LEADER_AGGREGATION_START_CROSS_REFFERENCE:
			logging.debug('LEADER_AGGREGATION_START_CROSS_REFFERENCE @' + str(peer)) # @LEADER
			print("start_crose_reference")
			block_l = json.dumps(self.crm.block_ref())
			block_msg = self._get_hash_sha256(block_l)
			self.crm.myblock_in = True
			c = self.gs.compute_digital_signature(block_msg)
			logging.debug('block_msg' + str(block_l))
			msg_d = {
				c + "__PORT(" + str(self.my_port) + ")":block_msg + "__(Block_Hash)"
			}
			logging.debug("block_hash" + str(msg_d))
			new_message = self.cm.get_message_text(MSG_CROSS_REFFERENCE_LEADER_AGGREGATION, json.dumps(msg_d, sort_keys = True ,ensure_ascii = False))
			print("============= start_cross_reference__Leader_aggregation =============")
			logging.info("============= start_cross_reference__Leader_aggregation =============")
			self.cm.send_msg(peer ,new_message, delay = False)
			logging.info("MSG_CROSS_REFFERENCE_LEADER_AGGREGATION")
			self.Send_heartbeat

		elif msg[2] == MSG_CROSS_REFFERENCE:
			logging.debug('MSG_CROSS_REFFERENCE @' + str(peer))
			print("received : MSG_CROSS_REFFERENCE")
			print("Phase1-1")
			msg_loads = json.loads(msg[4])

			print("HASH:" ,msg_loads)	

			if self.Ccount == 0:
				self.Ccount = 1
				self.Send_list = copy.deepcopy(self.cm.owner_node_set.get_list())
				logging.debug("sendlist is" + str(self.Send_list))
				
				if peer in self.Send_list:
					self.Send_list.remove(peer)
					self.current_crossref(msg_loads)
					logging.critical("A-1")
				else:
					logging.critical("A-2")
					pass
			elif self.Ccount >= 1:
				if peer in self.Send_list:
					self.Send_list.remove(peer)
					self.current_crossref(msg_loads)
					logging.critical("B-1")
				else:
					logging.critical("B-2")
					pass
			else:
				logging.critical("C")
				pass

			if len(self.Send_list) == 1:
				logging.debug("CROSS_REFERENCE_ACCEPT_ALL_NODE")
				check = self.myblock_in_check() 
				logging.debug("block-check-while" + str(check))
				if check == 0:
					logging.debug("block-check" + str(check))
				
				else:
					logging.debug("block-check" + str(check))

		elif msg[2] == COMPLETE_CROSS_REFERENCE:
			print(" ==== OK ==== COMPLETE_CROSS_REFERENCE ==== ")
			logging.debug(" ==== OK ==== COMPLETE_CROSS_REFERENCE ==== ")

#------------------------------ relayer_IBC --------------------------------------------------
		elif msg[2] == MSG_IBC_START:
			print("MSG_IBC_START")
			logging.debug('MSG_IBC_START @' + str(peer)) # @LEADER
			if self.IBC_MODE =="AtoN": 
				self.P_msg_to_peer = self.get_nx_peer()
				self.P_msg = MSG_IBC_NEXT_CHAIN1
			msg_loads = msg[4]
			block_info = list(msg_loads.keys())
			receive_list = list(msg_loads.values())
			# 入力値から不要な文字を取り除く
			cleaned_values = [value.replace("(", "").replace(")", "") for value in receive_list[0]]
			# 整形されたリストを出力
			C_list = [tuple(value.split(', ')) for value in cleaned_values]
			CC_list = ",".join(",".join(map(str, tpl)) for tpl in C_list)
			self.IBC_send_list = CC_list.split(",")
			print(self.IBC_send_list)
			print(" =============================== ")
			print(" ==== OK ==== MSG_IBC_START ==== ", type(self.IBC_send_list[0]), type(self.IBC_send_list[1]))
			print(" ==== OK ==== MSG_IBC_START ==== ", self.IBC_send_list[0], self.IBC_send_list[1])
			print(" =============================== ") 

			R = len(self.IBC_send_list)
			self.peer_list = []
			for x in range(R):  # 例として範囲を10としますが、実際の範囲は問題によります
				if x % 2 == 1:  # xが奇数の場合
					pass  # 何もしない
				else: # xが偶数の場合の処理
					# print(f"{x}は偶数です。")
					self.peer_list.append(f"{self.IBC_send_list[x]}, {self.IBC_send_list[x+1]}")
			print(" =============================== ")
			print(" ==== OK ==== MSG_IBC_START ==== ", type(self.peer_list[0]), type(self.IBC_send_list[1]))
			print(" ==== OK ==== MSG_IBC_START ==== ", self.peer_list[0], self.peer_list[1])
			print(" ==== OK ==== MSG_IBC_START ==== ", type(self.peer_list), self.peer_list)
			print(" =============================== ") 

			for item in self.peer_list:
				if str(self.my_port) in item:
					self.peer_list.remove(item)
					print(" ===============================remove!!!! ", item) 

			peer = self.peer_list[0]
			# if str(self.my_port) in peer:
			# 	x = 1
			# 	print(" =========== WARNING =========== " ,self.my_port)
			# 	print(" =========== WARNING =========== " ,peer)
			# 	peer = self.peer_list[x]		
			
			if str(self.owner_node_port) in peer:
				# if :
				y = 1
				print(" =========== WARNING =========== " ,self.my_port)
				print(" =========== WARNING =========== " ,peer)
				peer = self.peer_list[-y]
				print(" =============================== ", y)
			
			# self.nx_peer = self.confirm_ibc_address(self.peer_list)
			self.ibc.IBC_state = "WIP-IBC"
			print("========= Tarn to WIP-IBC =========",self.ibc.IBC_state)
			self.ibc_in_my_block(block_info ,self.peer_list)
			self.IBC_send_list # をibc proofへ
			self.ibc.path_list = self.peer_list
			# new_message = self.cm.get_message_text(MSG_IBC_SEND, msg) #7#
			print(" =========== confirm_ibc_address(Current_IBC_list) =========== ", peer)
			print(" =============================== ")
			print(" ==== OK ==== MSG_IBC_START ==== ", type(peer))
			print(" ==== OK ==== MSG_IBC_START ==== ", peer)
			print(" =============================== ")
			self.myibcblock_in_check()
			print("ここまできた？！＄！＄！＄！＄！＄")
			# self.start_ibc() 
			# result_list = msg_loads.split('), ')
			# listの受信
			# それに対して宛先をして送信

		elif msg[2] == MSG_IBC_FIN:
			print("PPPPPPPPPPPPPPP")
			print("PPPPPPPPPPPPPPP")
			print("PPPPPPPPPPPPPPP")
			IBC_time = self.ibc.time_stop_IBC()
			self.ibc.IBC_time_list.append(IBC_time)
			print("IBC time is :", IBC_time)
			print("MSG_IBC_FIN", len(self.ibc.IBC_time_list))
			print("PPPPPPPPPPPPPPP", len(self.ibc.IBC_time_list))
			logging.debug('MSG_IBC_FIN @' + str(peer)) 
			print("JJJJJJJJJJJJJJJJJJJJJJJJJ")
			print("JJJJJJJJJJJJJJJJJJJJJJJJJ")
			print("JJJJJJJJJJJJJJJJJJJJJJJJJ")
			print("JJJJJJJJJJJJJJJJJJJJJJJJJ")
			print("JJJJJJJJJJJJJJJJJJJJJJJJJ", len(self.ibc.IBC_time_list))
			print("JJJJJJJJJJJJJJJJJJJJJJJJJ", self.inter_list)
			print("JJJJJJJJJJJJJJJJJJJJJJJJJ", len(self.inter_list))
			if len(self.ibc.IBC_time_list) == 50:#8#
				print("aaaaaaaaaaaaaaaaa")
				filename01 = "IBC_time_50" + ".txt"
				for i in self.ibc.IBC_time_list:
					with open(filename01, mode='a') as f:
						f.write(str(i) + "\n")
				print("bbbbbbbbbbbbbbbbb")
				filename02 = "IBC_inter_50" + ".txt"
				for interR in self.inter_list:
					with open(filename02, mode='a') as f:
						f.write(str(interR) + "\n")
				print("aaaaaaaaaaaaaaaaa SAVED aaaaaaaaaaaaaaaaaaa")
			if len(self.ibc.IBC_time_list) == 100:#8#
				print("aaaaaaaaaaaaaaaaa")
				filename01 = "IBC_time_100" + ".txt"
				for i in self.ibc.IBC_time_list:
					with open(filename01, mode='a') as f:
						f.write(str(i) + "\n")
				print("bbbbbbbbbbbbbbbbb")
				filename02 = "IBC_inter_100" + ".txt"
				for interR in self.inter_list:
					with open(filename02, mode='a') as f:
						f.write(str(interR) + "\n")
				print("aaaaaaaaaaaaaaaaa SAVED aaaaaaaaaaaaaaaaaaa")
			if len(self.ibc.IBC_time_list) == 500:#8#
				print("aaaaaaaaaaaaaaaaa")
				filename01 = "IBC_time_500" + ".txt"
				for i in self.ibc.IBC_time_list:
					with open(filename01, mode='a') as f:
						f.write(str(i) + "\n")
				print("bbbbbbbbbbbbbbbbb")
				filename02 = "IBC_inter_500" + ".txt"
				for interR in self.inter_list:
					with open(filename02, mode='a') as f:
						f.write(str(interR) + "\n")
				print("aaaaaaaaaaaaaaaaa SAVED aaaaaaaaaaaaaaaaaaa")
			if len(self.ibc.IBC_time_list) == 1000:#8#
				print("aaaaaaaaaaaaaaaaa")
				filename03 = "IBC_time_1000" + ".txt"
				for i in self.ibc.IBC_time_list:
					with open(filename03, mode='a') as f:
						f.write(str(i) + "\n")
				print("bbbbbbbbbbbbbbbbb")
				filename04 = "IBC_inter_1000" + ".txt"
				for f in self.inter_list:
					with open(filename04, mode='a') as f:
						f.write(str(f) + "\n")
				print("aaaaaaaaaaaaaaaaa SAVED aaaaaaaaaaaaaaaaaaa")

		# elif msg[2] == MSG_IBC_SEND:# これに変更→MSG_IBC_SEND:
		# 	print("MSG_IBC_SEND")
		# 	logging.debug('MSG_START_IBC @' + str(peer))
		# 	block_l = json.dumps(self.ibc.block_ref())
		# 	block_msg = self._get_hash_sha256(block_l)
		# 	self.ibc.myblock_in = True
		# 	c = self.gs.compute_digital_signature(block_msg)
		# 	logging.debug('block_msg' + str(block_l))
		# 	msg_d = {
		# 		c + "__PORT(" + str(self.my_port) + ")":block_msg + "__(Block_Hash)"
		# 	}
		# 	logging.debug("block_hash" + str(msg_d))
		# 	new_message = self.cm.get_message_text(MSG_IBC_RECEIVE, json.dumps(msg_d, sort_keys = True ,ensure_ascii = False))
		# 	print("============= start_cross_reference__Leader_aggregation =============")
		# 	logging.info("============= start_cross_reference__Leader_aggregation =============")
		# 	self.cm.send_msg(peer ,new_message, delay = False)
		# 	logging.info("SEND_IBC")
		# 	self.Send_heartbeat

		# elif msg[2] == MSG_IBC_RECEIVE:
		# 	print("MSG_IBC_RECEIVE")
		# 	logging.debug('MSG_IBC_RECEIVE @' + str(peer))
		# 	print("received : =============== MSG_IBC_RECEIVE =============")
		# 	print("Phase1-1")
		# 	print("=============MSG===================", msg[4])
		# 	msg_loads = json.loads(msg[4])
		# 	print("HASH:" ,msg_loads)	
		# 	if self.Ccount == 0:
		# 		self.Ccount = 1
		# 		self.Send_list = copy.deepcopy(self.cm.owner_node_set.get_list())
		# 		logging.debug("sendlist is" + str(self.Send_list))
				
		# 		if peer in self.Send_list:
		# 			self.Send_list.remove(peer)
		# 			self.current_IBC(msg_loads)
		# 			logging.critical("A-1")
		# 		else:
		# 			logging.critical("A-2")
		# 			pass
 
		# 	elif self.Ccount >= 1:
		# 		if peer in self.Send_list:
		# 			self.Send_list.remove(peer)
		# 			self.current_IBC(msg_loads)
		# 			logging.critical("B-1")
		# 		else:
		# 			logging.critical("B-2")
		# 			pass
		# 	else:
		# 		logging.critical("C")
		# 		pass

		elif msg[2] == MSG_IBC_NEXT_CHAIN1:
			if self.IBC_multihop == 1:
				self.P_msg = MSG_IBC_FIN
				self.P_msg_to_peer = (self.owner_node_host, self.owner_node_port)
			else:
				self.P_msg = MSG_IBC_NEXT_CHAIN2
				self.P_msg_to_peer = self.get_nx_peer()

			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			print("MSG_IBC_NEXT_CHAIN1 @" + str(peer))
			logging.debug('MSG_IBC_NEXT_CHAIN1 @' + str(peer)) # @LEADER
			msg_loads = msg[4]
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			# block_info = msg_loads.keys()
			# print(block_info)
			# print(type(block_info))
			block_info = self.ibc_block_info()#ここは変える必要がある。
			self.peer_list = None
			# print(self.peer_list)
			# print(type(self.peer_list))
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			self.ibc_in_my_block(block_info ,self.peer_list)
			self.myibcblock_in_check()
			print("ここまできた？！＄！＄！＄！＄！＄")
			# 入力値から不要な文字を取り除く
			# cleaned_values = [value.replace("(", "").replace(")", "") for value in receive_list[0]]
			# # 整形されたリストを出力
			# C_list = [tuple(value.split(', ')) for value in cleaned_values]
			# CC_list = ",".join(",".join(map(str, tpl)) for tpl in C_list)
			# self.IBC_send_list = CC_list.split(",")
			# print(self.IBC_send_list)
			# print(" =============================== ")
			# print(" ==== OK ==== MSG_IBC_NEXT_CHAIN ==== ", type(self.IBC_send_list[0]), type(self.IBC_send_list[1]))
			# print(" ==== OK ==== MSG_IBC_NEXT_CHAIN ==== ", self.IBC_send_list[0], self.IBC_send_list[1])
			# print(" =============================== ") 

			# R = len(self.IBC_send_list)
			# self.peer_list = []
			# for x in range(R):  # 例として範囲を10としますが、実際の範囲は問題によります
			# 	if x % 2 == 1:  # xが奇数の場合
			# 		pass  # 何もしない
			# 	else: # xが偶数の場合の処理
			# 		# print(f"{x}は偶数です。")
			# 		self.peer_list.append(f"{self.IBC_send_list[x]}, {self.IBC_send_list[x+1]}")
			# print(" =============================== ")
			# print(" ==== OK ==== MSG_IBC_START ==== ", type(self.peer_list[0]), type(self.IBC_send_list[1]))
			# print(" ==== OK ==== MSG_IBC_START ==== ", self.peer_list[0], self.peer_list[1])
			# print(" ==== OK ==== MSG_IBC_START ==== ", type(self.peer_list), self.peer_list)
			# print(" =============================== ") 

			# for item in self.peer_list:
			# 	if str(self.my_port) in item:
			# 		self.peer_list.remove(item)
			# 		print(" ===============================remove!!!! ", item) 

			# peer = self.peer_list[0]
			# # if str(self.my_port) in peer:
			# # 	x = 1
			# # 	print(" =========== WARNING =========== " ,self.my_port)
			# # 	print(" =========== WARNING =========== " ,peer)
			# # 	peer = self.peer_list[x]		
			
			# if str(self.owner_node_port) in peer:
			# 	# if :
			# 	y = 1
			# 	print(" =========== WARNING =========== " ,self.my_port)
			# 	print(" =========== WARNING =========== " ,peer)
			# 	peer = self.peer_list[-y]
			# 	print(" =============================== ", y)
			
			# self.nx_peer = self.confirm_ibc_address(self.peer_list)
			# self.ibc.IBC_state = "WIP-IBC"
			# print("========= Tarn to WIP-IBC =========",self.ibc.IBC_state)
			# self.ibc_in_my_block(block_info ,self.peer_list)
			# self.IBC_send_list # をibc proofへ
			# self.ibc.path_list = self.peer_list
			# # new_message = self.cm.get_message_text(MSG_IBC_SEND, msg) #7#
			# print(" =========== confirm_ibc_address(Current_IBC_list) =========== ", peer)
			# print(" =============================== ")
			# print(" ==== OK ==== MSG_IBC_START ==== ", type(peer))
			# print(" ==== OK ==== MSG_IBC_START ==== ", peer)
			# print(" =============================== ")
			# self.myibcblock_in_check()
			# print("ここまできた？！＄！＄！＄！＄！＄")
		# elif msg[2] == IBC_

		elif msg[2] == MSG_IBC_NEXT_CHAIN2:
			if self.IBC_multihop == 2:
				self.P_msg = MSG_IBC_FIN
				self.P_msg_to_peer = (self.owner_node_host, self.owner_node_port)
				print("end to FIN HOP NUM === 2")
			else:
				self.P_msg = MSG_IBC_NEXT_CHAIN3
				self.P_msg_to_peer = self.get_nx_peer()
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			print("MSG_IBC_NEXT_CHAIN2 @" + str(peer))
			logging.debug('MSG_IBC_NEXT_CHAIN1 @' + str(peer)) # @LEADER
			msg_loads = msg[4]
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			block_info = self.ibc_block_info()#ここは変える必要がある。
			self.peer_list = None
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			self.ibc_in_my_block(block_info ,self.peer_list)
			self.myibcblock_in_check()
			print("ここまできた？！＄！＄！＄！＄！＄")

		elif msg[2] == MSG_IBC_NEXT_CHAIN3:
			if self.IBC_multihop == 3:
				self.P_msg = MSG_IBC_FIN
				self.P_msg_to_peer = self.owner_node_host, self.owner_node_port
				# print("end to FIN HOP NUM === 3", self.P_msg_to_peer)
				# print("end to FIN HOP NUM === 3", type(self.P_msg_to_peer))
				print("end to FIN HOP NUM === 3")
			else:
				self.P_msg = MSG_IBC_NEXT_CHAIN4
				self.P_msg_to_peer = self.get_nx_peer()
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			print("MSG_IBC_NEXT_CHAIN1 @" + str(peer))
			logging.debug('MSG_IBC_NEXT_CHAIN3 @' + str(peer)) # @LEADER
			msg_loads = msg[4]
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			block_info = self.ibc_block_info()#ここは変える必要がある。
			self.peer_list = None
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			self.ibc_in_my_block(block_info ,self.peer_list)
			self.myibcblock_in_check()
			print("ここまできた？！＄！＄！＄！＄！＄")

		elif msg[2] == MSG_IBC_NEXT_CHAIN4:
			if self.IBC_multihop == 4:
				self.P_msg = MSG_IBC_FIN
				self.P_msg_to_peer = (self.owner_node_host, self.owner_node_port)
				print("end to FIN HOP NUM === 4")
			else:
				self.P_msg = MSG_IBC_NEXT_CHAIN5
				self.P_msg_to_peer = self.get_nx_peer()
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			print("MSG_IBC_NEXT_CHAIN4 @" + str(peer))
			logging.debug('MSG_IBC_NEXT_CHAIN1 @' + str(peer)) # @LEADER
			msg_loads = msg[4]
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			block_info = self.ibc_block_info()#ここは変える必要がある。
			self.peer_list = None
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			self.ibc_in_my_block(block_info ,self.peer_list)
			self.myibcblock_in_check()
			print("ここまできた？！＄！＄！＄！＄！＄")

		elif msg[2] == MSG_IBC_NEXT_CHAIN5:
			if self.IBC_multihop == 5:
				self.P_msg = MSG_IBC_FIN
				self.P_msg_to_peer = (self.owner_node_host, self.owner_node_port)
				print("end to FIN HOP NUM === 5")
			else:
				self.P_msg = MSG_IBC_NEXT_CHAIN6
				self.P_msg_to_peer = self.get_nx_peer()
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			print("MSG_IBC_NEXT_CHAIN5 @" + str(peer))
			logging.debug('MSG_IBC_NEXT_CHAIN1 @' + str(peer)) # @LEADER
			msg_loads = msg[4]
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			block_info = self.ibc_block_info()#ここは変える必要がある。
			self.peer_list = None
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			self.ibc_in_my_block(block_info ,self.peer_list)
			self.myibcblock_in_check()
			print("ここまできた？！＄！＄！＄！＄！＄")

		elif msg[2] == MSG_IBC_NEXT_CHAIN6:
			if self.IBC_multihop == 6:
				self.P_msg = MSG_IBC_FIN
				self.P_msg_to_peer = (self.owner_node_host, self.owner_node_port)
				print("end to FIN HOP NUM === 6")
			else:
				self.P_msg = MSG_IBC_FIN
				self.P_msg_to_peer = (self.owner_node_host, self.owner_node_port)
				# ここは
				# self.P_msg = MSG_IBC_NEXT_CHAIN7
				# self.P_msg_to_peer = self.get_nx_peer()
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			print("MSG_IBC_NEXT_CHAIN5 @" + str(peer))
			logging.debug('MSG_IBC_NEXT_CHAIN1 @' + str(peer)) # @LEADER
			msg_loads = msg[4]
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			block_info = self.ibc_block_info()#ここは変える必要がある。
			self.peer_list = None
			print("[][][][][][][][][][][][][][][]")
			print("[][][][][][][][][][][][][][][]")
			self.ibc_in_my_block(block_info ,self.peer_list)
			self.myibcblock_in_check()
			print("ここまできた？！＄！＄！＄！＄！＄")

#------------------------------ Raft --------------------------------------------------
		elif msg[2] == RAFT_CANDIDATE_LEADER: 
			self.Last_Heartbeat_time() 
			print("msg[2] == Raft_My_Leader")
			logging.debug(str(peer) + "RAFT_CANDIDATE_LEAADER")

			if self.Raft_Voting == 0:
				self.Raft_Voting_state = True
				self.Raft_Voting = +1 
				new_message = self.cm.get_message_text(U_RAFT_FOLLOWER)
				self.cm.send_msg(peer,new_message, delay = False)
			
			else:
				print("Denial")
				logging.debug("")

		elif msg[2] == U_RAFT_FOLLOWER:
			self.Voting_Result.append(peer) 
			B = len(self.Voting_Result)
			A = copy.deepcopy(self.cm.owner_node_set.get_list())
			if len(A)/2 <= B:
				self.Raft_Leader_state = True
	
				new_message = self.cm.get_message_text(IM_RAFT_LEADER) 
				self.cm.send_msg_to_all_owner_peer(new_message) 

				self.Raft_reset_timer = threading.Timer(60, self.Raft_reset)
				self.Raft_reset_timer.start()
				self.Raft_Leader_loop()

			else:
				print(" ")
				logging.debug(" ")

		elif msg[2] == IM_RAFT_LEADER:
			self.Last_Heartbeat_time()
			self.Raft_Leader_state = False
			print("Re new leader is", peer)
			self.Raft_Leader = peer
			logging.debug("IM_RAFT_LEADE :Raft_Voting_state is)" + str(self.Raft_Voting_state))

			self.Raft_Leader_state = False
			self.Raft_reset()
			self.Raft_Follower_loop()
			
		elif msg[2] == RAFT_HEARTBEAT:
			self.Last_Heartbeat_time()

	def __get_myip(self):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(('8.8.8.8', 80))
		return s.getsockname()[0]

