#!/bin/bash

#Check if required programs are installed
declare -a req_progs=(openvpn pgrep)
for i in "${req_progs[@]}"
do
   echo "Checking if $i is installed"
   command -v $i >/dev/null 2>&1 || \
   { echo >&2 "$i is required but it's not installed! Aborting!"; exit 1; }
   echo "OK"
done
echo "All required programs are installed. Running main program."

CONFIG_FILE="ibVPN_Sweden_Stockholm_1.ovpn"
SERVER_CHANGE_COMMAND="/tmp/openVPN_aliver_command.txt"
PASS_FILE="/home/highstaker/Documents/ibVPN_pass.txt"
CONFIG_FILES_FOLDER="/home/highstaker/Documents/ibvpn_openvpn"
VPN_ENABLED=true
COMMAND_VPN_STOP="stop"

cd $CONFIG_FILES_FOLDER

while true
do

	#a command to change server. Config filename is in the file
	if [ -f $SERVER_CHANGE_COMMAND ]
		then
		echo "A command to change server received!"

		COMM=$(cat $SERVER_CHANGE_COMMAND)
		echo "Command: $COMM"

		killall openvpn

		if [ $COMM == $COMMAND_VPN_STOP ]
			then
			CONFIG_FILE=""
			VPN_ENABLED=false
			else
			CONFIG_FILE=$COMM
			VPN_ENABLED=true
		fi

		rm $SERVER_CHANGE_COMMAND
	fi

	echo "[DEBUG] VPN_ENABLED: $VPN_ENABLED"

	if [ $VPN_ENABLED == true ]
		then
		if pgrep -x openvpn > /dev/null
			then 
			echo "openvpn Running"
		else 
			echo "openvpn NOT running"
			openvpn --config "$CONFIG_FILE" --auth-user-pass $PASS_FILE &
		fi
	else
		echo "VPN disabled"
	fi

	sleep 3
done
