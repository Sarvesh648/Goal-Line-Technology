import smbus2
import time
import struct
import math

# I2C Addresses
TCA9548A_ADDR = 0x70  # TCA9548A Multiplexer
HMC5883L_ADDR = 0x1E  # HMC5883L Magnetometer

# Initialize I2C bus
bus = smbus2.SMBus(1)  # Use I2C bus 1 on Raspberry Pi

# Reference field strength at known distance (example values)
Bref = 500  # in microteslas (uT)
dref = 5    # in cm

# Goal detection flag
goal_detected = False

def select_channel(channel):
    """Select a specific channel on the TCA9548A multiplexer."""
    try:
        bus.write_byte(TCA9548A_ADDR, 1 << channel)
        time.sleep(0.1)
        return True
    except OSError:
        print(f"Error selecting channel {channel}. Check I2C connections!")
        return False

def init_hmc5883l():
    """Initialize the HMC5883L magnetometer."""
    try:
        bus.write_byte_data(HMC5883L_ADDR, 0x00, 0x70)  # Config A: 8 samples, 15Hz
        bus.write_byte_data(HMC5883L_ADDR, 0x01, 0x20)  # Config B: Gain
        bus.write_byte_data(HMC5883L_ADDR, 0x02, 0x00)  # Mode: Continuous
        time.sleep(0.05)
    except IOError:
        print("Error initializing HMC5883L. Check wiring.")

def read_hmc5883l():
    """Read magnetic field values from HMC5883L."""
    try:
        data = bus.read_i2c_block_data(HMC5883L_ADDR, 0x03, 6)
        x, z, y = struct.unpack('>hhh', bytes(data))
        B_total = math.sqrt(x**2 + y**2 + z**2)
        return B_total
    except IOError:
        print("I2C Read Error! Returning 0")
        return 0

def calculate_distance(B_measured):
    """Estimate distance using inverse square law."""
    if B_measured == 0:
        return float('inf')
    return dref * math.sqrt(Bref / B_measured)

# Start system
print("Checking I2C devices...")

if not select_channel(1) or not select_channel(4) or not select_channel(5):
    print("No sensor detected on channels 1, 4, or 5! Exiting.")
    exit()

init_hmc5883l()
time.sleep(0.05)
print("Monitoring Magnetic Field Changes... Press CTRL+C to stop.")

channels = [1, 4, 5]
current_channel = 0

try:
    while True:
        channel = channels[current_channel]
        if select_channel(channel):
            B_measured = read_hmc5883l()
            distance = calculate_distance(B_measured)

            if channel == 5 and distance < 2 and not goal_detected:
                print("Goal Detected!")
                goal_detected = True

            if channel == 5 and distance >= 2:
                goal_detected = False

            print(f"[Channel {channel}] Magnetic Field: {B_measured:.2f} uT, Estimated Distance: {distance:.2f} cm")

        current_channel = (current_channel + 1) % len(channels)
        time.sleep(1.5)

except KeyboardInterrupt:
    print("\nMonitoring stopped.")
