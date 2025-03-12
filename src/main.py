"""
File:	main.py
Author:	Zachary Milke
Description: This file controls a light which indicates whether or not the fish in our fish tank
    have been fed or not. It sets the need_feeding variable to True every 6 hours, which sets the
    state of the indicating LED to HIGH. Upon an external users click of the "fed" button, it will
    reset the need_feeding flag to False, shutting off the indicating LED.

Changelog
----------
03-Feb-2025
    - File created
04-Feb-2025
    - Optimized power & memory consumption through the following:
        1. Reduced clock speed from 125MHz to 62.5MHz
        2. Removed wasteful global variables
---------------------------------------------------------------------------------------------------
"""


# -------------------------------------------------------------------------------------------------
# Imports -----------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

from machine import (
    Pin,            # Accessing GPIO pins
    freq,			# Setting the CPU frequency. Comment out to disable import.
    lightsleep      # Putting device into light sleep mode
)
from utime import (
    ticks_ms,       # Measuring tick values
    ticks_diff,     # Measuring elapsed time between tick values
    sleep_ms        # Small, stability delays
)
from sys import exit


# -------------------------------------------------------------------------------------------------
# Settings ----------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

# Frequency at which the device CPU should run. Base frequency on the Pico used to test is 125 MHz
#	Min. freq. is ~0.5x  base frequency (62.5 MHz)
#	Max. freq. is ~2.24x base frequency (280 MHz)
#
# As you can probably imagine, using a lower frequency will come at the cost of performance, but
#	the device will consume less power. For this application, the half frequency is more than
#	enough considering all this system does is tell me when my fish need to be fed.
#
# Comment out the following two lines to use the devices base CPU speed.
freq(125_000_000 // 2)

# The following two variables control the duration of time after a feeding occurs before the next
#	feeding needs to take place. They are positive integers greater than or equal to zero.
#
# E.g., the following two variables would result in the feed indicator turning on every 6.5 hours
#	feed_delay_hr = 6
#	feed_delay_min = 30
feed_delay_hr: int 	= 6
feed_delay_min: int = 0

# Convert the total feeding delay to milliseconds
#	Step 1: Convert the feed_delay_hr to minutes
#	Step 2: Add the value from step 1 to the feed_delay_min variable
#	Step 3: Multiply the value from step 2 by 60 to get seconds
#	Step 4: Multiply the value from step 3 by 1000 to get milliseconds
feed_delay_ms: int = (((feed_delay_hr * 60) + feed_delay_min) * 60) * 1_000

# Constants used to assist in making calculations easier
ms_in_one_second: int = 1_000
ms_in_one_minute: int = 1_000 * 60
ms_in_one_hour: int = 1_000 * 60 * 60

# Boolean indicating if a feeding needs to take place. This is True by default, so it is
#	recommended that users power the device as they are feeding their fish, that way the timing is
#	accurate for the next feeding.
feeding_required: bool = True

# Integer used to hold the tick counter captured the last time the feed button was pressed
last_feeding_ticks: int = 0


# -------------------------------------------------------------------------------------------------
# Peripherals -------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

# LED connected to GPIO 0, then to ground with a 220 ohm resistor
#	The feed indicator is set HIGH (on) when a feeding needs to take place, and LOW (off) when a
#	feeding is not required.
feed_indicator: Pin = Pin(0, Pin.OUT, value=feeding_required)

# 6mm x 6mm x 6mm push button connected to GPIO 1, then to 3v3 OUT (physical pin 37 on this Pico)
#	The feed button is used to indicate that a feeding has taken place. Presses are only registered
#	when a feeding needs to take place.
feed_button: Pin = Pin(1, Pin.IN, Pin.PULL_DOWN)
    

# -------------------------------------------------------------------------------------------------
# Main Loop ----------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------

# Wrap in a try clause to assist with debugging
try:
    while True:
        # If the feeding required bool is True,
        if feeding_required:     
            # If the feed button has been pressed,
            if feed_button.value():
                # Set the feed indicator LED low (off)
                feed_indicator.off()
                
                # Update the last feeding ticks count
                last_feeding_ticks = ticks_ms()
                
                # Reset the feeding required flag
                feeding_required = False
                
                # Let the console know a feeding has taken place
                print("The fish have been fed")
        else:
            # Calculate the elapsed time since last feeding
            #	Step 1: Get the current tick counter
            #	Step 2: Calculate the elapsed time in ms between the last feeding and now
            current_ticks: int = ticks_ms()
            elapsed_ms: int = ticks_diff(current_ticks, last_feeding_ticks)
            
            # Calculate time until next feeding.
            #	The next two lines, along with the print statement outputting them can be commented
            #	out to have a more "production-esque" module. They are helpful when debugging
            remaining_hours: int = feed_delay_hr - (elapsed_ms // ms_in_one_hour)
            remaining_mins: int = feed_delay_min - (elapsed_ms - (remaining_hours * ms_in_one_hour)) // ms_in_one_minute if feed_delay_min != 0 else 0
            
            # Output time remaining to the console
            print(f"{remaining_hours} hour(s) {remaining_mins} minutes(s) until next feeding")
            
            # Check if enough time has passed since the last feeding to require another
            if feed_delay_ms <= elapsed_ms:
                # Set the feeding required to True and the feed indicator HIGH
                feeding_required = True
                feed_indicator.on()
                
                # Continue to avoid going to sleep
                continue

            # Feeding not required, put device to light sleep for one minute
            lightsleep(ms_in_one_minute)

except KeyboardInterrupt:
    print("Keyboard interrupt detected, exiting.")
    exit(0)
except Exception as err:
    print("Unkown exception occurred, details:\n{}".format(err))
    exit(-1)