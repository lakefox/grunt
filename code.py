import board  # type: ignore
import busio
import digitalio
import time
from adafruit_wiznet5k.adafruit_wiznet5k import WIZNET5K
from adafruit_wiznet5k.adafruit_wiznet5k_socketpool import SocketPool
import pwmio
import adafruit_motor.servo

def mac_string_to_tuple(mac_string):
    return tuple(int(part, 16) for part in mac_string.split(":"))

def mac_tuple_to_string(mac_tuple):
    return ":".join(f"{part:02x}" for part in mac_tuple)

def ip_string_to_tuple(ip_string):
    return tuple(int(part) for part in ip_string.split("."))

def ip_tuple_to_string(ip_tuple):
    return ".".join(str(part) for part in ip_tuple)

# Configuration
SPI1_SCK = board.GP10
SPI1_TX = board.GP11
SPI1_RX = board.GP12
SPI1_CSn = board.GP13
W5500_RSTn = board.GP15

STEPPER_STEP_PIN = board.GP3
STEPPER_DIR_PIN = board.GP2

RELAY_PIN = board.GP4
LED_PIN = board.GP25
 
SERVO_PWM_PIN = board.GP6
SERVO_PWM_FREQUENCY = 50

USE_DHCP = True  # Set to False to use static IP
MAC_ADDRESS_STRING = "00:01:02:03:04:05"
IP_ADDRESS_STRING = "192.168.0.111"
SUBNET_MASK_STRING = "255.255.0.0"
GATEWAY_ADDRESS_STRING = "192.168.0.1"
DNS_SERVER_STRING = "8.8.8.8"

# Convert strings to tuples
MY_MAC = mac_string_to_tuple(MAC_ADDRESS_STRING)
IP_ADDRESS = ip_string_to_tuple(IP_ADDRESS_STRING)
SUBNET_MASK = ip_string_to_tuple(SUBNET_MASK_STRING)
GATEWAY_ADDRESS = ip_string_to_tuple(GATEWAY_ADDRESS_STRING)
DNS_SERVER = ip_string_to_tuple(DNS_SERVER_STRING)

# Print to verify
print("MAC Tuple:", MY_MAC)
print("MAC String:", mac_tuple_to_string(MY_MAC))
print("IP Tuple:", IP_ADDRESS)
print("IP String:", ip_tuple_to_string(IP_ADDRESS))

# Initialize SPI and Ethernet
cs = digitalio.DigitalInOut(SPI1_CSn)
spi_bus = busio.SPI(SPI1_SCK, MOSI=SPI1_TX, MISO=SPI1_RX)
ethernetRst = digitalio.DigitalInOut(W5500_RSTn)
ethernetRst.direction = digitalio.Direction.OUTPUT

# Reset W5500
ethernetRst.value = False
time.sleep(1)
ethernetRst.value = True

# Initialize WIZNET5K
eth = WIZNET5K(spi_bus, cs, is_dhcp=USE_DHCP, mac=MAC_ADDRESS_STRING)

if not USE_DHCP:
    eth.ifconfig = (IP_ADDRESS, SUBNET_MASK, GATEWAY_ADDRESS, DNS_SERVER)
else:
    print("DHCP IP Address:", eth.pretty_ip(eth.ip_address))

# Initialize SocketPool
pool = SocketPool(eth)

# Create a socket
sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
sock.settimeout(10)  # Optional: Add a timeout for the socket
sock.bind((eth.pretty_ip(eth.ip_address), 5000))
sock.listen(1)

print("Listening on port 5000...")

# Initialize peripherals
pwm = pwmio.PWMOut(SERVO_PWM_PIN, frequency=SERVO_PWM_FREQUENCY)
servo = adafruit_motor.servo.Servo(pwm)

step_pin = digitalio.DigitalInOut(STEPPER_STEP_PIN)
dir_pin = digitalio.DigitalInOut(STEPPER_DIR_PIN)
step_pin.direction = digitalio.Direction.OUTPUT
dir_pin.direction = digitalio.Direction.OUTPUT

relay = digitalio.DigitalInOut(RELAY_PIN)
relay.direction = digitalio.Direction.OUTPUT

led = digitalio.DigitalInOut(LED_PIN)
led.direction = digitalio.Direction.OUTPUT

listening_pins = {}

# Function to move the stepper motor
def move_stepper(steps, direction):
    dir_pin.value = direction
    for _ in range(steps):
        step_pin.value = True
        time.sleep(0.001)
        step_pin.value = False
        time.sleep(0.001)

# Function to handle commands
def handle_command(command, conn):
    global listening_pins
    
    if command.startswith("servo"):
        angle = int(command.split(" ")[1])
        print(angle)
        servo.angle = angle
    elif command.startswith("relay on"):
        relay.value = True
    elif command.startswith("relay off"):
        relay.value = False
    elif command.startswith("stepper"):
        parts = command.split(" ")
        steps = int(parts[1])
        direction = parts[2].lower() == "forward"
        move_stepper(steps, direction)
    elif command == "kill":
        servo.angle = None
        step_pin.value = False
    elif command.startswith("listen"):
        pin_number = int(command.split(" ")[1])
        try:
            pin = digitalio.DigitalInOut(getattr(board, f"GP{pin_number}"))
            pin.direction = digitalio.Direction.INPUT
            listening_pins[pin_number] = {'pin': pin, 'last_value': pin.value}
            conn.send(f"Listening on pin {pin_number}\n".encode("utf-8"))
        except Exception as e:
            conn.send(f"Error: {e}\n".encode("utf-8"))
    elif command.startswith("unlisten"):
        pin_number = int(command.split(" ")[1])
        if pin_number in listening_pins:
            del listening_pins[pin_number]
            conn.send(f"Stopped listening on pin {pin_number}\n".encode("utf-8"))
        else:
            conn.send(f"Pin {pin_number} is not being listened to.\n".encode("utf-8"))
    elif command.startswith("test on"):
        led.value = True
    elif command.startswith("test off"):
        led.value = False
    elif command.startswith("autoauth"):
        code = int(command.split(" ")[1])
        conn.send(f"{code}".encode("utf-8"))
    return "OK"

# Main loop to listen for commands and poll pins
while True:
    try:
        conn, addr = sock.accept()
        print(f"Connected by {addr}")
        
        while True:
            try:
                # Poll the listening pins for changes
                for pin_number, info in list(listening_pins.items()):
                    pin = info['pin']
                    current_value = pin.value
                    if current_value != info['last_value']:
                        listening_pins[pin_number]['last_value'] = current_value
                        message = f"Pin {pin_number} changed to {current_value}\n"
                        conn.send(message.encode("utf-8"))
                
                # Check for incoming commands
                data = conn.recv(1024).decode("utf-8")
                if not data:
                    break
                response = handle_command(data.strip(), conn)
                conn.send(response.encode("utf-8"))
                
            except Exception as e:
                print(f"Error: {e}")
                break
        
        conn.close()
        print(f"Connection with {addr} closed.")
    
    except KeyboardInterrupt:
        print("Server stopped.")
        sock.close()
        break
