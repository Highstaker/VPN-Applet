#!/usr/bin/python3
#! -*- coding: utf-8 -*-

import subprocess, os, glob
from gi.repository import Gtk, GLib
from gi.repository import AppIndicator3 as appindicator
from country_codes import COUNTRIES

CONFIG_FILES_PATH="/home/highstaker/Документы/ibvpn_openvpn/"
SIGNAL_FILE_PATH="/tmp/"
SIGNAL_FILENAME="openVPN_aliver_command.txt"

class menuRefresher:

    #an IP is saved to this variable when it is changed. If the IP is the same, there is no point of doing other tasks like getting country etc
    IP_buf = ""

    def change_server(self,widget,config_filename):
        pass
        print("[DEBUG]Change server to " + config_filename)
        print("[DEBUG]Signal file: " + SIGNAL_FILE_PATH + SIGNAL_FILENAME)

        f = open(SIGNAL_FILE_PATH + SIGNAL_FILENAME,"w")
        f.write(config_filename)
        f.close()

        return True


    def set_indicating_menus(self,ind):
        """Sets the values in menus on each refresh"""
        myip = get_myip()

        if myip == self.IP_buf:
            print("[DEBUG]IP is the same")
            return True
        else:
            self.IP_buf = myip

        print("[DEBUG]Getting country")
        myCountry = get_country(myip) #country CODE
        myCountryName = [i for i in COUNTRIES if myCountry in i] #name of a country
        if myCountryName:
        	myCountryName = myCountryName[0][0]
        	flagIconFilename = "Flag_of_" + myCountryName.replace(" ","_")
        else:
        	print("[DEBUG]Could not get country name")
        	flagIconFilename = ""
        	myCountryName = ""


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

        ind.set_label(myip,"")
        ind.set_icon_full(flagIconFilename,myCountry)

        subprocess.Popen(['notify-send', "You external IP has been changed", \
            "New IP: " + myip + "\nCountry: " + myCountryName])

        return True
     
    def __init__(self,ind):
        GLib.timeout_add_seconds(5,self.set_indicating_menus,ind)

#returns current IP
def get_myip():

	getter_process = subprocess.Popen( \
		["dig", "+short", "myip.opendns.com", "@resolver1.opendns.com"] \
		,stdout=subprocess.PIPE)

	myip = getter_process.communicate()[0].decode(encoding="ascii", errors="ignore").replace("\n","")
	return myip

def get_country(ip):

	getter_process = subprocess.Popen( \
		["whois", ip] \
		,stdout=subprocess.PIPE)

	ipCountry = getter_process.communicate()[0].decode(encoding="ascii", errors="ignore")
	ipCountry = [line for line in ipCountry.split("\n") if (("country" in line) or ("Country" in line))]    

	if not ipCountry:
		return ""

	ipCountry = ipCountry[0]
	ipCountry = ipCountry.replace(" ","").replace("\t","").replace("country:","").replace("Country:","")

	return ipCountry

def main():

	#Debug
	myip = get_myip()#debug
	print(myip)#debug
	print(get_country(myip))#debug
	# quit()#debug

	ind = appindicator.Indicator.new (
                        "External_IP_applet",
                        "",
                        appindicator.IndicatorCategory.SYSTEM_SERVICES)
	ind.set_status(appindicator.IndicatorStatus.ACTIVE)


	ind.set_icon_theme_path(os.path.join(os.environ['HOME'], 'FlagsOfCountries'))
	# ind.set_icon_full("RO","")
	#ind.set_attention_icon("")
	# ind.set_label("test","")

	menuRefresher(ind)

	Gtk.main()

if __name__ == '__main__':
	main()
