from fabric.contrib.files import append, exists
from fabric.api import env, local, run, cd, task, prefix, warn_only, quiet
import random

env.project_pkg = 'superlists'
env.repo_url = 'https://github.com/bhrutledge/superlists.git'

@task
def staging():
    env.hosts = ['debugged.org']
    env.user = 'rutt'
    env.app_name = 'superlists_staging'
    env.app_port = '27916'
    env.app_url = 'superlists-staging.bhrutledge.com'
    env.python = '/usr/local/bin/python3.3'

    init_env()

def init_env():
    env.user_dir = '/home/%(user)s' % env
    env.project_dir = '%(user_dir)s/webapps/%(app_name)s' % env
    env.static_dir = '%(user_dir)s/webapps/%(app_name)s_static' % env
    env.workon = 'workon %(app_name)s' % env
    env.wsgi_app = '%(project_pkg)s.wsgi:application' % env
    env.pid_path = '%(project_dir)s/gunicorn.pid' % env

@task
def deploy():
    # Assume project and static apps are set up
    # Assume virtualenvwrapper works on login

    mkvirtualenv()
    git_reset()
    pip_install()
    local_settings()
    collectstatic()
    syncdb()
    restart()

def mkvirtualenv():
    if run(env.workon).failed:
        run('mkvirtualenv -p %(python)s -a %(project_dir)s %(app_name)s'
            % env)

def git_reset():
    with cd(env.project_dir):
        if exists('.git'):
            run('git fetch')
        else:
            run('git clone %(repo_url)s .' % env)

        current_commit = local('git log -n 1 --format=%H', capture=True)
        run('git reset --hard ' + current_commit)

def pip_install():
    with prefix(env.workon):
        run('pip install -r requirements.txt')

def local_settings():
    with cd('%(project_dir)s/%(project_pkg)s/settings' % env):
        settings_path = 'local.py'
        if exists(settings_path):
            return

        append(settings_path, 'from .common import *')
        append(settings_path, 'ALLOWED_HOSTS = ["%(app_url)s"]' % env)
        append(settings_path, 'STATIC_ROOT = "%(static_dir)s"' % env)

        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        key = ''.join(random.SystemRandom().choice(chars) for _ in range(50))
        append(settings_path, "SECRET_KEY = '%s'" % (key,))

def collectstatic():
    with prefix(env.workon):
        run('./manage.py collectstatic --noinput')

def syncdb():
    with prefix(env.workon):
        run('./manage.py syncdb --noinput')

@task
def start():
    with prefix(env.workon):
        run('gunicorn -D -b 127.0.0.1:%(app_port)s -p %(pid_path)s %(wsgi_app)s'
            % env)

@task
def stop():
    with warn_only():
        run('kill $(cat %(pid_path)s)' % env)

    with quiet():
        run('rm %(pid_path)s' % env)

@task
def restart():
    try:
        run('kill -HUP $(cat %(pid_path)s)' % env)
    except:
        start()

