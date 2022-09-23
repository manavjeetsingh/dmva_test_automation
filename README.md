# Automating the manual testing commands for dmva pipeline project

## Following flags and arguments can be used with the script.
```
$ ./automate.py -h
-h - prints this help message
-bci - build common docker image
-bdi - build decoder docker image
-xk8 - do not create new k8_configs and apply it-vid <path_to_video> - give path to custom video image for testing
-r <k8config_name.yaml>:<no of replicas> - Runs the mentioned number of replicas for the block. Default=1.
-cpu_r <k8config_name.yaml>:<millicores> - sets request cpu in millicores for the given block. Default=1000
-cpu_l <k8config_name.yaml>:<millicores> - sets cpu limit in millicores for the given block. Default=1000
-o /path/to/k8_config_folder - sets custom k8_configs folder. By default used from *_k8_details.json"
```

## Following are the configuration files and folders

- common_server_details.json: Contails information about the docker image server used by all blocks except decoder. Following is a sample:

```
{
    "docker_image_path": "..",
    "docker_image_name": "server_o",
    "docker_image_tag": "0.0.2"
}
```

- decoder_k8_details.json: Contains information about the docker image server for decoder block. Following is a sample:

```
{
    "docker_image_path": "../livego",
    "docker_image_name": "server_decoder",
    "docker_image_tag": "0.0.5"
}
```

- common_k8_details.json: Contains the name of the k8 config file and final path where that config should be put. This file is for all k8 configs using common docker image. Following is an example:

```
{
    "counting_deployment.yaml": "../k8s_configurations",
    "detector_deployment.yaml": "../k8s_configurations",
    "resize_deployment.yaml": "../k8s_configurations"
}
```

- decoder_k8_details.json: Contains the name of the k8 config file and final path where that config should be put. This file is only for configs using decoder docker image. Following is an example:
```
{
    "decoder_deployment.yaml": "../k8s_configurations"
}
```
- k8_configs_templates: This contains the k8 config template files. All configs mentioned in common_k8_details.json and decoder_k8_details.json should be present here. The place where docker image details are required should be replaced with {{DOCKER}}. Currently there is support for setting CPU request, CPU limit and replicas. These numbers should be replaced by {{CPU_R}}, {{CPU_L}} and {{REPLICAS}} respectively.