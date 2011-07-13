========
Batucada
========

Batucada is a ground up rewrite of drumbeat.org in `Django`_. 

.. _Django: http://www.djangoproject.com/

Installation
------------

To install Batucada, you must clone the repository: ::

   git clone git://github.com/paulosman/batucada.git

If you're planning on contributing back to the project, `fork the repository`_ instead in the usual GitHub fashion.

.. _fork the repository: http://help.github.com/forking/

Next, you'll need to install ``virtualenv`` and ``pip`` if you don't already have them: ::

   sudo easy_install virtualenv
   sudo easy_install pip
   
Using ``virtualenvwrapper`` is also recommended (see the `installation instructions`_). Be sure to configure your shell so that pip knows where to find your virtual environments: ::

   # in .bashrc or .bash_profile
   export WORKON_HOME=$HOME/.virtualenvs
   export PIP_VIRTUALENV_BASE=$WORKON_HOME
   export PIP_RESPECT_VIRTUALENV=true
   source /usr/bin/virtualenvwrapper.sh

.. _installation instructions: http://www.doughellmann.com/docs/virtualenvwrapper/

virtualenvwrapper is sometimes installed to /usr/local/bin/ so if you set things up and are informed of missing file errors change the location accordingly.

Now create a virtual environment for ``batucada`` and install its dependencies: ::

   cd batucada
   mkvirtualenv --no-site-packages batucada
   workon batucada
   pip install -r requirements/compiled.txt
   pip install -r requirements/dev.txt

There's a chance that packages listed in ``requirements/compiled.txt`` won't install cleanly if your system is missing some key development libraries. For example, lxml requires ``libxsml2-dev`` and ``libxslt-dev``. These should be available from your system's package manager.

Problems have also been experienced with using Xcode4. If you're pip installs fail try giving things a kick by running the following and try it again: ::

    ARCHFLAGS="-arch i386 -arch x86_64"
   
To be extra sure you're working from a clean slate, you might find it helps to delete ``.pyc`` files: ::

    find . -name "*.pyc" | xargs rm

Create a ``settings_local.py`` based on the template provided in the checkout. Edit the database parameters as needed ::

   cp settings_local.dist.py settings_local.py

If you have yet to get a local version of mysql running you will want to do so now. 

In order to run the migrations and syncd command you need to have an empty database set up. Default name is 'batucada', if you didn't change anything in local_settings.py then you can simply run, from an mysql command line: ::

    CREATE DATABASE 'batucada';

Now sync the database and run migrations. ::

   python manage.py syncdb --noinput 

There's a problem with real databases (read: not sqlite) where south migrations are run in an order that violates foreign key constraints. See `Bug # 623612`_ for details. Until that is fixed, you're best off running migrations in this order. ::

   python manage.py migrate projects
   python manage.py migrate users
   python manage.py migrate activity
   python manage.py migrate statuses
   python manage.py migrate links
   python manage.py migrate dashboard
   python manage.py migrate relationships
   python manage.py migrate feeds
   python manage.py migrate challenges

What a pain! 

.. _Bug # 623612: https://bugzilla.mozilla.org/show_bug.cgi?id=623612

Finally, start the development server to take it for a spin. ::

   python manage.py runserver 

Get Involved
------------

To help out with batucada, join the `Drumbeat mailing list`_ and introduce yourself. We're currently looking for help from Django / Python and front-end (HTML, CSS, Javascript) developers. 

.. _Drumbeat mailing list: http://www.mozilla.org/about/forums/#drumbeat-website
