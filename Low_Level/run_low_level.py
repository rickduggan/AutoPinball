# Source correct files
import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../Classes') # Still is not how I should be doing this, but...it works

# Schedule tasks
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime  
from datetime import timedelta 

# Status of playfield
from playfield import Playfield

# Ros stuff
import rospy
from std_msgs.msg import Int32
from std_msgs.msg import Int32MultiArray
from std_msgs.msg import Bool
from pinball_messages.srv import get_light, get_lightResponse
from pinball_messages.srv import get_switch, get_switchResponse
from pinball_messages.msg import override_light

# Time and scheduling
import time

# Capture ctl + c
import signal

# Will use flipper.general_flipper_on_time if time_until_off is set. 
# Set it to 0 to hold
def flipper_on(flipper, time_util_off=-1):
    flipper.on = True
    flipper.last_time_on = rospy.get_rostime().to_sec()
    flipper_pub.publish(flipper.flipper_num)
    if time_util_off > 0:
        try:
            schedule.add_job(flipper_off, 'date', run_date=(datetime.now() + timedelta(seconds=time_util_off)), args=[flipper], id=str(flipper.flipper_num) + "OFF")
        except:
            print("Tried to schedule flipper off: " + str(flipper.flipper_num))
    elif time_util_off == 0:
        # Will HOLD the flipper until you turn it off
        pass
    else:
        try:
            schedule.add_job(flipper_off, 'date', run_date=(datetime.now() + timedelta(seconds=flipper.general_flipper_on_time)), args=[flipper], id=str(flipper.flipper_num) + "OFF")
        except:
            print("Tried to schedule flipper off: " + str(flipper.flipper_num))

def flipper_off(flipper):
    flipper.on = False
    flipper_pub.publish(flipper.flipper_num * -1)

# Schedule a time to turn a light on
def schedule_on(light, time_until):
    try:
        schedule.add_job(turn_on, 'date', run_date=calc_date(time_until, light), args=[light], id=str(light.pin) + "ON")
    except:
        print("Tried to schedule on, job with same name, no can do!")

# Schedule a time to turn a light off
def schedule_off(light, time_until):
    try:
        schedule.add_job(turn_off, 'date', run_date=calc_date(time_until, light), args=[light], id=str(light.pin) + "OFF") 
    except:
        print("Tried to schedule off, job with same name, no can do!")

# Calculate the time to turn on or off a light
def calc_date(seconds_in_future, light):
    if light.blink_start_time == -1:
        return datetime.now() + timedelta(seconds=seconds_in_future)
    elif light.on:
        return light.blink_start_time + timedelta(seconds=(seconds_in_future + (2*light.curr_number_blink * seconds_in_future)))
    elif not light.on:
        return light.blink_start_time + timedelta(seconds=(seconds_in_future + ((2*light.curr_number_blink - 1) * seconds_in_future)))

# Here we reset all playfield components to begin the game
def reset_all_components():
    # Let the user know we are resetting the game
    print("Deleting all events")
    
    # Turn off all lights
    for row in myPlay.lights: # for every row in the playfield (top, mid, bot)...
        for curr_light in myPlay.lights[row]: # ...and for every element 'i' in that row...
            light_off_pub.publish(curr_light.pin)

    # New playfield reference
    myPlay.reset()
    myPlay.setup_pins()

    # clear all old scheduled events
    for job in schedule.get_jobs():
        job.remove()

    # Publish out that we have no points
    update_score(0)
    update_bonus(0)

# Keeps the last five commands stored here so we can change mode if you get a sertain combo:
def new_switch_hit(pin):
    myPlay.switch_list.append(pin)
    myPlay.switch_list.pop(0)
    switch_list_pub.publish(data=myPlay.switch_list)

# Publishes out new score value
def update_score(score_to_add):
    print(myPlay.mode)
    if myPlay.mode != "Idle" and myPlay.mode != "Idle_Waiting":
        myPlay.score += score_to_add
        update_score_pub.publish(myPlay.score)

# Published out new bonus value
def update_bonus(bonus_to_add):
    myPlay.bonus += (bonus_to_add * myPlay.bonus_modifier)
    update_bonus_pub.publish(myPlay.bonus)

# Based on ROS srv of row and column, return the information inside the light
def handle_get_light(req):
    light = myPlay.lights[req.row][req.column]
    return get_lightResponse(light.on, light.last_time_on, light.pin, light.general_light_on_time, light.override_light) # Have a lookup table for information

# Based on ROS srv of row and column, return the information inside the light
def handle_get_switch(req):
    switch = myPlay.switches[req.row][req.column]
    return get_switchResponse(switch.on, switch.last_time_on, switch.pin, switch.num_times_triggered)

# Can put the mode of any switch into "Blink, Hold, etc." 
def handle_override_light(override):
    light = myPlay.lights[override.row][override.column]
    if override.override == light.override_light:
        pass
    else:
        light.override_light = override.override
        if override == "None":
            turn_off(light)
        else:
            turn_on(light)

def local_override_light(override, light):
    if override == light.override_light:
        pass
    else:
        light.override_light = override
        if override == "None":
            turn_off(light)
            light.curr_number_blink = 0
            light.blink_start_time = -1
            try:
                schedule.remove_job(str(light.pin) + "ON")
            except:
                print("Tried to remove job, but no name - NONE")
        else:
            light.curr_number_blink = 0
            light.blink_start_time = datetime.now()
            try:
                schedule.remove_job(str(light.pin) + "ON")            
            except:
                print("Tried to remove job, but no name - ON")
            try:
                schedule.remove_job(str(light.pin) + "OFF")            
            except:
                print("Tried to remove job, but no name - OFF")
            turn_on(light)



# Turns on a light. If it is supposed to be blinking, it tells it to turn off
def turn_on(light):
    light.on = True
    light.last_time_on = rospy.get_rostime().to_sec()
    light_on_pub.publish(light.pin)
    if light.override_light == "Blink_Slow":
        schedule_off(light, 1)
        light.curr_number_blink += 1
    elif light.override_light == "Blink_Med":
        schedule_off(light, 0.6)
        light.curr_number_blink += 1
    elif light.override_light == "Blink_Fast":
        schedule_off(light, 0.3)
        light.curr_number_blink += 1
    else:
        schedule_off(light, light.general_light_on_time)

    #print("on")

# Turns off a light. If it is supposed to be blinking, it tieels it to turn on
def turn_off(light):
    light.on = False
    light_off_pub.publish(light.pin)
    if light.override_light == "Blink_Slow":
        schedule_on(light, 1)
    elif light.override_light == "Blink_Med":
        schedule_on(light, 0.6)
    elif light.override_light == "Blink_Fast":
        schedule_on(light, 0.3)

    #print("off")

# Callback for each switch on the playfield...
def switch_top_0(data):
    switch = myPlay.switches["top"][0]
    light = myPlay.lights["top"][0]
    if light.override_light == "None":
        turn_on(light)
    switch.num_times_triggered += 1
    new_switch_hit(switch.pin)
    update_score(10000)
    # Do other things, score, etc.
    
def switch_mid_0(data):
    switch = myPlay.switches["mid"][0]
    light = myPlay.lights["mid"][0]
    if light.override_light == "None":
        turn_on(light)
    switch.num_times_triggered += 1
    new_switch_hit(switch.pin)
    update_score(1000)
    # Do other things, score, etc.

def switch_bot_0(data):
    switch = myPlay.switches["bot"][0]
    light = myPlay.lights["bot"][0]
    if light.override_light == "None":
        turn_on(light)
    switch.num_times_triggered += 1
    new_switch_hit(switch.pin)
    update_score(100)
    # Do other things, score, etc.

def switch_bot_1(data):
    print("Ball Drained")
    switch = myPlay.switches["bot"][1]
    new_switch_hit(switch.pin)
    reset_all_components()
    myPlay.mode = "Idle"

def switch_start_button(data):
    print("Start Button Pressed!")
    reset_all_components()
    myPlay.mode = "Normal_Play"

# Capture ros shutdown
def signal_handler():
        print('\nExiting...')
        schedule.shutdown()

        # Turn off all lights
        for row in myPlay.lights: # for every row in the playfield (top, mid, bot)...
            for curr_light in myPlay.lights[row]: # ...and for every element 'i' in that row...
                light_off_pub.publish(curr_light.pin)

# The status of the playfield, lights, switches, score, etc
myPlay = Playfield()

# ROS initialization and shutdown
rospy.init_node('low_level')
rospy.on_shutdown(signal_handler)

# Ros services to return the lights and switches
get_light_service = rospy.Service('get_light', get_light, handle_get_light)
get_switch_service = rospy.Service('get_switch', get_switch, handle_get_switch)

# ROS subscriber to change the status of a light from blinking to not or vice versa
override_light_sub = rospy.Subscriber("override_light", override_light, handle_override_light)

# ROS subscribers for each switch that will exist on the playfield
switch_top_0_sub = rospy.Subscriber("switch_top_0_triggered", Bool, switch_top_0)
switch_mid_0_sub = rospy.Subscriber("switch_mid_0_triggered", Bool, switch_mid_0)
switch_bot_0_sub = rospy.Subscriber("switch_bot_0_triggered", Bool, switch_bot_0)
switch_bot_1_sub = rospy.Subscriber("switch_bot_1_triggered", Bool, switch_bot_1)

# ROS subscirber that checkes when the start button is pressed
switch_start_button_sub = rospy.Subscriber("switch_start_button_triggered", Bool, switch_start_button)

# ROS publishers to turn on or off lights
light_on_pub = rospy.Publisher('light_on', Int32, queue_size=10)
light_off_pub = rospy.Publisher('light_off', Int32, queue_size=10)

# ROS publisher to update score
update_score_pub = rospy.Publisher('update_score', Int32, queue_size=10)
update_bonus_pub = rospy.Publisher('update_bonus', Int32, queue_size=10)

# ROS publisher for when a new switch is hit
switch_list_pub = rospy.Publisher('switch_list', Int32MultiArray, queue_size=10)

# Flipper Publisher
flipper_pub = rospy.Publisher('flip_flipper', Int32, queue_size=10)

# Scheduler to keep track of when we want to turn on.off devices on the playfield
schedule = BackgroundScheduler()
schedule.start()

if __name__ == "__main__":
    myPlay.setup_pins()

    # Make sure everything is off at startup
    for row in myPlay.lights: # for every row in the playfield (top, mid, bot)...
        for curr_light in myPlay.lights[row]: # ...and for every element 'i' in that row...
            light_off_pub.publish(curr_light.pin)

    '''
    while not rospy.is_shutdown():
        print(myPlay.switch_list)
        switch_bot_0(True)
        time.sleep(2)
        switch_mid_0(True)
        time.sleep(2)
    '''

    rate = rospy.Rate(10)

    '''
    local_override_light("Blink_Slow", myPlay.lights["top"][0])
    local_override_light("Blink_Med", myPlay.lights["mid"][0])
    local_override_light("Blink_Fast", myPlay.lights["bot"][0])
    
    time.sleep(.5)

    local_override_light("Blink_Slow", myPlay.lights["top"][0])
    local_override_light("Blink_Slow", myPlay.lights["mid"][0])
    local_override_light("Blink_Slow", myPlay.lights["bot"][0])
    '''
    myPlay.mode = "Idle"

    # Keep the scheduler in a loop
    while not rospy.is_shutdown():
        if myPlay.mode == "Idle":
            # TODO: Change this to be by pin number maybe? that way I can do one loop?
            print("Game Setting Up")
            i = 1
            for row in myPlay.lights: # for every row in the playfield (top, mid, bot)...
                for curr_light in myPlay.lights[row]: # ...and for every element 'i' in that row...
                    i += 1
                    if i % 2 == 0 and curr_light.pin != -1:
                        local_override_light("Blink_Slow", light=curr_light)
            i = 1
            time.sleep(1)
            for row in myPlay.lights: # for every row in the playfield (top, mid, bot)...
                for curr_light in myPlay.lights[row]: # ...and for every element 'i' in that row...
                    i += 1
                    if i % 2 == 1 and curr_light.pin != -1:
                        local_override_light("Blink_Slow", light=curr_light)
            print("Done Setting up")
            myPlay.mode="Idle_Waiting"

        if myPlay.mode == "Normal_Play":
            print("Normal_Play")
            print(myPlay.lights["top"][0].override_light)
            #local_override_light("Blink_Med", light=myPlay.lights["top"][0])
            pass

        #if myPlay.mode == "High_Score":


        rate.sleep()