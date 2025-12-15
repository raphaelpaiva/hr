#!/bin/bash

USERNAME=$(whoami)

sudo sed "s/username/${USERNAME}/g" linux/sudoers.d/shutdown > /etc/sudoers.d/shutdown
sudo chmod 440 /etc/sudoers.d/shutdown
echo "Shutdown permissions installed."

sudo sed "s/username/${USERNAME}/g" systemd/hr.service > /etc/systemd/system/hr.service
sudo systemctl daemon-reload
sudo systemctl enable hr.service
sudo systemctl start hr.service
echo "HR service installed and started."
