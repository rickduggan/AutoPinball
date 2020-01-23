/*
 * Author: Tyler Gragg
 * Date First Created: 01/18/2019
 * Project: AutoPinball
 */

#include <ros.h>
#include <std_msgs/Int32.h>

// Light Outputs
#define TopLight1 5
#define TopLight2 11
#define MidLight1 4
#define MidLight2 16
#define BotLight1 3
#define BotLight2 21

// Flipper Outputs
#define LeftFlipper 1
#define RightFlipper 2

// Switch Inputs
#define TopSwitch1 11
#define TopSwitch2 26
#define MidSwitch1 12
#define MidSwitch2 31
#define BotSwitch1 13
#define BotSwitch2 36

// ROS Node Handle
ros::NodeHandle nh;

// ROS Published messages
//TODO: Possibly add a publisher for each switch triggered
std_msgs::Int32 int_msg;
ros::Publisher switch_pub("switch_triggered", &int_msg);

//TODO: Possibly add callback for each flipper - then I could change to bool
void flip_callback(const std_msgs::Int32& flipper){
  // 1 = left_flipper ON, 2 = right_flipper ON, -1 = left_flipper OFF, -2 = right_flipper OFF
  if (flipper.data == 1){
    digitalWrite(LeftFlipper, HIGH);
  }
  else if(flipper.data == 2){
    digitalWrite(RightFlipper, HIGH); 
  }
  else if(flipper.data == -1){
    digitalWrite(LeftFlipper, LOW);
  }
  else if(flipper.data == -2){
    digitalWrite(RightFlipper, LOW);
  }
}

// Turn on whatever int comes in
void light_on_callback(const std_msgs::Int32& light){
  digitalWrite(light.data, HIGH);
}

// Turn off whatever int comes in
void light_off_callback(const std_msgs::Int32& light){
  digitalWrite(light.data, LOW);
}


// ROS Subscibed messages
ros::Subscriber<std_msgs::Int32> flip_sub("flip_flipper", &flip_callback);
ros::Subscriber<std_msgs::Int32> light_on_sub("light_on", &light_on_callback);
ros::Subscriber<std_msgs::Int32> light_off_sub("light_off", &light_off_callback);

//TODO: Possibly add publisher for each switch
void checkSwitches(){
  if (!digitalRead(TopSwitch1)){
    int_msg.data = TopSwitch1;
    switch_pub.publish(&int_msg);
    nh.spinOnce();
  }
  /*
  if (!digitalRead(TopSwitch2)){
    int_msg.data = TopSwitch2;
    switch_pub.publish(&int_msg);
    nh.spinOnce();
  }
  */
  if (!digitalRead(MidSwitch1)){
    int_msg.data = MidSwitch1;
    switch_pub.publish(&int_msg);
    nh.spinOnce();
  }
  /*
  if (!digitalRead(MidSwitch2)){
    int_msg.data = MidSwitch2;
    switch_pub.publish(&int_msg);
    nh.spinOnce();
  }
  */
  if (!digitalRead(BotSwitch1)){
    int_msg.data = BotSwitch1;
    switch_pub.publish(&int_msg);
    nh.spinOnce();
  }
  /*
  if (!digitalRead(BotSwitch2)){
    int_msg.data = BotSwitch2;
    switch_pub.publish(&int_msg);
    nh.spinOnce();
  }
  */
}

void setup(){
  // Setutp Inputs annd outputs
  pinMode(TopLight1, OUTPUT);
  pinMode(TopLight2, OUTPUT);
  pinMode(MidLight1, OUTPUT);
  pinMode(MidLight2, OUTPUT);
  pinMode(BotLight1, OUTPUT);
  pinMode(BotLight2, OUTPUT);
  pinMode(LeftFlipper, OUTPUT);
  pinMode(RightFlipper, OUTPUT);

  pinMode(TopSwitch1, INPUT_PULLUP);
  pinMode(TopSwitch2, INPUT_PULLUP);
  pinMode(MidSwitch1, INPUT_PULLUP);
  pinMode(MidSwitch2, INPUT_PULLUP);
  pinMode(BotSwitch1, INPUT_PULLUP);
  pinMode(BotSwitch2, INPUT_PULLUP);
  
  nh.initNode();
  nh.advertise(switch_pub);
  nh.subscribe(flip_sub);
  nh.subscribe(light_on_sub);
  nh.subscribe(light_off_sub);
}

void loop(){
  checkSwitches();
  nh.spinOnce();
}
