import logging
import time
import threading, json
import hashlib

from signature.generate_sigunature import DigitalSignature
from signature.generate_sigunature import CheckDigitalSignature
from p2p.connection_manager_4owner import ConnectionManager4Owner
from p2p.my_protocol_message_handler import MyProtocolMessageHandler
from blockchain.blockchain_manager import BlockchainManager
# from p2p.owner_node_list import OwnerCoreNodeList

class IBCManager:

	def __init__(self):
		self.gs = DigitalSignature()
		self.occ = None
		self.cross_IBC = []
		# self.reference = []
		self.lock1 = threading.Lock()
		self.lock2 = threading.Lock()
		self.lock3 = threading.Lock()
		self.lock4 = threading.Lock()
		self.timer1 = 0
		self.flag1 = False
		self.timer2 = 0
		self.flag2 = False
		self.timer3 = 0
		self.flag3 = False
		self.cross_reference_flag = False
		self.inc = 0
		self.ref_block_num = 9999
		self.Block_confirmed = None
		self.myblock_in = False
		self.phase1_list = []
		self.IBC_state = "stand-by" # 待機中
		self.IBC_list = None
		self.ibc_maltihop_channels = []
		self.path_list = []
		self.IBC_time_list = []

	def set_new_ibc(self, ibc_block):
		logging.debug("rq == self.lock1-1")
		with self.lock1: 
			self.IBC_state = "WIP-IBC"
			logging.debug("self.lock1_ON-set_new_cross_reference ")
			self.cross_IBC.append(ibc_block)
			print("======= set_new_cross_IBC =======", self.cross_IBC)
		logging.debug("self.lock1_OFF-set_new_cross_reference ==")
		print("========= Tarn to WIP-IBC =========!!!!!!!!!!!", self.IBC_state)

	def in_block(self, ibc_block, peer_list):
		print("=========self.ibc===============", ibc_block, peer_list)
		print("=========self.ibc===============", ibc_block, peer_list)
		self.ibc_maltihop_channels = peer_list #7# listを引き継ぎ
		print("=========self.ibc===============", type(self.ibc_maltihop_channels))
		print("=========self.ibc===============", self.ibc_maltihop_channels)
		self.set_new_ibc(ibc_block)
		print("=========self.ibc===============type(self.reference)", type(self.cross_IBC))
		print("=========self.ibc===============self.reference", self.cross_IBC)		
		# return 0

	def clear_IBC(self):#7#ここで
		logging.debug("rq == self.lock1-4")
		with self.lock1:
			logging.debug("self.lock1_ON-clear_cross_reference ==")
			if self.IBC_state == "WIP-IBC":
				# self.occ.send_NEXT_IBC(self)
				self.IBC_state = "stand-by"
				print("======== reference part clear ======== Tarn to IBC_state → ", self.IBC_state)
			elif self.IBC_state == "stand-by":
				print("IBC_state → ", self.IBC_state)

			else:
				print("======== reference part clear なにか問題起きてるよmay be。 ======== Tarn to IBC_state → ", self.IBC_state)
		self.cross_IBC.clear()#list
		print("=")
		print("=")
		print("=")
		print("=")
		print("=")
		print(" ======== reference part clear ======== ", self.cross_IBC)
		logging.debug("self.lock1_ON-clear_cross_reference == ")
	
	def get_IBC_pool(self): #7#
		logging.debug("rq == self.lock3")
		with self.lock3:
			logging.debug("self.lock3_ON-get_reference_pool")
			if len(self.cross_IBC) == 1:
				logging.debug("len(self.reference) == 1")
				return self.cross_IBC[0]
				
			elif len(self.cross_IBC) > 1:
				logging.debug("len(self.reference) > 1")
				return self.cross_IBC[:]

			else:
				logging.debug("Currently, it seems cross pool is empty...")
				print("Currently, it seems cross pool is empty...")
				return []

	def _get_hash_sha256(self, message):
		return hashlib.sha256(message.encode()).hexdigest()

	def time_start_IBC(self):
		print("================= time_start_phase1 =================")
		self.flag1 = True
		self.timer1 =  time.perf_counter()
	
	def time_stop_IBC(self):
		if self.flag1:
			t = time.perf_counter()- self.timer1
			self.flag1 = False
			return t
		else:
			return None

	# def time_start_phase1(self):
	# 	print("================= time_start_phase1 =================")
	# 	self.flag1 = True
	# 	self.timer1 =  time.perf_counter()
	
	# def time_stop_phase1(self):
	# 	if self.flag1:
	# 		t = time.perf_counter()- self.timer1
	# 		self.flag1 = False
	# 		return t
	# 	else:
	# 		return None

	def time_start_phase2(self):
		self.flag2 = True
		self.timer2 =  time.perf_counter()
	
	def time_stop_phase2(self):
		if self.flag2:
			t = time.perf_counter()- self.timer2
			self.flag2 = False
			return t
		else:
			return None

			# if len(self.IBC_list) == 1:
			# 	print("自分が最後のCHAIN")
			# 	# リーダーに終了を送信

			# elif len(self.IBC_list) >= 1:
			# 	print("len(self.IBC_list) >= 1")
			# 	msg = MSG_IBC_NEXT_CHAIN
			# 	return msg

			# else:
			# 	print("!!!!!!!!!!!! -ここは通らないはず- !!!!!!!!!!!!")


	def get_IBC_prof(self): #IBC
		"!!!!!!!!!!!!!!!!!! get_IBC_prof !!!!!!!!!!!!!!!!!!"
		if self.IBC_state == "WIP-IBC":
			print("WIP-IBC")
			if self.ibc_maltihop_channels == None:
				return "WIP-IBC"
			else:
				return self.ibc_maltihop_channels[:]

		elif self.IBC_state == "stand-by":
			print("stand-by")
			return "stand-by"
  		
		else: #7#ここは通らない。
			print("!=!=!=!=!=! ここは通らない。!=!=!=!=!=!")
			return None

	def ref_block_number(self,num):
		self.ref_block_num = num + 2
		print("##########################",self.ref_block_num)

	def check_ref_block_num(self):
		return self.ref_block_num

	# def block_cheek(self):
	# 	self.cross_reference_flag = False

	# def block_ref(self): #
	# 	return self.Block_confirmed

	# def renew_block_ref(self,block):
	# 	self.Block_confirmed = block
