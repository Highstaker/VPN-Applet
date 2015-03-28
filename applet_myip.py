#!/usr/bin/python3
#! -*- coding: utf-8 -*-

####other means of getting IP
##curl -s http://whatismijnip.nl |cut -d " " -f 5

import subprocess, os, glob
from gi.repository import Gtk, GLib
from gi.repository import AppIndicator3 as appindicator
from country_codes import COUNTRIES
from threading import Thread, Timer, Lock
import socket

CONFIG_FILES_PATH="/home/highstaker/Документы/ibvpn_openvpn/"
SIGNAL_FILE_PATH="/tmp/"
SIGNAL_FILENAME="openVPN_aliver_command.txt"

class menuRefresher:

	lock1 = Lock()

	#a flag showing that an IP has already been set. Prevents threads that got it later from assgning it to cur_IP for the second time
	flag_IP_already_set = False

	#a list of IP-asking threads
	#threads = []

	#how often, in seconds, we need to refresh the IP and indicator menus
	REFRESH_TIMEOUT = 5

	#handle to the indicator
	hIndicator = None

	#the current IP. Used by threads
	#cur_IP = ""

	#an IP is saved to this variable when it is changed. If the IP is the same, there is no point of doing other tasks like getting country etc
	IP_buf = ""

	#a flag, whether to show label with IP in tray or not
	show_label=False

	def change_server(self,widget,config_filename):
		pass
		print("[DEBUG]Change server to " + config_filename)
		print("[DEBUG]Signal file: " + SIGNAL_FILE_PATH + SIGNAL_FILENAME)

		f = open(SIGNAL_FILE_PATH + SIGNAL_FILENAME,"w")
		f.write(config_filename)
		f.close()

		return True

	def refresh_label(self,ind,myip):
		if self.show_label:
			ind.set_label(myip,"")
		else:
			print("[DEBUG]Set empty label")
			ind.set_label("","")

		return True

	def toggle_label(self,widget,ind,myip):
		self.show_label= not self.show_label
		self.refresh_label(ind,myip)

		return True

	def setIndicatingMenus(self,myip,ind):
		"""Sets the values in menus"""
		print("setIndicatingMenus with IP ", myip)

		if myip == self.IP_buf:
			print("[DEBUG]IP is the same")
			self.startRefreshSequence(ind)
			return True
		else:
			self.IP_buf = myip

		print("[DEBUG]Getting country")
		# myCountry = get_country(myip) #country CODE
		myCountry = "BD" #debug
		myCountryName = [i for i in COUNTRIES if myCountry in i] #name of a country
		if myCountryName:
			myCountryName = myCountryName[0][0]
			flagIconFilename = "Flag_of_" + myCountryName.replace(" ","_")
		else:
			print("[DEBUG]Could not get country name")
			flagIconFilename = ""
			myCountryName = ""


		print("[DEBUG]Creating menu")
		# create a menu
		menu = Gtk.Menu()

		menu_items = Gtk.MenuItem("External IP: \n" + myip) 
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem("Country code: \n" + myCountry) 
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem("Country: \n" + myCountryName)
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem("-"*20)
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem( "Disable VPN" )
		menu_items.connect("activate",self.change_server,"stop")
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem( "Toggle Label" )
		menu_items.connect("activate",self.toggle_label,ind,myip)
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem("Exit") 
		menu_items.connect("activate",Gtk.main_quit)
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem("-"*20)
		menu.append(menu_items)        
		menu_items.show()

		# global CONFIG_FILES
		CONFIG_FILES = glob.glob(CONFIG_FILES_PATH + "*.ovpn")
		CONFIG_FILES.sort()

		for i in CONFIG_FILES:
			menu_items = Gtk.MenuItem( os.path.basename(i) )
			menu_items.connect("activate",self.change_server,i)
			menu.append(menu_items)        
			menu_items.show()

		ind.set_menu(menu)

		self.refresh_label(ind,myip)

		ind.set_icon_full(flagIconFilename,myCountry)

		subprocess.Popen(['notify-send', "Your external IP has changed", \
			"New IP: " + myip + "\nCountry: " + myCountryName])

		self.startRefreshSequence(ind)

		print("Menus set!")
		return True

	def getIP(self,commandline):
		"""
		A thread that sets an IP using the method specified in commandline
		"""

		print("getIP with ", commandline, " started")

		getter_process = subprocess.Popen(commandline,stdout=subprocess.PIPE)
		myip = getter_process.communicate()[0].decode(encoding="ascii", errors="ignore").replace("\n","")

		if isIP(myip):
			self.lock1.acquire()
			try:
				if not self.flag_IP_already_set:
					# self.cur_IP = myip
					self.flag_IP_already_set = True
			finally:
				self.lock1.release()
				#self.threads = []
				print("debug2")
				self.setIndicatingMenus(myip,self.hIndicator)

		print("getIP end")

		return True


	def askIP(self,ind):
		"""
		Start subprocesses asking for external IP in separate threads
		"""

		#list of commandlines that are supposed to return IP as a result
		IPgettingMethods = [
		["dig", "+short", "myip.opendns.com", "@resolver1.opendns.com"]
		]

		for i in IPgettingMethods:
			th = Thread(target=self.getIP, args=(i,))
			th.start()


		return False


	def startRefreshSequence(self,ind):
		"""
		Ask for IP after certain amount of seconds
		"""
		print("[DEBUG]startRefreshSequence")
		self.cur_IP = ""
		flag_IP_already_set = False
		GLib.timeout_add_seconds(self.REFRESH_TIMEOUT,self.askIP,ind,)
		# refresh_timer = Timer(self.REFRESH_TIMEOUT,self.askIP,(ind,))
		# refresh_timer.start()

		print("[DEBUG]End of startRefreshSequence")
		return True

	 
	def __init__(self,ind):
		self.hIndicator = ind
		self.askIP(ind)


def isIP(check):
	"""
	returns True if the specified string is an IPv4 IP address, False otherwise
	"""
	if not isinstance(check,str):
		return False

	try:
		socket.inet_aton(check)
	except socket.error:
		return False

	return True

def get_country(ip):

	getter_process = subprocess.Popen(["whois", ip],stdout=subprocess.PIPE)

	ipCountry = getter_process.communicate()[0].decode(encoding="ascii", errors="ignore")
	ipCountry = [line for line in ipCountry.split("\n") if (("country" in line) or ("Country" in line))]    

	if not ipCountry:
		return ""

	ipCountry = ipCountry[0]
	ipCountry = ipCountry.replace(" ","").replace("\t","").replace("country:","").replace("Country:","")

	return ipCountry

def main():

	ind = appindicator.Indicator.new (
						"External_IP_applet",
						"",
						appindicator.IndicatorCategory.SYSTEM_SERVICES)
	ind.set_status(appindicator.IndicatorStatus.ACTIVE)


	ind.set_icon_theme_path(os.path.join(os.environ['HOME'], 'FlagsOfCountries'))

	menu_refresher1 = menuRefresher(ind)

	print("starting Gtk.Main")
	Gtk.main()

if __name__ == '__main__':
	main()
