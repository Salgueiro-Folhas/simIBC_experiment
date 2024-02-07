import signal
from settings import *

from core.owner_core import OwnerCore
from core.server_core import ServerCore
from cross_reference.cross_reference_manager import CrossReferenceManager
from cross_reference.ibc_manager import IBCManager

my_p2p_server_outer = None
my_p2p_server_inner = None

def signal_handler(signal, frame):
	shutdown_server()

def shutdown_server():
	global my_p2p_server_inner
	global my_p2p_server_outer
	my_p2p_server_inner.shutdown()
	my_p2p_server_outer.shutdown()

def main():
	crossref = CrossReferenceManager()
	ibc = IBCManager()
	signal.signal(signal.SIGINT, signal_handler)
	global my_p2p_server_inner
	global my_p2p_server_outer
	my_p2p_server_inner = ServerCore(HOST_PORT_LAYER_1_origin)
	my_p2p_server_inner.start(crm = crossref, ibc = ibc)
	my_p2p_server_outer = OwnerCore(HOST_PORT_LAYER_0_origin)
	my_p2p_server_outer.start(crm = crossref, ibc = ibc)

def window():
	print("window")
	my_p2p_server_outer.window()

if __name__ == '__main__':
	main()
	window()
	
