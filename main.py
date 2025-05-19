"""
File:			main.py
Author:			Zachary Milke
Description: 	This module runs at boot, controlling the light which reminds me to feed my fish.
"""

# ---------------------------------------------------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------------------------------------------------

from machine import Pin, Timer, freq
from micropython import const
from utime import sleep_ms


# ---------------------------------------------------------------------------------------------------------------------
# GPIO Pins
# ---------------------------------------------------------------------------------------------------------------------

PIN_LED_FEED_INDICATOR: int = const(14)		# GPIO pin tied to indicating LED
PIN_BTN_RESET_FEED: int = const(16)			# GPIO pin tied to reset button


# ---------------------------------------------------------------------------------------------------------------------
# Peripherals
# ---------------------------------------------------------------------------------------------------------------------

# Red LED set HIGH (on) when a feeding needs to take place, otherwise, LOW (off).
led_feed_indicator: Pin = Pin(PIN_LED_FEED_INDICATOR, Pin.OUT, value=0)

# Click once when the indicating LED is HIGH to reset, or twice while it is LOW to manually reset the timer.
btn_reset_feed: Pin = Pin(PIN_BTN_RESET_FEED, Pin.IN, Pin.PULL_DOWN)


# ---------------------------------------------------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------------------------------------------------

# Next two variables are used to set the duration of time between each feedings. E.g., the following values would
#	result in a total duration of 1 hour 45 minutes from when the timer is started to when the indicator is set HIGH.
#
#	FEED_DELAY_SEC = 0
#	FEED_DELAY_MIN = 45
#	FEED_DELAY_HR = 1
#
# The absolute value functions act as a safety check for accidental negative values, so try to avoid removing them.

FEED_DELAY_SEC: int = const(abs(0))
FEED_DELAY_MIN: int = const(abs(0))
FEED_DELAY_HR: int = const(abs(6))

# Total feed delay takes the sum of the three values above, after converting each to milliseconds.
total_feed_delay_ms: int = const(
    (FEED_DELAY_SEC * 1_000) +
    (FEED_DELAY_MIN * 60 * 1_000) +
    FEED_DELAY_HR * 60 * 60 * 1_000)

# True when a feeding is required, otherwise, False. True by default, meaning it will set indicating LED HIGH at boot.
feed_required: bool = True

# True when a feeding took place, otherwise, False. False by default.
feed_event: bool = False

# Duration of time after a button press is registered in which another press needs to occur in order for the system
#	to register it as a double click. This value is expressed in milliseconds (1000 ms = 1 sec).
BTN_DBL_CLK_THRESH_MS: int = const(250)

# Previous state of the push button, used for software debouncing.
btn_prev_state: bool = btn_reset_feed.value()


# ---------------------------------------------------------------------------------------------------------------------
# Software Timers
# ---------------------------------------------------------------------------------------------------------------------

# Timer used to set the feed reminder values. Runs once and not again until reset.
timer_feed_reminder: Timer = None

# Timer used to detect a double click event. Runs once and not again until reset.
timer_btn_dbl_clk: Timer = None


# ---------------------------------------------------------------------------------------------------------------------
# Interrupt Service Routines
# ---------------------------------------------------------------------------------------------------------------------

def ISR_Expire_Double_Click_Timer(double_click_timer: Timer) -> None:
    """ Expires the double click timer, thus, closing the window of time users have to register a double click
            event.
    
    params
    -----
    double_click_timer [required, machine.Timer] : Software timer the ISR is attached to.
    """
    
    # Get the global variables modified within the ISR
    global timer_btn_dbl_clk

    # Deinitialize and Nullify the double click timer
    timer_btn_dbl_clk.deinit()
    timer_btn_dbl_clk = None
    

def ISR_Set_Feed_Reminder(feed_reminder_timer: Timer) -> None:
    """ Sets feed reminder variables HIGH when called by the feed reminder timer.

    params
    -----
    feed_reminder_timer [required, machine.Timer] : Software timer the ISR is attached to.
    """
    
    # Get required global variables modified within the ISR
    global feed_required
    global timer_feed_reminder
    
    # Deinitiailize and Nullify the feed reminder timer
    timer_feed_reminder.deinit()
    timer_feed_reminder = None
    
    # Set feed_required to True, indicating LED HIGH
    feed_required = True
    led_feed_indicator.on()


def ISR_Handle_PB_Click(push_button: Pin) -> None:
    """ Handle input from the push button.

    params
    -----
    push_button [required, machine.Pin] : Push button peripheral the ISR is attached to.
    """
    
    # Turn off ISR while executing to avoid more spawning
    btn_reset_feed.irq(handler=None)
    
    # Grab required global variables modified within the ISR
    global feed_event
    global btn_prev_state
    global timer_btn_dbl_clk
    global timer_feed_reminder
    
    # Get the current state of the button
    current_state: bool = btn_reset_feed.value()
    
    # Software debounce by verifying the switch just turned on and the previous state was off (state change)
    if current_state == 1 and btn_prev_state == 0:
        # Button state has changed to pushed (HIGH).
        
        # Handle button presses differently depending on whether a feeding is required or not.
        if feed_required:
            # Button has been pressed to indicate a feeding took place, update the feed_event boolean
            feed_event = True
        else:
            # When a feeding is not required, a double click indicates a feeding took place and the feed timer should
            #	be restarted.
            
            # Check if the double click timer exists, meaning the previous press opened the double click window
            if timer_btn_dbl_clk:
                # Double click detected, set the feed_event bool HIGH
                timer_feed_reminder.deinit()
                feed_event = True
            else:
                # Open the double click window by initializing a new timer
                timer_btn_dbl_clk = Timer(period=BTN_DBL_CLK_THRESH_MS, mode=Timer.ONE_SHOT,
                                          callback=ISR_Expire_Double_Click_Timer)                
    
    # Update the previous state of the button to the current state
    btn_prev_state = current_state
    
    # Re-assign ISR to button
    btn_reset_feed.irq(handler=ISR_Handle_PB_Click)


# Attach the ISR_Handle_PB_Click ISR to the associated button
btn_reset_feed.irq(handler=ISR_Handle_PB_Click)


# ---------------------------------------------------------------------------------------------------------------------
# Static Functions
# ---------------------------------------------------------------------------------------------------------------------

def perform_feeding_event() -> None:
    """ Performs a feeding event, resetting the feed related variables. """
    
    # Grab required global variables modified within the function
    global timer_feed_reminder
    global feed_required
    global feed_event
    
    # Set the feed_required and feed_event booleans to False
    feed_required = False
    feed_event = False
    
    # Initialize a new feed reminder timer
    timer_feed_reminder = Timer(period=total_feed_delay_ms, mode=Timer.ONE_SHOT, callback=ISR_Set_Feed_Reminder)
    
    # Acknowledgement flashes
    for i in range(3):
        led_feed_indicator.off()
        sleep_ms(250)
        led_feed_indicator.on()
        sleep_ms(500)
    
    # Finish with the indicating LED LOW
    led_feed_indicator.off()


# ---------------------------------------------------------------------------------------------------------------------
# Main Block
# ---------------------------------------------------------------------------------------------------------------------

# Power optimization:
#	- Decrease CPU clock speed from 125 Mhz to 62.5 Mhz. This value may prove problematic as it has only been tested
#       using a Pico, and should be commented out if device doesn't function as expected when using it.

freq(62_500_000)

# Memory Optimizations:
#	- Variables holding the GPIO pin values are not used passed the initialization of the peripherals, they may be
#		deleted to save RAM.
#	- Variables holding the FEED_DELAY_HR, FEED_DELAY_MIN values are not used after the total feed delay has been set,
#		they may be deleted to save RAM.

del PIN_LED_FEED_INDICATOR
del PIN_BTN_RESET_FEED

del FEED_DELAY_SEC
del FEED_DELAY_MIN
del FEED_DELAY_HR

# Desired behavior is to require a feeding behavior at boot. To do this, Initialize a feed timer with a period of 1ms
timer_feed_reminder = Timer(period=1, mode=Timer.ONE_SHOT, callback=ISR_Set_Feed_Reminder)

# Main Loop (forever)
while True:
    # Check if a feeding is required and if a feed event took place, or if just a feed event took place.
    if feed_event:
        # Feeding was performed, call the perform_feeding_event function
        perform_feeding_event()

