
#!/bin/bash

gnome-terminal -- bash -c "python3 APP/owner_server0.py; bash"
sleep 8
gnome-terminal -- bash -c "python3 APP/owner_server1.py; bash"
sleep 5
gnome-terminal -- bash -c "python3 APP/owner_server2.py; bash"
sleep 5
gnome-terminal -- bash -c "python3 APP/owner_server3.py; bash"
# sleep 5
# gnome-terminal -- bash -c "python3 APP/owner_server4.py; bash"
# sleep 10
# gnome-terminal -- bash -c "python3 APP/owner_server5.py; bash"
