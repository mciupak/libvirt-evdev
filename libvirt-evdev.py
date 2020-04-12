#!/usr/bin/env python3

import systemd.daemon as sd
import asyncio
import evdev
import evdev.ecodes as e
import os
import re
import sys
import subprocess
import pyudev
import toml
import pickle

def screen_input_switch(owner):
    for screen in config['screens']:
        for source in screen['sources']:
            if source['owner'] == owner:
                print("Screen input switch: {0} {1}".format(screen['name'], source['name']))
                subprocess.run(["/usr/bin/ddccontrol", "-r", screen['address'], "-w", source['id'], screen['dev']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def replicate(source_device):
    global current_mode

    try:
        async for event in input_devices[source_device].async_read_loop():
            if event.type == e.EV_SYN:
                continue

            if event.type == e.EV_KEY and event.code == e.KEY_SCROLLLOCK:
                if event.value == 0:
                    current_mode = {
                        "host": "guest",
                        "guest": "host",
                    }[mode]

                    screen_input_switch(current_mode)

                mode = "host"
            else:
                mode = current_mode

            target_device = {
                "host": host_devices[source_device],
                "guest": guest_devices[source_device],
            }[mode]

            target_device.write_event(event)
            target_device.syn()

    except:
        pass

def action_input(action, device):
    if action != 'add':
        return
    if not device.get('DEVLINKS'):
        return

    for link in device.get('DEVLINKS').split():
        for device in config['inputs']:
            if link == config['inputs'][device]:
                input_devices[device] = evdev.InputDevice(link)
                input_devices[device].grab()
                asyncio.run_coroutine_threadsafe(replicate(device), loop)

def action_usb(action, device):
    global current_mode

    if device.get(config['usb_switch']['property_name']) == config['usb_switch']['property_value']:
        if action == 'add':
            screen_input_switch(current_mode)
        elif action == 'remove':
            screen_input_switch("external")


if __name__ == '__main__':

    try:
        config = toml.load('/usr/local/etc/libvirt-evdev.toml')
    except:
        print("Reading config file failed.")
        exit(0)
    
    if not 'inputs' in config:
        print("No [inputs] section in config file.")
        exit(0)

    if not config['inputs']:
        print("No keyboard/mouse in config [inputs] section.")
        exit(0)

    current_mode = "host"

    # read capabilities and grab input devices
    input_devices = {}
    capabilities = {}
    for device in config['inputs']:
        p = '/var/lib/libvirt-evdev/' + device + '.p'
        # use capabilities from real device if connected
        if os.path.exists(config['inputs'][device]):
            input_devices[device] = evdev.InputDevice(config['inputs'][device])
            input_devices[device].grab()
            capabilities[device] = input_devices[device].capabilities()
            del capabilities[device][0]
            pickle.dump(capabilities[device], open(p,'wb'))
        # read stored capabilities otherwise
        elif os.path.exists(p):
            with open(p,'rb') as fp:
                capabilities[device] = pickle.load(open(p,'rb'))

    if not capabilities:
        exit(0)
    

    # create host devices
    host_devices = {
        key:evdev.UInput(cap)
        for (key,cap) in capabilities.items()
    }

    # create guest devices
    guest_devices = {
        key:evdev.UInput(cap)
        for (key,cap) in capabilities.items()
    }

    #prepare host device paths
    host_device_paths = [
        os.path.join("/dev/input/by-id", "host-%s" % device)
        for device in config['inputs']
    ]

    #prepare guest device paths
    guest_device_paths = [
        os.path.join("/dev/input/by-id", "guest-%s" % device)
        for device in config['inputs']
    ]

    virtual_devices = list(host_devices.values()) + list(guest_devices.values())
    virtual_device_paths = host_device_paths + guest_device_paths

    if not os.path.exists('/dev/input/by-id'):
        try:
            os.makedirs('/dev/input/by-id')
        except FileExistsError:
            pass

    # create symlinks
    for (device, path) in zip(virtual_devices, virtual_device_paths):
        if os.path.exists(path):
            subprocess.run(["unlink", "--", path])
        subprocess.run(["ln", "-s", device.device, path])

    # setup replicate input coroutine
    for device in input_devices:
        asyncio.ensure_future(replicate(device))

    #setup udev monitoring of inpt and usb susbsystems
    context = pyudev.Context()
    monitor_input = pyudev.Monitor.from_netlink(context)
    monitor_input.filter_by(subsystem='input')

    monitor_usb = pyudev.Monitor.from_netlink(context)
    monitor_usb.filter_by(subsystem='usb')

    observer_input = pyudev.MonitorObserver(monitor_input, action_input)
    observer_usb = pyudev.MonitorObserver(monitor_usb, action_usb)

    observer_input.start()
    observer_usb.start()

    # notify systemd that start is done
    sd.notify(sd.Notification.READY)

    loop = asyncio.get_event_loop()
    loop.run_forever()

    