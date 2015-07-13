#!/usr/bin/python3
#! -*- coding: utf-8 -*-

####other means of getting IP
##curl -s http://whatismijnip.nl |cut -d " " -f 5

import subprocess, os, glob
from gi.repository import Gtk, GLib, GObject
from gi.repository import AppIndicator3 as appindicator
from country_codes import COUNTRIES
from threading import Thread, Timer, Lock
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal

CONFIG_FILES_PATH="/home/highstaker/Документы/ibvpn_openvpn/"
SIGNAL_FILE_PATH="/tmp/"
SIGNAL_FILENAME="openVPN_aliver_command.txt"

def exMsg(message):
	'''
	Shows a message tagged as [EXCEPTION]
	'''
	print("[EXCEPTION]" + message)


class menuRefresher:

	lock1 = Lock()

	#how often, in seconds, we need to refresh the IP and indicator menus
	REFRESH_TIMEOUT = 10

	#A timeout for IP-getting process. If it doesn't get IP within that time - it returns none and the subprocess is destroyed.
	GETTER_TIMEOUT = 5

	#handle to the indicator
	hIndicator = None

	#an IP is saved to this variable when it is changed. If the IP is the same, there is no point of doing other tasks like getting country etc
	IP_buf = ""

	cur_country = ""

	#a flag, whether to show label with IP in tray or not
	show_label = True

	#a flag, whether to show notifications or not
	show_notifications = True

	def change_server(self,widget,config_filename):
		'''
		Invoked when the menu entry for server change or VPN stop is pressed
		Creates a signal file for the daemon
		'''
		print("[DEBUG]Change server to " + config_filename)
		print("[DEBUG]Signal file: " + SIGNAL_FILE_PATH + SIGNAL_FILENAME)

		f = open(SIGNAL_FILE_PATH + SIGNAL_FILENAME,"w")
		f.write(config_filename)
		f.close()

		return True

	def get_country(self,ip):
		'''
		Returns the country code of the country the IP is based in
		'''

		try:
			getter_process = subprocess.Popen(["whois", ip],stdout=subprocess.PIPE)
		except:
			exMsg("Could not get country. Is 'whois' installed?")
			return ""

		ipCountry = getter_process.communicate()[0].decode(encoding="ascii", errors="ignore")
		ipCountry = [line for line in ipCountry.split("\n") if (("country" in line) or ("Country" in line))]    

		if not ipCountry:
			return ""

		ipCountry = ipCountry[0]
		ipCountry = ipCountry.replace(" ","").replace("\t","").replace("country:","").replace("Country:","")
		ipCountry = ipCountry.upper()

		return ipCountry

	def refresh_label(self,ind,myip):
		'''
		Shows the label near the applet icon in the top bar, but only if show_label flag is True.
		'''
		if self.show_label:
			ind.set_label(myip,"")
		else:
			print("[DEBUG]Set empty label")
			ind.set_label("","")

		return True

	def toggle_label(self,widget,ind,myip):
		'''
		Toggles the label in top bar by changing the show_label flag.
		'''
		self.show_label= not self.show_label
		self.refresh_label(ind,myip)
		self.setIndicatingMenus(myip=myip,ind=ind,onlySetMenus=True)

		return True

	def toggle_notifications(self,widget,ind,myip):
		'''
		Toggles the notifications by changing the show_notifications flag.
		'''
		self.show_notifications= not self.show_notifications
		self.setIndicatingMenus(myip=myip,ind=ind,onlySetMenus=True)

		return True

	def refresh_data(self,widget):
		'''
		Re-ask the IP data manually.
		Need to clear buffer to force applet to update.
		NOTE: Basically, that's all we need to do, the data will be refreshed on next refresh cycle, calling self.askIP directly causes strange behaviour - lots of repetitive copies of same askers.
		'''
		self.IP_buf = None
		# self.askIP(self.hIndicator)
		
		return True

	def setIndicatingMenus(self,myip,ind,onlySetMenus=False):
		"""Sets the values in menus"""
		print("setIndicatingMenus with IP ", myip)

		if not onlySetMenus:
			if myip == self.IP_buf:
				print("[DEBUG]IP is the same")
				GLib.idle_add(self.startRefreshSequence,ind)
				return False
			else:
				self.IP_buf = myip

		if not myip:
			myip = ""


		if not onlySetMenus:
			print("[DEBUG]Getting country")
			myCountry = ""
			if myip:
				self.cur_country = myCountry = self.get_country(myip) #country CODE
		else:
			myCountry = self.cur_country

		if myCountry:
			myCountryName = [i for i in COUNTRIES if myCountry in i] #name of a country
		else:
			myCountryName = [["Unknown"]]
		if myCountryName:
			myCountryName = myCountryName[0][0]
			flagIconFilename = "Flag_of_" + myCountryName.replace(" ","_")
		else:
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

		# menu.append(Gtk.SeparatorMenuItem())

		menu_items = Gtk.MenuItem("-"*20)
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem( "Disable VPN" )
		menu_items.connect("activate",self.change_server,"stop")
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem( "Toggle Label (" + ("ON" if self.show_label else "OFF") + ")")
		menu_items.connect("activate",self.toggle_label,ind,myip)
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem( "Toggle Notifications(" + ("ON" if self.show_notifications else "OFF") + ")" )
		menu_items.connect("activate",self.toggle_notifications,ind,myip)
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem( "Refresh Data" )
		menu_items.connect("activate",self.refresh_data)
		menu.append(menu_items)        
		menu_items.show()

		menu_items = Gtk.MenuItem("Exit") 
		menu_items.connect("activate",Gtk.main_quit)
		menu.append(menu_items)        
		menu_items.show()

		# menu.append(Gtk.SeparatorMenuItem())

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

		if not onlySetMenus:
			if not myip:
				notification_message = "Could not get IP. Connection lost."
			else:
				notification_message = "Your external IP has changed"

			if self.show_notifications:
				try:
					subprocess.Popen(['notify-send', notification_message, \
					"New IP: " + myip + "\nCountry: " + myCountryName])
				except:
					exMsg("Could not send notification. Is notify-send available in this system?")

			GLib.idle_add(self.startRefreshSequence,ind)

		print("Menus set!")
		return False

	def getIP(self,commandline):
		"""
		A thread that sets an IP using the method specified in commandline
		"""
		try:
			getter_process = subprocess.Popen(commandline,stdout=subprocess.PIPE)
		except:
			print("Could not get IP with this method. Is ", commandline[0], " installed?")
			return None
		try:
			myip = getter_process.communicate(timeout=self.GETTER_TIMEOUT)[0].decode(encoding="ascii", errors="ignore").replace("\n","")
		except subprocess.TimeoutExpired:
			getter_process.kill()
			print("IP getter with command line ", commandline, "timed out")
			return None
		else:
			print("getIP with ", commandline, " result:" , myip)
			return myip if isIP(myip) else None


	def askIP(self,ind):
		"""
		Start subprocesses asking for external IP in separate threads
		"""
		print("askIP start")
		#list of commandlines that are supposed to return IP as a result
		IPgettingMethods = [
		["dig", "+short", "myip.opendns.com", "@resolver1.opendns.com"]
		,["curl", "-s", "curlmyip.com"]
		,["curl", "-s" ,"icanhazip.com"]
		,["curl", "-s" ,"ifconfig.me"]
		]

		def controller_getIP():
			with ThreadPoolExecutor(len(IPgettingMethods)) as executor:
				futures = [executor.submit(self.getIP, i) for i in IPgettingMethods]
				for future in as_completed(futures):					
					ip = future.result()
					if ip:
						GLib.idle_add(self.setIndicatingMenus, ip, self.hIndicator)
						break
				else:
					#could not get IP by any means. No connection?
					GLib.idle_add(self.setIndicatingMenus, None, self.hIndicator)



		th = Thread(target=controller_getIP)
		th.start()

		return False


	def startRefreshSequence(self,ind):
		"""
		Ask for IP after certain amount of seconds
		"""
		print("[DEBUG]startRefreshSequence")
		self.cur_IP = ""
		GLib.timeout_add_seconds(self.REFRESH_TIMEOUT,self.askIP,ind,)

		print("[DEBUG]End of startRefreshSequence")
		return False

	 
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

def main():

	# Catch CTRL-C
	signal.signal(signal.SIGINT, lambda signal, frame: Gtk.main_quit())

	GObject.threads_init()

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
