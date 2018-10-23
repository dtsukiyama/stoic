import click
import boto3
import pprint
import os, errno
import subprocess
import tarfile
import shutil
import stat
import docker
import re
import sagemaker as sage
from colorama import Fore, Back, Style

from PyInquirer import prompt, print_json
from utils import modelChoice, repoChoice, abort_if_false, training, prefix
from utils import dirWalk, questions, repos, changeDirectory, stringExtract
from build_db import modelTable, createModel, returnModels, deleteModel

@click.group()
def cli():
    """
    Command line tool to build, train, and deploy ML models.
    """
    pass


@cli.command()
def initdb():
    """
    This intializes a models directory and builds a models table.
    """
    try:
        os.makedirs('models')
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    

    click.echo('model table setup')
    modelTable()



@cli.command()
def models():
    """
    Prints all SageMaker models.
    """
    pprint.pprint(boto3.client('sagemaker').list_models())

@cli.command()
def endpoints():
    """
    Prints all SageMaker endpoints.
    """
    pprint.pprint(boto3.client('sagemaker').list_endpoints())


@cli.command()
@click.argument('container_name')
@click.option('--yes', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Are you sure you want to remove this container?')
def removemodel(container_name):
    current_dir = os.getcwd()
    target = current_dir + "/" + 'models'
    try:
        shutil.rmtree(target+"/"+container_name, ignore_errors=False, onerror=None)
        print('{} sucessfully removed.'.format(container_name))
    except OSError as e:
        print("Error: {} - {}.".format(e.filename, e.strerror))


@cli.command()
def checkmodels():
    """
    This checks current models directory for Docker Model Containers.
    """
    current_dir = os.getcwd()
    target = current_dir + "/" + 'models'
    containers = dirWalk(target)
    models = dict()
    try:
        if len(containers) == 0:
            click.echo("There currently are no models")
        else:
            for container in containers:
                models[container] = [b for b in dirWalk(target + "/" + container) if b != 'local_test']
            print(models)

    except Exception as e:
        print(e)



@cli.command()
@click.argument('container_name')
@click.argument('model_name')
def container(container_name, model_name):
    
    """
    This builds a ML model container template with Dockerfile.
    """
   
    current_dir = os.getcwd()
    target = current_dir + "/" + 'models'

    # check if container already exists
    # current_models = [b[0] for b in returnModels()]
    current_containers = dirWalk(target)
    try:
        if container_name in current_containers:
            click.echo("container name already exists")
        else: 
            #createModel((container_name, model_name))
            source = 'container_build/container_template.tar.gz'
            shutil.copy(source, target)
            process_string = 'tar -xvf {}/container_template.tar.gz --directory {} && mv {}/container_template {}/{} && rm {}/container_template.tar.gz'.format(target,
                                                                                                                                                                target,
                                                                                                                                                                target, 
                                                                                                                                                                target,
                                                                                                                                                                container_name, 
                                                                                                                                                                target)
            subprocess.run([process_string], shell=True)
            rename = 'mv {}/{}/algorithm {}/{}/{}'.format(target, container_name,
                                                          target, container_name, model_name)
            subprocess.run([rename], shell=True)


    except Exception as e:
        print(e)



@cli.command()
def build():
    """
    This builds a Docker image from a model container.
    """
    current_dir = os.getcwd()
    target = current_dir + "/" + 'models'
    dirs = dirWalk(target)
    try:
        if len(dirs) == 0:
            click.echo("There currently are no models")
        else:
            answers = prompt(questions)
            pprint.pprint(answers)
            # create build_and_push executable
            # check if train, serve and build_and_push are executables
            # chmod +x {model}/train
            # chmod +x {model}/serve
            # chmod +x build_and_push.sh
            docker_model = answers['docker model']
            print('Create executables for {}.'.format(docker_model))
            # model
            model = [b for b in dirWalk(target+'/'+docker_model) if b != 'local_test']
           
            train = model[0]+'/train'
            serve = model[0]+'/serve'    
            executables = ['build_and_push.sh', train, serve]
            print(executables)
            
            with changeDirectory(target+'/'+docker_model):
                for _file in executables:
                    st = os.stat(_file)
                    os.chmod(_file, st.st_mode | stat.S_IEXEC)
                raise Exception('Container executables finished')
            print('done')
    
    except Exception as e:
        print(e)



@cli.command()
@click.option('--yes', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Are you sure you want to push docker model to ECR?')
def push():
    """
    This pushes Docker model image to ECR and also build a local Docker image for testing.
    """
    current_dir = os.getcwd()
    target = current_dir + "/" + 'models'
    dirs = dirWalk(target)
    try:
        if len(dirs) == 0:
            click.echo("There currently are no models")

        else:
            answers = prompt(questions)
            pprint.pprint(answers)
            docker_model = answers['docker model']
            model = [b for b in dirWalk(target+'/'+docker_model) if b != 'local_test'][0]
            createModel((docker_model, model))
            with changeDirectory(target+'/'+docker_model):
                command = './build_and_push.sh {}'.format(model)
                subprocess.run([command], shell=True)
            raise Exception('ECR push...')
 
    
    except Exception as e:
        print(e)

@cli.command()
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
    click.echo(models)



@cli.command()
@click.option('--yes', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Are you sure you want to delete the ECR repository?')
def deleterepo():
    #boto3.client('ecr').delete_repository(repostoryName=, 
    #                                      force=True)
    pass


@cli.command()
def listdocker():
    client = docker.from_env()
    images = []
    for b in client.images.list():
        images.extend(stringExtract(str(b)))
    pprint.pprint([image for image in images if 'amazonaws' in image])

@cli.command()
def trainlocal():
    answers = prompt(repos)
    pprint.pprint(answers)
    image = answers['image']
    container, model = image.split(':')
    current_dir = os.getcwd()
    target = current_dir + "/" + 'models'
    executables = ['predict.sh','serve_local.sh','train_local.sh']
    try:
        with changeDirectory(target+'/'+ container + '/local_test'):
            for _file in executables:
                st = os.stat(_file)
                os.chmod(_file, st.st_mode | stat.S_IEXEC)
                command = './train_local.sh {}'.format(model)
                subprocess.run([command], shell=True)

            raise Exception('local train complete')
 
    
    except Exception as e:
        print(e)

@cli.command()
def servelocal():
    answers = prompt(repos)
    pprint.pprint(answers)
    image = answers['image']
    container, model = image.split(':')
    current_dir = os.getcwd()
    target = current_dir + "/" + 'models'
    try:
        with changeDirectory(target+'/'+ container + '/local_test'):
            command = './serve_local.sh {} > outlog.log'.format(model)
            subprocess.run([command], shell=True)
        raise Exception('Local server')
 
    
    except Exception as e:
        print(e)


@cli.command()
@click.argument('payload')
@click.argument('content_type')
def predictlocal(payload, content_type):
    answers = prompt(repos)
    pprint.pprint(answers)
    image = answers['image']
    container, _ = image.split(':')
    current_dir = os.getcwd()
    target = current_dir + "/" + 'models'
    try:
        with changeDirectory(target+'/'+ container + '/local_test'):
            command = './predict.sh {} {}'.format(payload, content_type)
            subprocess.run([command], shell=True)
        raise Exception('local prediction complete')
 
    
    except Exception as e:
        print(e)

@cli.command()
@click.argument('work_directory')
def s3Upload(work_directory):
    """
    Upload model training data to s3.
    """
    sess = sage.Session()
    answers = prompt(prefix)
    pprint.pprint(answers)
    #data_location = sess.upload(work_directory, key_prefix=prefix)
    #print('Data location: '.format(data_location))
    pprint.pprint(answers['prefix'].split(':')[1])
    

@cli.command()
def train():
    """
    Train on AWS infrastructure.
    """
    # requirements: load training data to S3 bucket
    answers = prompt(training)
    pprint.pprint(answers)


