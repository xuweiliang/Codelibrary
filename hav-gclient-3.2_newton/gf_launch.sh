#!/bin/bash
#
# gf Cloud Desktop Entry Point
#
#

# Backup log files
LOG_DIR=~/logbackup
EXT=`date +%Y%m%d`
FILENAME=zvmclient.log
LOGFILENAME=~/$FILENAME
BACKUP_FILENAME=$LOG_DIR/$FILENAME.$EXT

mkdir -vp $LOG_DIR

if [ ! -f $BACKUP_FILENAME.gz ]; then
	mv $LOGFILENAME $BACKUP_FILENAME
	gzip $BACKUP_FILENAME
fi

# Disable Power Saving
pm-powersave false

# Update Client
# Disable auto update for security reason
#python /usr/share/gclient/Update.pyc >> $FILENAME
service firewalld stop
#insmod /usr/share/hav-gclient/tusbd.ko
#/usr/share/hav-gclient/usbsrvd &
sed -i '/rm -rf .pulse/d' ~/.bash_profile
sed -i '/cd ~/d' ~/.bash_profile
sed -i '$a\cd ~' ~/.bash_profile
sed -i '$a\rm -rf .pulse' ~/.bash_profile
cp -f  /usr/share/hav-gclient/pcmanfm.conf ~/.config/pcmanfm/LXDE/
cp -f  /usr/share/hav-gclient/lxde-rc.xml ~/.config/openbox/
rm -rf /etc/X11/xorg.conf
cd /usr/share/hav-gclient
sercd -p 7004 7 -l 0.0.0.0 -b 115200 /dev/ttyUSB0 /var/lock/lock..ttyUSB0 &
sercd -p 7000 7 -l 0.0.0.0 -b 115200 /dev/ttyS0 /var/lock/lock..ttyS0 &
sercd -p 7001 7 -l 0.0.0.0 -b 115200 /dev/ttyS1 /var/lock/lock..ttyS1 &
sercd -p 7002 7 -l 0.0.0.0 -b 115200 /dev/ttyS2 /var/lock/lock..ttyS2 &
sercd -p 7003 7 -l 0.0.0.0 -b 115200 /dev/ttyS3 /var/lock/lock..ttyS3 &
sh /usr/bin/broadcast/broadcast.sh &
python start.pyc
python Main.pyc
