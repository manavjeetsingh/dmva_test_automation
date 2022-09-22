#!/usr/bin/python3
from ast import Global
import os
import inspect
import json
import time
import threading
import sys

# GLOBAL VARS
class vars:
    def __init__(self): #Also take all these as arguments
        self.BUILD_COMMON_IMAGE=False
        self.BUILD_DECODER_IMAGE=False
        self.VIDEO_FILE_PATH="../2.flv"

GLOBAL=vars()

def log(s):
    print("::>",inspect.stack()[1][3]+':',s)


def build_docker(path_to_dockerfile,image_name,image_tag):
    """
    Builds docker image based on given image name and image tag
    """
    command='docker build -t %s:%s %s'%(image_name,image_tag,path_to_dockerfile)
    log(command)
    os.system(command)

def usertag_docker_image(image_name, image_tag, username):
    """
    Tags the already created docker image with a username
    """    
    command='docker tag %s:%s %s/%s:%s'%(image_name,image_tag, username, image_name,image_tag)
    log(command)
    os.system(command)

def push_docker_image(image_name, image_tag, username, password):
    """
    Logs in dockerhub using given username and password and pushes the
    already tagged image to dockerhub.
    """
    command='docker login -u "%s" -p "%s" docker.io'%(username, password)
    log(command)
    os.system(command)
    command='docker push %s/%s:%s'%(username, image_name,image_tag)
    log(command)
    os.system(command)

def replace_write_file(placeholder, replace_content, path, file_name,new_path):
    """
    Replace a placeholder in the template and puts the image into
    actual k8s_configs
    """
    file = open(path+"/"+file_name,mode='r')
    file_content = file.read()
    file.close()

    file_content=file_content.replace(placeholder, replace_content)

    new_path=new_path+"/"+file_name
    file = open(new_path, "w")
    file.write(file_content)
    file.close()

def change_docker_k8_configs(k8_configs_dict,docker_username, image_name, image_tag):
    """
    adds docker image info in the k8 template and puts k8 template into final position.
    """
    for config_type in k8_configs_dict: # dict is like filename.yaml: path, where to put final file
        docker_image = 'image: %s/%s:%s'%(docker_username,image_name,image_tag)
        log("Adding "+docker_image+" -> "+k8_configs_dict[config_type]+"/"+config_type)
        replace_write_file("{{DOCKER}}", docker_image, './k8_configs_templates',\
            config_type,k8_configs_dict[config_type])

def apply_k8_configs(k8_details):
    """
    Apply the k8 configrations to pods
    """
    for k8 in k8_details:
        config_path=k8_details[k8]+"/"+k8
        command='kubectl apply -f %s'%(config_path)
        log(command)
        os.system(command)


def read_details():
    """
    Loads and returns json details.
    """
    common_server_details = json.load(open('./common_server_details.json'))
    decoder_server_details = json.load(open('./decoder_server_details.json'))
    docker_hub_details = json.load(open('./docker_hub_details.json'))
    common_k8_details = json.load(open('./common_k8_details.json'))
    decoder_k8_details = json.load(open('./decoder_k8_details.json'))

    return common_server_details,decoder_server_details,docker_hub_details,common_k8_details,decoder_k8_details

def get_decoder_ip():
    """
    TODO: Write this
    """
    return "0.0.0.0"

def make_decoder_listen():
    decoder_ip=get_decoder_ip()
    command="curl "+decoder_ip+":5057/add-decode-task/?source=rtmp%3A%2F%2F130.245.127.103%3A1935%2Flive%2Fsample_2"
    log("Curling the decoder: " + command)
    # os.system(command)


def start_ffmpeg_server():
    time.sleep(2) # waiting for decoder to get ready
    log("Video path: "+GLOBAL.VIDEO_FILE_PATH)
    command='ffmpeg -re -i %s -c copy -f flv rtmp://localhost:1935/live/sample2'%(GLOBAL.VIDEO_FILE_PATH)
    # os.system(command)

def main():
    common_server_details,decoder_server_details,docker_hub_details,common_k8_details,decoder_k8_details=read_details()

    if GLOBAL.BUILD_COMMON_IMAGE:
        #Building and pushing the common docker image
        build_docker(common_server_details["docker_image_path"], common_server_details["docker_image_name"]\
            , common_server_details["docker_image_tag"])
        usertag_docker_image(common_server_details["docker_image_name"],common_server_details["docker_image_tag"]\
            ,docker_hub_details['uname'])
        push_docker_image(common_server_details["docker_image_name"],common_server_details["docker_image_tag"]\
            ,docker_hub_details['uname'],docker_hub_details['passwd'])

    if GLOBAL.BUILD_DECODER_IMAGE:
        #Building and pushing the common docker image
        build_docker(decoder_server_details["docker_image_path"], decoder_server_details["docker_image_name"]\
            , decoder_server_details["docker_image_tag"])
        usertag_docker_image(decoder_server_details["docker_image_name"],decoder_server_details["docker_image_tag"]\
            ,docker_hub_details['uname'])
        push_docker_image(decoder_server_details["docker_image_name"],decoder_server_details["docker_image_tag"]\
            ,docker_hub_details['uname'],docker_hub_details['passwd'])

    # making k8 configs using common server
    change_docker_k8_configs(common_k8_details,docker_hub_details['uname'],common_server_details["docker_image_name"]\
        ,common_server_details["docker_image_tag"])

    # making k8 config using decoder server
    change_docker_k8_configs(decoder_k8_details,docker_hub_details['uname'],decoder_server_details["docker_image_name"]\
        ,decoder_server_details["docker_image_tag"])
    
    # apply_k8_configs(common_k8_details)
    # apply_k8_configs(decoder_k8_details)

    # log("Sleeping for 30 seconds after apply k8 configs.")
    # time.sleep(30)

    # Curling the decoder to make it listen to the server
    
    x = threading.Thread(target=make_decoder_listen, args=())
    x.start()

    #Running the ffmpeg server with flv file
    start_ffmpeg_server()

    
def parse_input():
    """
    parse the command line input
    """
    for i in range(1,len(sys.argv)):
        arg=sys.argv[i]
        # print(arg)
        if (arg=='-h'):
            help()
            sys.exit(0)
        elif (arg=='-bci'):
            GLOBAL.BUILD_COMMON_IMAGE=True
        elif (arg=='-bdi'):
            GLOBAL.BUILD_DECODER_IMAGE=True
        elif (arg=='-vid'):
            i+=1
            try:
                GLOBAL.VIDEO_FILE_PATH=sys.argv[i]
                if GLOBAL.VIDEO_FILE_PATH[0]=='-':
                    raise Exception("")
            except:
                print("Cannot parse video name.")
                sys.exit(1)

def help():
    """
    prints the help message
    """
    help_message=[
        '-h: prints this help message',
        '-bci - build common docker image',
        '-bdi - build decoder docker image',
        '-vid <path_to_video> - give path to custom video image for testing',
        #TODO
        '-r <k8config_name.json>:<no of replicas> - Runs the mentioned number of replicas for the block',
        '-cpu_req <k8config_name.json>:<millicores> - sets request cpu in millicores for the given block',
        '-cpu_limit <k8config_name.json>:<millicores> - sets cpu limit in millicores for the given block' 
    ]

    for i in help_message:
        print(i)

if __name__=="__main__":
    #TODO: create a temporary copy of k8_config templates and change info there, 
    # only after all that is done, move it to k8s_configurations
    parse_input()
    main()
    