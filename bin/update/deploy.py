"""
Deploy this project in dev/stage/production.

Requires commander_ which is installed on the systems that need it.

.. _commander: https://github.com/oremj/commander

"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from commander.deploy import task, hostgroups
import commander_settings as settings


@task
def update_code(ctx, tag):
    """Update the code to a specific git reference (tag/sha/etc)."""
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('git fetch')
        ctx.local('git checkout -f %s' % tag)
        ctx.local('git submodule sync')
        ctx.local('git submodule update --init --recursive')


@task
def update_info(ctx):
    """Write info about the current state to a publicly visible file."""
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('date')
        ctx.local('git branch')
        ctx.local('git log -3')
        ctx.local('git status')
        ctx.local('git submodule status')
        with ctx.lcd('locale'):
            ctx.local('svn info')
            ctx.local('svn status')

        ctx.local('git rev-parse HEAD > static/revision')


@task
def clean(ctx):
    """Clean .gitignore and .pyc files."""
    with ctx.lcd(settings.SRC_DIR):
        ctx.local("find . -type f -name '.gitignore' -or -name '*.pyc' -delete")


@task
def update_assets(ctx):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('python2.6 manage.py collectstatic --noinput')
        # LANG=en_US.UTF-8 is sometimes necessary for the YUICompressor.
        ctx.local('LANG=en_US.UTF8 python2.6 manage.py compress_assets')

    # Compile nunjucks templates (assumes nunjucks is installed).
    with ctx.lcd(os.path.join(settings.SRC_DIR, 'static', 'templates')):
        ctx.local('nunjucks-precompile . > compiled.js')


@task
def update_db(ctx):
    """
    Update the database schema, if necessary.

    Uses schematic by default. Change to south if you need to.
    """
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('python2.6 manage.py syncdb --noinput')
        ctx.local('python2.6 manage.py migrate --noinput')
        ctx.local('python2.6 manage.py migrate --list')


@task
def update_locales(ctx):
    """
    Update a locale directory from SVN.

    Assumes localizations 1) exist, 2) are in SVN, 3) are in SRC_DIR/locale and
    4) have a compile-mo.sh script. This should all be pretty standard, but
    change it if you need to.
    """
    with ctx.lcd(os.path.join(settings.SRC_DIR, 'locale')):
        ctx.local('svn up')
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('./bin/compile-mo.sh locale/')


@task
def update_product_details(ctx):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('python2.6 manage.py update_product_details')


@task
def checkin_changes(ctx):
    """Use the local, IT-written deploy script to check in changes."""
    ctx.local(settings.DEPLOY_SCRIPT)


@hostgroups(settings.WEB_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def deploy_app(ctx):
    """Call the remote update script to push changes to webheads."""
    ctx.remote('touch %s' % settings.REMOTE_WSGI)


@hostgroups(settings.CELERY_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def update_celery(ctx):
    """Update and restart Celery."""
    ctx.remote(settings.REMOTE_UPDATE_SCRIPT)
    ctx.remote('supervisorctl restart %s' % settings.CELERY_SERVICE)


@task
def pre_update(ctx, ref=settings.UPDATE_REF):
    """Update code to pick up changes to this file."""
    update_code(ref)
    update_info()
    clean()


@task
def update(ctx):
    update_assets()
    #update_locales()
    update_db()
    update_product_details()


@task
def deploy(ctx):
    checkin_changes()
    deploy_app()
    #update_celery()


@task
def update_site(ctx, tag):
    """Update the app to prep for deployment."""
    pre_update(tag)
    update()
