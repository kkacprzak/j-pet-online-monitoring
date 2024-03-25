#!/usr/bin/env bash

source /usr/local/bin/thisroot.sh

prev_filename="-"
inotifywait -rqm --format '%w%f' /data/DAQ/ | while read -r f event; 
do
	if [[ "$f" =~ .*hld$ ]]; then
		filename=$(find /data/DAQ -name "*hld" -print0 | sort -z | tail -zn 2 | head -zn 1 | tr -d "\0")
		
		if [[ "$filename" != "$prev_filename" ]]; then
	    	temp=$(cat /home/jpet/monitoring/j-pet-online-monitoring/data_monitoring/temp)
	    	count=$((temp + 1))
			frequency=$(cat /home/jpet/monitoring/j-pet-online-monitoring/data_monitoring/frequency.txt)
			prev_filename=$filename
	    	echo "$count" > /home/jpet/monitoring/j-pet-online-monitoring/data_monitoring/temp

	    	if [ `echo ""$count" % $frequency" | bc` -eq 0 ]  
	    	then
		    	python3 /home/jpet/monitoring/j-pet-online-monitoring/data_monitoring/monitoring.py "$filename"
		    	sleep 10
  	  		fi
		fi
	fi
done
