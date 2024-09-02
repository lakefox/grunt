# Install Circuit Python

Hold `bootsel` button, load pico as a flash drive, then drop this `.UF2` file into the drive
<https://circuitpython.org/board/raspberry_pi_pico/>

Then use MU Editor to run/use the code

## Accessing Server

```sh
nc 192.168.0.111 5000
```

then enter commands

## Listing ip addresses

```sh
arp -a
```

## Install circuit python libraries

```sh
sudo circup install adafruit_wiznet5k
also
pipx install
```

## Motor driver

<https://lastminuteengineers.com/a4988-stepper-motor-driver-arduino-tutorial/>
