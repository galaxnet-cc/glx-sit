#!/bin/bash

Help()
{
    echo "./redeploy.sh [-h|-f|-r]"
    echo ""
    echo "options:"
    echo "h print the help"
    echo "f reinstall the deb package, and do fac init"
    echo "r reset and refactory init (without package reinstalled)"
}

facinit="n"

RED='\e[31m'
NC='\e[0m' # No Color

dut1ip="192.168.31.201"
dut2ip="192.168.31.202"
dut3ip="192.168.31.203"
dut4ip="192.168.31.204"
dutip_list="192.168.31.201 192.168.31.202 192.168.31.203 192.168.31.204"

Reset()
{
    # copy per device fwdmd config
    echo -e "$RED[copy per device fwdmd configs when do reset]$NC"
    scp testDevice_dut1.json root@$dut1ip:/var/lib/fwdmd/params/devices/testDevice.json
    scp testDevice_dut2.json root@$dut2ip:/var/lib/fwdmd/params/devices/testDevice.json
    scp testDevice_dut3.json root@$dut3ip:/var/lib/fwdmd/params/devices/testDevice.json
    scp testDevice_dut4.json root@$dut4ip:/var/lib/fwdmd/params/devices/testDevice.json

    for dip in $dutip_list
    do
        # prepare directory
        echo -e "$RED[ resetting $dip]$NC"

        # enable fwdmd is running.
        ssh root@$dip systemctl restart fwdmd
        # wait for fwdmd started.
        sleep 5

        # copy vpp config
        echo -e "$RED[copy vpp config for ip $dip]$NC"
        scp ./vpp.conf root@$dip:/var/lib/fwdmd/params/devices/testDeviceVppStartup.conf

        ssh root@$dip redis-cli flushall
        scp ./facinit.sh root@$dip:/tmp/
        ssh root@$dip nohup sh /tmp/facinit.sh

        echo -e "$RED[ reset $dip done]$NC"
    done
}

while getopts "fhr" option;
do
    case "$option" in
        h) # display help.
            Help
            exit;;
        f)
            facinit="y";;
        r)
            Reset
            exit;;
        \?) # Invalid option
            echo "Error: Invalid option"
            exit;;
    esac
done

if [[ "$facinit" == "y" ]]; then
    echo -e "$RED[redeploy with facinit enabled ]$NC"
else
    echo -e "$RED[redeploy with facinit disabled ]$NC"
fi

# redeploy debs
for dip in $dutip_list
do
    # prepare directory
    echo -e "$RED[prepare directories for ip $dip]$NC"
    ssh root@$dip mkdir -p /tmp/sdwandebs
    ssh root@$dip rm /tmp/sdwandebs/*
    scp debs/*.deb root@$dip:/tmp/sdwandebs/

    # install prerequisite pkgs.
    ssh root@$dip apt-get -y install redis-server bridge-utils dnsmasq
    # install frr
    ssh root@$dip 'curl -s https://deb.frrouting.org/frr/keys.asc | apt-key add -'
    ssh root@$dip 'echo "deb https://deb.frrouting.org/frr $(lsb_release -s -c) frr-stable" | tee -a /etc/apt/sources.list.d/frr.list'
    ssh root@$dip 'apt update && apt install -y frr frr-pythontools'

    # reinstall vpp
    echo -e "$RED[reinstall vpp for ip $dip]$NC"
    ssh root@$dip dpkg -r libvppinfra vpp vpp-plugin-core vpp-plugin-dpdk
    ssh root@$dip dpkg -i /tmp/sdwandebs/libvppinfra*.deb /tmp/sdwandebs/vpp*.deb /tmp/sdwandebs/vpp-plugin-core*.deb /tmp/sdwandebs/vpp-plugin-dpdk*.deb

    # copy vpp config
    echo -e "$RED[copy vpp config for ip $dip]$NC"
    scp ./vpp.conf root@$dip:/etc/vpp/startup.conf


    # reinstall fwdmd
    echo -e "$RED[reinstall fwdmd for ip $dip]$NC"
    ssh root@$dip dpkg -r fwdmd
    ssh root@$dip dpkg -i /tmp/sdwandebs/fwdmd*.deb

    # fix possible dependencies.
    echo -e "$RED[fix dependencies ip $dip]$NC"
    ssh root@$dip apt -f -y install

    # enable coredumps
    ssh root@$dip mkdir -p /tmp/dumps
    ssh root@$dip sysctl -w debug.exception-trace=1 
    ssh root@$dip sysctl -w kernel.core_pattern="/tmp/dumps/%e-%t"
    ssh root@$dip ulimit -c unlimited
    ssh root@$dip echo 2 > /proc/sys/fs/suid_dumpable
done

# copy per device fwdmd config
echo -e "$RED[copy per device fwdmd configs]$NC"
scp testDevice_dut1.json root@$dut1ip:/var/lib/fwdmd/params/devices/testDevice.json
scp testDevice_dut2.json root@$dut2ip:/var/lib/fwdmd/params/devices/testDevice.json
scp testDevice_dut3.json root@$dut3ip:/var/lib/fwdmd/params/devices/testDevice.json
scp testDevice_dut4.json root@$dut4ip:/var/lib/fwdmd/params/devices/testDevice.json

# prepare all device to be running in dpdk mode.
for dip in $dutip_list
do
    echo -e "$RED[prepare device for dpdk mode for ip $dip]$NC"
    ssh root@$dip systemctl stop vpp
    ssh root@$dip systemctl stop fwdmd
    # 非d102机型，所以不做处理，虚拟机采用isolated网络，网卡默认为
    # down，可被dpdk加载，不需要特殊处理。
    # # move wan2/lan1/lan2 from the linux bridge.
    # # they will be used for sit testing.
    # ssh root@$dip brctl delif wan1 eth1
    # ssh root@$dip brctl delif lan eth2
    # ssh root@$dip brctl delif lan eth3
    # # down all ther interface
    # ssh root@$dip  ip link set eth1 down
    # ssh root@$dip  ip link set eth2 down
    # ssh root@$dip  ip link set eth3 down

    # bring up the vpp and do fac ini
    ssh root@$dip systemctl daemon-reload
    ssh root@$dip systemctl start vpp
    ssh root@$dip systemctl start fwdmd

    # sleep a while to wait fwdmd.
    sleep 5

    if [[ "$facinit" = "y" ]]; then
        ssh root@$dip redis-cli flushall
        scp ./facinit.sh root@$dip:/tmp/
        ssh root@$dip nohup sh /tmp/facinit.sh
    fi
done
