#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import torch
import torch.nn as nn
import torchvision
import torch.nn.functional as F
import torchvision.transforms as transforms
import torchvision.models as models

from std_msgs.msg import String
from dslam_sp.msg import TransformStampedArray, PoseStampedArray, InterMatch
from dslam_sp.srv import *
import numpy as np
from PIL import Image
import os
import rospy
from geometry_msgs.msg import TransformStamped
from dslam_sp.msg import image_depth, PRrepresentor, TransformStampedArray, MatchedFrame
from cv_bridge import CvBridge, CvBridgeError
import cv2
import sys, getopt 

###################
# added by jianming 
import time
from time_profiling_node_prevar import TIME_PROFILING
from time_profiling_node_prevar import TIME_PROFILING_PATH
###################



self_ID = 1
# frame 规则是 self_ID*1e8 + framecount

FileDir = "/PATH/TO/DATASET/";
bridge = None
looptrans_frames_pub = None
loop_inter_pub = {}
inter_posearray_pub = {}
inter_transarray_pub = {}


def callback(msg):
    if(TIME_PROFILING):
        start =time.time()
    global bridge, self_ID, FileDir, looptrans_frames_pub, inter_transarray, inter_posearray_pub, inter_transarray_pub
    frameids = msg.data.split()
    frameid1 = frameids[0]
    frameid2 = frameids[1]
    # print("loop detected!!!")
    print(frameid1, frameid2)
    robotid1 = int(int(frameid1)/1e8)
    robotid2 = int(int(frameid2)/1e8)
    if (robotid1 == robotid2): #如果是本机的local回环
        assert (robotid1 == self_ID)

        #把对应的图片读取进来
        fileid1 = int(int(frameid1) % 1e8 )
        fileid2 = int(int(frameid2) % 1e8 )
        image1_name = "{filepath}/left_{fileid}.png".format(filepath = FileDir, fileid = fileid1)
        image1 = cv2.imread ( image1_name, -1 )
        depth1_name = "{filepath}/depth_{fileid}.png".format(filepath = FileDir, fileid = fileid1)
        depth1 = cv2.imread ( depth1_name, -1 )

        image2_name = "{filepath}/left_{fileid}.png".format(filepath = FileDir, fileid = fileid2)
        image2 = cv2.imread ( image2_name, -1 )
        depth2_name = "{filepath}/depth_{fileid}.png".format(filepath = FileDir, fileid = fileid2)
        depth2 = cv2.imread ( depth2_name, -1 )
        # print("depth2.shape"+str(depth2.shape))

        publishMsg = MatchedFrame()
        publishMsg.frame1.header.frame_id = frameid1 #先来的
        publishMsg.frame2.header.frame_id = frameid2 #后来的


        tpm1 = 0
        # print("depth2")
        # print(depth2)
        # print("depth2 end")
        publishMsg.frame1.image = bridge.cv2_to_imgmsg(image1, "passthrough")
        publishMsg.frame1.depth = bridge.cv2_to_imgmsg(depth1, "passthrough")

        publishMsg.frame2.image = bridge.cv2_to_imgmsg(image2, "passthrough")
        publishMsg.frame2.depth = bridge.cv2_to_imgmsg(depth2, "passthrough")

        looptrans_frames_pub.publish(publishMsg)
    else : # 是不同的两个机器人
        assert (robotid1 == self_ID) #其中第一个ID得是自己
        if not loop_inter_pub.has_key(str(robotid2)):
            # inter_posearray_pub[str(robotid2)] = rospy.Publisher("/robot{}/loopinterpose".format(robotid2),PoseStampedArray, queue_size=3)
            # inter_transarray_pub[str(robotid2)] = rospy.Publisher("/robot{}/loopintertrans".format(robotid2),TransformStampedArray, queue_size=3)

            loop_inter_pub[str(robotid2)] = rospy.Publisher("/robot{}/loopinterframe".format(robotid2),InterMatch, queue_size=3)
        interframesMsg = InterMatch()
        interframesMsg.frameid2 = frameid2 #对方的
        fileid1 = int(int(frameid1) % 1e8 ) #自己的
        image1_name = "{filepath}/left_{fileid}.png".format(filepath = FileDir, fileid = fileid1)
        image1 = cv2.imread ( image1_name, -1 )
        depth1_name = "{filepath}/depth_{fileid}.png".format(filepath = FileDir, fileid = fileid1)
        depth1 = cv2.imread ( depth1_name, -1 )
        interframesMsg.frame1.image = bridge.cv2_to_imgmsg(image1, "passthrough")
        interframesMsg.frame1.depth = bridge.cv2_to_imgmsg(depth1, "passthrough")
        interframesMsg.frame1.header.frame_id = frameid1

        # rospy.wait_for_service('/robot{}/posearray_srv'.format(self_ID) )
        # posearray_srvhandle = rospy.ServiceProxy('/robot{}/posearray_srv'.format(self_ID), posearray_srv)
        # posearray_result = posearray_srvhandle(str(self_ID))
        # print("loop find server!!!")
        # rospy.wait_for_service('/robot{}/transarray_srv'.format(self_ID) )
        # transarray_srvhandle = rospy.ServiceProxy('/robot{}/transarray_srv'.format(self_ID), transarray_srv)
        # transarray_result = transarray_srvhandle(str(self_ID))
        # print("loop get server!!!")


        # inter_posearray_pub[str(robotid2)].publish(posearray_result.posearray)
        # inter_transarray_pub[str(robotid2)].publish(transarray_result.transarray)
        loop_inter_pub[str(robotid2)].publish(interframesMsg)
        # print("loop publised!!!")
        if(TIME_PROFILING):
            ofile = open(TIME_PROFILING_PATH + "string2frame_loopstring.txt", 'a')
            end = time.time()
            ofile.write('string2frame_loopstring time: %s Seconds'%(end-start))
            ofile.write('\n')


def intercallback(msg):
    if(TIME_PROFILING):
        start =time.time()
    global bridge, self_ID, FileDir, looptrans_frames_pub
    frameid2 = msg.frameid2  
    robotid2 = int(int(frameid2)/1e8)
    if(robotid2 == self_ID):
        fileid2 = int(int(frameid2) % 1e8 )      
        image2_name = "{filepath}/left_{fileid}.png".format(filepath = FileDir, fileid = fileid2)
        image2 = cv2.imread ( image2_name, -1 )
        depth2_name = "{filepath}/depth_{fileid}.png".format(filepath = FileDir, fileid = fileid2)
        depth2 = cv2.imread ( depth2_name, -1 )

        publishMsg = MatchedFrame()
        publishMsg.frame1 = msg.frame1 #对方的，和发送端相反
        publishMsg.frame2.header.frame_id = frameid2 #自己的，和发送端相反
        
        publishMsg.frame2.image = bridge.cv2_to_imgmsg(image2, "passthrough")
        publishMsg.frame2.depth = bridge.cv2_to_imgmsg(depth2, "passthrough")

        looptrans_frames_pub.publish(publishMsg)

    if(TIME_PROFILING):
        ofile1 = open(TIME_PROFILING_PATH + "string2frame_loop_interframe.txt", 'a')
        end = time.time()
        ofile1.write('string2frame_loop_interframe time: %s Seconds'%(end-start))
        ofile1.write('\n')



def main(argv):

    global looptrans_pub, looptrans_frames_pub, self_ID, FileDir, bridge
    opts, args = getopt.getopt(argv,"i:p:")
    for opt, arg in opts:
        if opt in ("-i"):
            self_ID = int(arg)
        if opt in ("-p"):
            FileDir = arg

    rospy.init_node('matcher', anonymous=True)
    bridge = CvBridge()
    print("test log OK")
    rospy.Subscriber("loopstring", String, callback)
    rospy.Subscriber("/robot{}/loopinterframe".format(self_ID), InterMatch, intercallback)
    looptrans_frames_pub = rospy.Publisher("loopframe",MatchedFrame, queue_size=3)

    rospy.spin()



if __name__ == '__main__':
    main(sys.argv[1:])