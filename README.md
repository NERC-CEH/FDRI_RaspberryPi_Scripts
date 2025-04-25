# FDRI_Development_Scripts
This is the repository where scripts will be inputted for review before pushing to the main repo 

## Getting set up

This code has dependencies on `libcamera` which can only be used on Rasberry PI's, so it cannot be installed on any other machine.

### Install the linux dependencies
```
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install python3 python3-picamzero python3-libcamera libcap-dev -y
```

### Get the Repository Onto a Rasberry PI

The best way to get the code onto a Rasberry PI and ensure it stays up to date is to pull the git repository to it. To do this you need an internet connection.

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
The code expects some environment variables, so create a bash script with the contents:
```shell
export AWS_ROLE_ARN="<>"
export AWS_BUCKET_NAME="<>"
export AWS_ACCESS_KEY_ID="<>"
export AWS_SECRET_ACCESS_KEY="<>"
```

Where the "<>" has been replaced with the secrets. Ask WP2 if you don't know what they are.

To run the bash script ensure the following environment variables are present:

- AWS_ROLE_ARN - The uploader role
- AWS_BUCKET_NAME - Name of the bucket that receives the images
- AWS_ACCESS_KEY_ID - AWS access key ID
- AWS_SECRET_ACCESS_KEY - AWS secret access key

An example of how to run the code is in [./src/rasberrycam/\_\_main\_\_.py](./src/rasberrycam/__main__.py). This can be run as:

```shell
python src/rasberrycam/__main__.py
```

or

```bash
# Special invocation for a file called __main__.py
python -m rasberrycam
```

Ensure that the latitude/longitude are set correctly or the python code may exit at the wrong time.

