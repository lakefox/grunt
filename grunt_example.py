import grunt

# Example usage:
machine = grunt.Grunt()

# Example G-code event handlers
def g1_handler(args):
    x = args.get("X", None)
    y = args.get("Y", None)
    f = args.get("F", "+")
    print(f"G1 command: Moving to X={x}, Y={y}, F={f}")

def g14_handler(args):
    x = args.get("S", None)
    y = args.get("C", None)
    f = args.get("F", "+")

    print(f"G14 command: Moving to Steps: S={x}, Micro step size C={y} {f}")

def m2_handler(args):
    print("M2 command: Ending program")

# Register handlers
machine.register("G1", g1_handler)
machine.register("G14", g14_handler)
machine.register("G15", g1_handler)
machine.register("G16", g1_handler)

machine.register("M2", m2_handler)


def read_pin(pin_number):
        print(f"Reading from pin {pin_number}")
        return 123.45  # Example value
machine.register("READ", read_pin)


def receive_message(timeout):
        print(f"Receiving message with timeout {timeout}")
        return "received_command"  # Example command
machine.register("RECV", receive_message)


def send_message(message):
        print(f"Sent message: {message}")
machine.register("WRITEMSG", send_message)

def write_pin(pin_number, value):
        print(f"Writing value {value} to pin {pin_number}")
machine.register("WRITEPIN", write_pin)

# Full G-code example using all requested features
gcode_program = """
; Initialize variables
#1 = 0
#2 = 3
#speed = 100

; Define a macro that moves to a specified position
MACRO move_to
    G1 X[$1] Y[$2] F[#speed]
ENDMACRO

; Conditional to check if #1 is less than #2
IF [#1 LT #2]
    ; Move to (X10, Y20) at the specified speed
    G1 X10 Y20 F[#speed] ; Move to a starting position
ENDIF

; Loop from #i = 1 to 3
FOR #i 1 3
    ; Call the move_to macro with #i and 10 as arguments
    CALL move_to #i 10.0
    ; Increment the speed by 20
    #speed = [#speed + 20]
ENDFOR

; A while loop that runs while #1 is less than or equal to #2
WHILE [#1 LE #2]
    ; Move to positions based on the current value of #1 and #2
    CALL move_to #1 [#1 * 2]
    ; Increment #1
    #1 = [#1 + 1]
ENDWHILE

; Read a sensor value from pin 7
#sensor_value = [READ 7]
G14 S100 C16 
; Write a value to a pin using a variable
WRITE 1 [#sensor_value]

; Send a message
WRITE "Operation complete"

; Wait for a command with a 10-second timeout
#command = [RECV 10]

; Write the received command
WRITE [#command]

; Multiple commands on a single line
G1 X50 Y75 F200

; End the program
M2
"""

# Parse and execute G-code
machine.run(gcode_program)