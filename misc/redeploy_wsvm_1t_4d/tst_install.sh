#!/bin/bash

Help()
{
    echo "./tst_install.sh [-h|-l|-i]"
    echo ""
    echo "options:"
    echo "h print the help"
    echo "l list dependencies"
    echo "i install dependencies"
}

tstip="192.168.31.200"
DEB_DEPENDS="dhcpcd5"

List()
{
    echo "[Info][ListDependencies] $DEB_DEPENDS"
}

InstallDependencies()
{
    echo "[Info][InstallDependencies] --------------------------------------"
    echo "[Info][InstallDependencies] (begin) install the dependency to the target machine"

    ssh root@$tstip apt-get -y update
    ssh root@$tstip apt-get -y install $DEB_DEPENDS

    echo "[Info][InstallDependencies] (end) install the dependency to the target machine"
    echo "[Info][InstallDependencies] --------------------------------------"
}

while getopts "hli" option;
do
    case "$option" in
        h) # display help.
            Help
            exit;;
	l)
	    List
	    exit;;
        i)
            InstallDependencies
            exit;;
        \?) # Invalid option
            echo "Error: Invalid option"
            exit;;
    esac
done
