import os
import random

from fabric.contrib.files import append, exists
from fabric.api import env, local, run, cd, task, prefix, warn_only, quiet

env.repo_url = 'https://github.com/bhrutledge/superlists.git'
env.project_pkg = 'superlists'
env.project_apps = ['lists']

def _get_secret_key():
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return ''.join(random.SystemRandom().choice(chars) for _ in range(50))

@task
def staging():
    env.hosts = ['debugged.org']
    env.user = 'rutt'
    env.app_name = 'superlists_staging'
    env.app_port = '27916'
    env.app_url = 'superlists-staging.bhrutledge.com'
    env.python = '/usr/local/bin/python3.3'
    env.settings = 'superlists.settings.local'
    env.key = _get_secret_key()

    init_env()

def init_env():
    env.user_dir = '/home/%(user)s' % env
    env.venv_dir = '%(user_dir)s/.virtualenvs/%(app_name)s' % env
    env.project_dir = '%(user_dir)s/webapps/%(app_name)s' % env
    env.static_dir = '%(user_dir)s/webapps/%(app_name)s_static' % env
    env.workon = 'workon %(app_name)s' % env
    env.wsgi_app = '%(project_pkg)s.wsgi:application' % env
    env.gunicorn_dir = '%(project_dir)s/.gunicorn' % env
    env.pid_path = '%(gunicorn_dir)s/pid' % env
    env.log_path = '%(gunicorn_dir)s/log' % env

@task
def deploy():
    # Assume project and static apps are set up
    # Assume virtualenvwrapper works on login

    # TODO: Create WebFaction app
    mkvirtualenv()
    git_reset()
    pip_install()
    local_settings()
    collectstatic()
    syncdb()
    restart()

@task
def clean():
    rmvirtualenv()
    clean_dirs()

def mkvirtualenv():
    postactivate_path = os.path.join(env.venv_dir, 'bin', 'postactivate')
    if not exists(postactivate_path):
        run('mkvirtualenv -p %(python)s -a %(project_dir)s %(app_name)s'
            % env)

        append(postactivate_path,
               'export DJANGO_SETTINGS_MODULE=%(settings)s' % env)
        append(postactivate_path, "export SECRET_KEY='%(key)s'" % env)

def rmvirtualenv():
    run('rmvirtualenv %(app_name)s' % env)

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
    # TODO: Add production settings to git
    with cd('%(project_dir)s/%(project_pkg)s/settings' % env):
        settings_path = 'local.py'
        if exists(settings_path):
            return

        append(settings_path, 'from .base import *')
        append(settings_path, 'ALLOWED_HOSTS = ["%(app_url)s"]' % env)
        append(settings_path, 'STATIC_ROOT = "%(static_dir)s"' % env)

def collectstatic():
    with prefix(env.workon):
        run('./manage.py collectstatic --noinput')

def syncdb():
    with prefix(env.workon):
        run('./manage.py syncdb --noinput')

def clean_dirs():
    run('find %(project_dir)s -mindepth 1 -delete' % env)
    run('find %(static_dir)s -mindepth 1 -delete' % env)

@task
def start():
    run('mkdir -p %(gunicorn_dir)s' % env)
    with prefix(env.workon):
        run('gunicorn --daemon '
            '--bind 127.0.0.1:%(app_port)s '
            '--log-file %(log_path)s '
            '--pid %(pid_path)s '
            '%(wsgi_app)s'
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

@task
def unittest():
    with prefix(env.workon):
        run('./manage.py test ' + ' '.join(env.project_apps))

@task
def functest():
    local('./manage.py test %(project_pkg)s --liveserver=%(app_url)s' % env)

