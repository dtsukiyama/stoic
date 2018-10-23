import os, errno
import re
import docker
import yaml
from contextlib import contextmanager
from build_db import returnModels
from PyInquirer import Validator, ValidationError

CONFIG = yaml.load(open('configurations/config.yaml', 'r'))
sagemaker_role   = CONFIG['roles'][0]['role'] 
sagemaker_bucket = CONFIG['descriptions'][0]['bucket']



@contextmanager
def changeDirectory(newdir):
    """
    Credit goes here: https://stackoverflow.com/questions/431684/how-do-i-change-directory-cd-in-python/24176022#24176022
    Context manager is the best way to be pythonically safe 
    """
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


def dirWalk(target):
    return next(os.walk(target))[1]


def modelChoice():
    try:
        os.makedirs('models')
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    current_dir = os.getcwd()
    target = current_dir + "/" + 'models'
    return dirWalk(target)


def stringExtract(string):
    return re.findall(r"'(.*?)'", string, re.DOTALL)


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


def repoChoice():
    models = returnModels()
    return [str(model[0] + ":" + model[1]) for model in models]
    

def listrepos():
    """
    This lists all Docker images in ECR repository.
    """
    repos = returnModels()
    client = boto3.client('ecr')
    models = dict()
    for repo in repos:
        models[repo[0]] = {'repo': repo[1],
                           'image_data': client.list_images(repositoryName=repo[1])['imageIds']}
    return models

def listdocker():
    client = docker.from_env()
    images = []
    for b in client.images.list():
        images.extend(stringExtract(str(b)))
    return [image for image in images if 'amazonaws' in image]



questions = [
        {
        'type': 'list',
        'name': 'docker model',
        'message': 'Select model to build',
        'choices': modelChoice()
        }]


repos = [
        {
        'type': 'list',
        'name': 'image',
        'message': 'Select local image',
        'choices': repoChoice() 
        }]

prefix = [
        {
        'type': 'list',
        'name': 'prefix',
        'message': 'Select s3 data upload prefix name',
        'choices': repoChoice() 
        }]


training = [
           {'type':'list',
            'name':'AlgorithmSpecification',
            'message':'Which Image?',
            'choices': listdocker()},


           {'type':'list',
            'name':'InstanceType',
            'message':'What instance type?',
            'choices':['ml.m4.xlarge','ml.m4.2xlarge','ml.m4.4xlarge','ml.m4.10xlarge','ml.m4.16xlarge',
                       'ml.p2.xlarge','ml.p2.8xlarge','ml.p2.16xlarge']},

           {'type':'list',
            'name':'InstanceCount',
            'message':'How many instances?',
            'choices':['One','Two','Three']}
]



