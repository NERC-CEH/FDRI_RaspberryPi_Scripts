# FDRI_Development_Scripts
This is the repository where scripts will be inputted for review before pushing to the main repo 

## Getting set up

To install the Python package and dependencies, do the following

Create a virtual environment:

`python -m venv .venv`

Activate the environment

`source .venv/bin/activate`

Install the codebase and dependencies

`pip install -e .`

## How to run fdri_raspicam_v0.2.py

The Python script no longer has any credentials inside, they now come from environment variables and there isn't any logic checking for their existance right now, so any authentication failures should point to these being missing.

To run the script ensure the following environment variables are present:

- AWS_ROLE_ARN - The uploader role
- AWS_BUCKET_NAME - Name of the bucket that receives the images
- AWS_REGION - The region we operate in
- AWS_ACCESS_KEY_ID - AWS access key ID
- AWS_SECRET_ACCESS_KEY - AWS secret access key

They may be loaded in a script or any other mechanism. Once they're loaded, the script may be run `python fdri_raspicam_v0.2.py`

## Dependencies
### Linux
- python3
- python3-picamzero
- libcap-dev
