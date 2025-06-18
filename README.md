# FDRI Raspberry Pi Camera

This repository holds the script and configuration for setting up a Raspberry Pi camera to monitor the environment on one of the FDRI sites.

## Getting set up

This code has dependencies on `libcamera` which can only be used on Rasberry PI's, so it cannot be installed on any other machine.

### Install the linux dependencies
```
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install python3 python3-picamzero python3-libcamera libcap-dev -y
```

## Deploy on a Raspberry PI

Load the code onto a Raspberry Pi by pulling the git repository to it. To do this you need an internet connection.

First, create a [deploy key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys#deploy-keys) on the GitHub repository.

Copy the private key onto the Rasberry PI into `~/.ssh/id_github`.

Create a config file in `~/.ssh/config`

```
Host github.com
    IdentityFile ~/.ssh/id_github
```

Clone the repository

```shell
git clone git@github.com:NERC-CEH/FDRI_RaspberryPi_Scripts.git
```

When there is a code change you can then run:
```shell
git pull
```

## Configuration

### Site configuration

The file `config.yaml` in the `config` directory contains a description of the site. It looks like this:

```
site: CARGN
lat: 51.8626453
lon: -0.2031049
camera: SE
direction: E
interval: 3000
```

This is used to control the capture interval, create the filenames, and use the location's sun times to tell when to stop and start taking pictures.

### Environment variables
The code expects some environment variables to connect to AWS.
These are set in the file `.env`

```shell .env
AWS_ROLE_ARN="<>"
AWS_BUCKET_NAME="<>"
AWS_ACCESS_KEY_ID="<>"
AWS_SECRET_ACCESS_KEY="<>"
```

Where the "<>" has been replaced with the secrets. Ask @JacHam12 or @metazool if you don't know what they are.

- AWS_ROLE_ARN - The uploader role
- AWS_BUCKET_NAME - Name of the bucket that receives the images
- AWS_ACCESS_KEY_ID - AWS access key ID
- AWS_SECRET_ACCESS_KEY - AWS secret access key

### Site-specific configuration

Replace the values in `config.yaml` with those of your specific installation

```
site: CARGN
lat: 51.8626453
lon: -0.2031049
camera: SE
direction: E
```

### Setup script

`setup.sh` automates most steps of the setup - upgrades the Pi's packages with apt, installs our python code and configures it to run through `systemctl`.

```shell
bash setup.sh
```

### Create a Virtual Environment

Because `libcamera` is installed as a linux package it will be installed into the default `python3` installation so you need an extra flag when creating a virtual environment

```
python -m venv --system-site-packages .venv
``` 
Activate the environment

```shell
source .venv/bin/activate
```

Install the codebase and dependencies

```shell
pip install -e .
```

## How to Run the Code


An example of how to run the code is in [./src/rasberrycam/\_\_main\_\_.py](src/raspberrycam/__main__.py). This can be run as:

```shell
python src/raspberrycam/__main__.py
```

or

```bash
# Special invocation for a file called __main__.py
python -m raspberrycam
```

Ensure that the latitude/longitude are set correctly or the python code may exit at the wrong time.

# fdri_assets
