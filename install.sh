#!/bin/sh

mkdir -p /usr/local/etc
mkdir -p /var/lib/libvirt-evdev/capabilities

cp -a libvirt-evdev.py /usr/local/bin/
cp -a libvirt-evdev.service /etc/systemd/system/
cp -a libvirt-evdev.toml /usr/local/etc/

chmod +x /usr/local/bin/libvirt-evdev.py
systemctl daemon-reload
systemctl enable libvirt-evdev.service