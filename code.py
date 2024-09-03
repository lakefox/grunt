import board  # type: ignore
import busio
import digitalio
import time
from adafruit_wiznet5k.adafruit_wiznet5k import WIZNET5K
from adafruit_wiznet5k.adafruit_wiznet5k_socketpool import SocketPool
import pwmio
import adafruit_motor.servo
import grunt
import time


def mac_string_to_tuple(mac_string):
    return tuple(int(part, 16) for part in mac_string.split(":"))

def mac_tuple_to_string(mac_tuple):
    return ":".join(f"{part:02x}" for part in mac_tuple)

def ip_string_to_tuple(ip_string):
    return tuple(int(part) for part in ip_string.split("."))

def ip_tuple_to_string(ip_tuple):
    return ".".join(str(part) for part in ip_tuple)

class SimpleQueue:
    def __init__(self):
        self.queue = []
    
    def append(self, item):
        self.queue.append(item)
    
    def popleft(self):
        if self.queue:
            return self.queue.pop(0)
        else:
            raise IndexError("pop from an empty queue")
    
    def __len__(self):
        return len(self.queue)

# Queue to store incoming messages
message_queue = SimpleQueue()

# Message identifier for G-code messages
GCODE_IDENTIFIER = "[GCODE]"

# Flag to indicate if receive_message is waiting for a message
receiving_message = False

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
    
    if command.startswith("test on"):
        led.value = True
    elif command.startswith("test off"):
        led.value = False
    elif command.startswith("autoauth"):
        code = int(command.split(" ")[1])
        conn.send(f"{code}".encode("utf-8"))
    else:
        machine.run(command)
    return "OK"


machine = grunt.Grunt()

# Stepper 
def g14_handler(args):
    # G14 (S)TEPS (D)IRECTION (+/-)
    s = args.get("S", 0)
    d = args.get("D", "+")
    move_stepper(s,d=="+")
machine.register("G14", g14_handler)

# Servo
def g15_handler(args):
    # G15 (A)ngle
    # Need to add a way to control servo PWM Freq
    a = args.get("A", 0)
    servo.angle = a
machine.register("G15", g15_handler)

# Relay On
def m10_handler(args):
    # M10
    relay.value = True
machine.register("M10", m10_handler)

# Relay Off
def m11_handler(args):
    # M11
    relay.value = True
machine.register("M11", m11_handler)

allowed_pins = [board.GP5]

def read_pin(pin_number):
        print(f"Reading from pin {pin_number}")
        if len(allowed_pins) >= pin_number:
            return 0
        pin = digitalio.DigitalInOut(allowed_pins[pin_number])
        pin.direction = digitalio.Direction.INPUT
        return pin.value
machine.register("READ", read_pin)

def write_pin(pin_number, value):
    print(f"Writing value {value} to pin {pin_number}")
    if len(allowed_pins) > pin_number:
        pin = digitalio.DigitalInOut(allowed_pins[pin_number])
        pin.direction = digitalio.Direction.OUTPUT
        pin.value = bool(value)  # Set pin to True or False based on value
    else:
        print(f"Error: Pin number {pin_number} is out of allowed range")

machine.register("WRITEPIN", write_pin)

def send_message(message):
    full_message = f"{GCODE_IDENTIFIER} {message}"
    conn.send(f"{full_message}\n".encode("utf-8"))
    print(f"Sent message: {full_message}")

machine.register("WRITEMSG", send_message)

def receive_message(timeout):
    global message_queue, receiving_message
    start_time = time.monotonic()
    
    # Set the flag indicating we're waiting for a message
    receiving_message = True
    
    # Check if there is a message in the queue
    if message_queue:
        receiving_message = False
        return message_queue.popleft()

    # Wait for a message with the identifier
    while (time.monotonic() - start_time) < timeout:
        try:
            data = conn.recv(1024).decode("utf-8").strip()
            if data.startswith(GCODE_IDENTIFIER):
                message = data[len(GCODE_IDENTIFIER):].strip()
                receiving_message = False
                return message
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

    # If no message is received within the timeout, reset the flag
    receiving_message = False
    print(f"No message received within {timeout} seconds.")
    return None

machine.register("RECV", receive_message)

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

                # If receive_message is active, skip G-code messages
                if receiving_message and data.startswith(GCODE_IDENTIFIER):
                    continue

                # If it's a G-code message and not waiting, add to the queue
                if data.startswith(GCODE_IDENTIFIER):
                    message_queue.append(data[len(GCODE_IDENTIFIER):].strip())
                    continue

                # Handle other commands
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