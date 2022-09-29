#!/usr/bin/python3
import os
import inspect
import json
import time
import threading
import sys
import io

# GLOBAL VARS
class vars:
    def __init__(self): #Also take all these as arguments
        self.BUILD_COMMON_IMAGE=False
        self.BUILD_DECODER_IMAGE=False
        self.VIDEO_FILE_PATH="../2.flv"
        self.CONFIG_DICT=None
        self.K8_CONFIG_PATH=None
        self.DEFAULT_REPLICAS="1"
        self.DEFAULT_CPU_R="1000"
        self.DEFAULT_CPU_L="1000"
        self.APPLY_K8_CONFIGS=True

GLOBAL=vars()

def log(s):
    print("::>",inspect.stack()[1][3]+':',s)

def execute(command):
    ret=os.system(command)
    if ret!=0:
        print("ERROR: %s, command did not work"%(command))
        sys.exit(1)


def build_docker(path_to_dockerfile,image_name,image_tag):
    """
    Builds docker image based on given image name and image tag
    """
    command='docker build -t %s:%s %s'%(image_name,image_tag,path_to_dockerfile)
    log(command)
    execute(command)

def usertag_docker_image(image_name, image_tag, username):
    """
    Tags the already created docker image with a username
    """    
    command='docker tag %s:%s %s/%s:%s'%(image_name,image_tag, username, image_name,image_tag)
    log(command)
    execute(command)

def push_docker_image(image_name, image_tag, username, password):
    """
    Logs in dockerhub using given username and password and pushes the
    already tagged image to dockerhub.
    """
    command='docker login -u "%s" -p "%s" docker.io'%(username, password)
    log(command)
    execute(command)
    command='docker push %s/%s:%s'%(username, image_name,image_tag)
    log(command)
    execute(command)

def write_to_file(file_content,new_path):
    file = open(new_path, "w") #new_path also contains file name
    file.write(file_content)
    file.close()

## REMOVE IT
# def replace_write_file(placeholder, replace_content, path, file_name,new_path):
#     """
#     Replace a placeholder in the template and puts the image into
#     actual k8s_configs
#     """
#     file = open(path+"/"+file_name,mode='r')
#     file_content = file.read()
#     file.close()

#     file_content=file_content.replace(placeholder, replace_content)
#     new_path=new_path+"/"+file_name
#     write_to_file(file_content,new_path)

def change_docker_k8_configs(k8_configs_dict,docker_username, image_name, image_tag):
    """
    adds docker image info in the k8 template and puts k8 template into final position.
    """
    for config_type in k8_configs_dict: # dict is like filename.yaml: path, where to put final file
        docker_image = 'image: %s/%s:%s'%(docker_username,image_name,image_tag)
        log("Adding "+docker_image+" -> "+config_type)
        try:
            GLOBAL.CONFIG_DICT[config_type]=\
                GLOBAL.CONFIG_DICT[config_type].replace('{{DOCKER}}',docker_image)
        except Exception as e:
            print(e)
            print("Did you put entry in *_k8_details.json?")
            sys.exit(1)
        
def apply_k8_configs(k8_details):
    """
    Apply the k8 configrations to pods
    """
    time.sleep(1)
    for k8 in k8_details:
        config_path=k8_details[k8]+"/"+k8
        command='kubectl apply -f %s'%(config_path)
        log(command)
        execute(command)


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
    Gives the ip of decoder pod from the k8 cluster
    """
    ip=None
    raw_data=os.popen("kubectl get pods -o wide").read()
    buf = io.StringIO(raw_data)
    for line in buf.readlines():
        if line.split()[0].split("-")[0]=='decoder':
            ip=line.split()[5]
            log("Decoder ip is: "+ip)
            break
    if ip!=None:
        return ip
    else:
        raise Exception("Cannot find decoder IP, is decoder running?")


def make_decoder_listen():
    decoder_ip=get_decoder_ip()
    command="curl "+decoder_ip+":5057/add-decode-task/?source=rtmp%3A%2F%2F130.245.127.103%3A1935%2Flive%2Fsample2"
    log("Curling the decoder: " + command)
    execute(command)


def start_ffmpeg_server():
    time.sleep(2) # waiting for decoder to get ready
    log("Video path: "+GLOBAL.VIDEO_FILE_PATH)
    command='ffmpeg -re -i %s -c copy -f flv rtmp://localhost:1935/live/sample2'%(GLOBAL.VIDEO_FILE_PATH)
    execute(command)

def main(common_server_details,decoder_server_details,docker_hub_details,common_k8_details,decoder_k8_details):
    

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

    if GLOBAL.APPLY_K8_CONFIGS:
        # making k8 configs using common server
        change_docker_k8_configs(common_k8_details,docker_hub_details['uname'],common_server_details["docker_image_name"]\
            ,common_server_details["docker_image_tag"])

        # making k8 config using decoder server
        change_docker_k8_configs(decoder_k8_details,docker_hub_details['uname'],decoder_server_details["docker_image_name"]\
            ,decoder_server_details["docker_image_tag"])
        
        save_config_files(common_k8_details,decoder_k8_details)

        apply_k8_configs(common_k8_details)
        apply_k8_configs(decoder_k8_details)


        log("Sleeping for 300 seconds after apply k8 configs.")
        time.sleep(300)

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
        elif (arg=='-xk8'):
            GLOBAL.APPLY_K8_CONFIGS=False
        elif (arg=='-bci'):
            GLOBAL.BUILD_COMMON_IMAGE=True
        elif (arg=='-bdi'):
            GLOBAL.BUILD_DECODER_IMAGE=True
        elif (arg=='-vid'):
            i+=1
            try:
                GLOBAL.VIDEO_FILE_PATH=sys.argv[i]
                if GLOBAL.VIDEO_FILE_PATH[0]=='-':
                    raise Exception("Cannot path -vid argument")
            except Exception as e:
                print("Cannot parse video name:",e)
                sys.exit(1)
        elif (arg=='-r'):
            i+=1
            try:
                arg=sys.argv[i]
                if arg[0]=='-':
                    raise Exception("Cannot parse -r argument")
                
                k8_config_name,replicas=arg.split(':')

                if replicas=='':
                    raise Exception("Cannot parse -r argument")


                if k8_config_name in GLOBAL.CONFIG_DICT.keys():
                    GLOBAL.CONFIG_DICT[k8_config_name]=\
                        GLOBAL.CONFIG_DICT[k8_config_name].replace('{{REPLICAS}}', replicas)
                    log("REPLICAS set to "+replicas+" in k8_configs")
                    
                else:
                    raise Exception("wrong k8_config_name: %s. Suggestion: add .yaml in the name if not already done."%k8_config_name)

            except Exception as e:
                print("Cannot parse number of replicas:",e)
                sys.exit(1)

        elif (arg=='-cpu_r'):
            i+=1
            try:
                arg=sys.argv[i]
                if arg[0]=='-':
                    raise Exception("Cannot parse -cpu_r argument")
                
                k8_config_name,cpu_r=arg.split(':')

                if cpu_r=='':
                    raise Exception("Cannot parse -cpu_r argument")

                if k8_config_name in GLOBAL.CONFIG_DICT.keys():
                    GLOBAL.CONFIG_DICT[k8_config_name]=\
                        GLOBAL.CONFIG_DICT[k8_config_name].replace('{{CPU_R}}', cpu_r)
                    log("CPU_R set to "+cpu_r+" in k8_configs")
                    
                else:
                    raise Exception("wrong k8_config_name. Suggestion: add .yaml in the name if not already done.")

            except Exception as e:
                print("Cannot parse number of cpu request:",e)
                sys.exit(1)

        elif (arg=='-cpu_l'):
            i+=1
            try:
                arg=sys.argv[i]
                if arg[0]=='-':
                    raise Exception("Cannot parse -l argument")
                
                k8_config_name,cpu_l=arg.split(':')

                if cpu_l=='':
                    raise Exception("Cannot parse -cpu_l argument")

                if k8_config_name in GLOBAL.CONFIG_DICT.keys():
                    GLOBAL.CONFIG_DICT[k8_config_name]=\
                        GLOBAL.CONFIG_DICT[k8_config_name].replace('{{CPU_L}}', cpu_l)
                    log("CPU_L set to "+cpu_l+" in k8_configs")
                    
                else:
                    raise Exception("wrong k8_config_name. Suggestion: add .yaml in the name if not already done.")

            except Exception as e:
                print("Cannot parse number of cpu limit:",e)
                sys.exit(1)

        elif (arg=='-o'):
            i+=1
            try:
                arg=sys.argv[i]
                if arg[0]=='-':
                    raise Exception("Cannot parse -o argument")
                
                GLOBAL.K8_CONFIG_PATH=arg
                log("K8 config out set to "+arg)

            except Exception as e:
                print("Cannot parse k8 config out path:",e)
                sys.exit(1)


def help():
    """
    prints the help message
    """
    help_message=[
        '-h - prints this help message',
        '-bci - build common docker image',
        '-bdi - build decoder docker image',
        '-xk8 - do not create new k8_configs and apply it'
        '-vid <path_to_video> - give path to custom video image for testing',
        '-r <k8config_name.yaml>:<no of replicas> - Runs the mentioned number of replicas for the block. Default=1.',
        '-cpu_r <k8config_name.yaml>:<millicores> - sets request cpu in millicores for the given block. Default=3500',
        '-cpu_l <k8config_name.yaml>:<millicores> - sets cpu limit in millicores for the given block. Default=3500',
        '-o /path/to/k8_config_folder - sets custom k8_configs folder. By default used from *_k8_details.json"'
    ]

    for i in help_message:
        print(i)


def get_config_files(common_k8_details,decoder_k8_details):
    """
    Loads the k8_config files into the memory and returns as a dictionary.
    """
    to_ret={}

    for file_name in common_k8_details:
        file = open("./k8_configs_templates/"+file_name,mode='r')
        data = file.read()
        file.close()

        to_ret[file_name]=data

    for file_name in decoder_k8_details:
        file = open("./k8_configs_templates/"+file_name,mode='r')
        data = file.read()
        file.close()
        to_ret[file_name]=data
    return to_ret

def set_config_defaults():
    """
    Set default vaulues in the config files if not given as arguments
    """
    pass
    for k8_config_name in GLOBAL.CONFIG_DICT:
        GLOBAL.CONFIG_DICT[k8_config_name]=GLOBAL.CONFIG_DICT[k8_config_name]\
            .replace('{{REPLICAS}}', GLOBAL.DEFAULT_REPLICAS)

        GLOBAL.CONFIG_DICT[k8_config_name]=GLOBAL.CONFIG_DICT[k8_config_name]\
            .replace('{{CPU_L}}', GLOBAL.DEFAULT_CPU_L)

        GLOBAL.CONFIG_DICT[k8_config_name]=GLOBAL.CONFIG_DICT[k8_config_name]\
            .replace('{{CPU_R}}', GLOBAL.DEFAULT_CPU_R)


def save_config_files(common_k8_details,decoder_k8_details):
    """
    Saves the k8 configration files in the given or default location.
    """
    if GLOBAL.K8_CONFIG_PATH!=None:
        for k8_config_name in common_k8_details:
            write_to_file(GLOBAL.CONFIG_DICT[k8_config_name],GLOBAL.K8_CONFIG_PATH+'/'+k8_config_name)

        for k8_config_name in decoder_k8_details:
            write_to_file(GLOBAL.CONFIG_DICT[k8_config_name],GLOBAL.K8_CONFIG_PATH+'/'+k8_config_name)

    else:
        for k8_config_name in common_k8_details:
            write_to_file(GLOBAL.CONFIG_DICT[k8_config_name],common_k8_details[k8_config_name]+'/'+k8_config_name)

        for k8_config_name in decoder_k8_details:
            write_to_file(GLOBAL.CONFIG_DICT[k8_config_name],decoder_k8_details[k8_config_name]+'/'+k8_config_name)
if __name__=="__main__":
    common_server_details,decoder_server_details,docker_hub_details,common_k8_details,decoder_k8_details=read_details()

    config_files=get_config_files(common_k8_details,decoder_k8_details)
    GLOBAL.CONFIG_DICT=config_files
    parse_input()
    set_config_defaults()
    main(common_server_details,decoder_server_details,docker_hub_details,common_k8_details,decoder_k8_details)
    