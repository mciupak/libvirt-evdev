# libvirt-evdev
The purpose of libvirt-evdev service is to provide means to use libvirt evdev passthrough for hotpluggable input devices.
## Example configuration
This service is intended to be used in configuraton like in the following diagram:
```
                           +---------------------+
                           |        Screen       |
                           +---------------------+
                           | HDMI1  HDMI2  HDMI3 |
                           +---^------^------^---+
                               |      |      |
            +--------------+   |      |      |   +--------------+
            |   Main PC    |   |      |      |   |   Other PC   |
    evdev   +--------------+   |      |      |   +--------------+
+----------->   Guest      +---+      |      +---+              |
|passthrough|--------------+          |          |              |
+-----------+   Host       +----------+          |              |
            +-------^------+                     +-------^------+
                    |                                    |
                    |              +------+              |
                    |              | USB  |              |
                    +--------------+SWITCH+--------------+
                                   +-^--^-+
                                     |  |
                            +--------+  +--------+
                            |                    |
                      +-----+------+       +-----+-----+
                      |  Keyboard  |       |   Mouse   |
                      +------------+       +-----------+

```
In such configuration there are two PCs - main and other. Both PCs uses one set of keyboard and mouse which coukd be unplugged/hotplugged using USB switch. There two OSes running on main PC - Host and Guest. Guest uses evdev passthrough input from host.

## Primary problem
Due to fact the keyboard and mouse is shared by two PCs, evdev passthrough stops working after keyboard/mouse is unplugged and replugged using USB switch.

## Priamary solution
- ussing uinput module (CONFIG_INPUT_UINPUT) create two set of keyboard/mouse input devices - one for host and one for guest os,
- provide mode selector (SCROLL_LOCK key) which selects which os receives input events,
- replicate uinput events form real input devices to uinput devices selected by mode selector,
- passthrough uinput device to guest os.

## Secondary problem
Sine Guest is configured to be started during boot of main pc, tihis service is intended to be started during boot and before libvirtd.service to ensure that uinput devices are created before Guest is started. The problem shows up when this service is started with keyboard/mouse connected to the other PC. There are not device based on which uninput devices could be created, thus this service will fail following by libvrtd.service and Guest is not started.

## Secondary solution
- when service is started with keyboard/mouse connected to the main pc, save input devices' capabilities in /var/lib/libvirt-evdev/,
- when service is started with keyboard/mouse connected to the other pc, create proper uinput devices based on previoulsy saved capabilities.

## Extras
### Configuration File
Simple toml file (libvirt-evdev.toml) with definition of input devices, screens and usb switch parameters.

### Screen Input Switch
This service provide Screen Input switch using DDC/CI control (https://github.com/ddccontrol/ddccontrol)

### Instalation
Very basic install script provided (install.sh) which creates mandatory directories and copies files.

### TODO
- improve exception handling
- verify correctness of aysncio usage
- remove dependency to ddccontrol and implement DDC/CI using python-smbus
