# Item Catalog

An item catalog where it's possible to define categories and items. Categories and items can be created, updated and deleted once the users log in with their Google account.

## Requirements

In order to use the software it's necessary to clone in your local enviroment [this virtual machine](https://github.com/udacity/fullstack-nanodegree-vm).

You need installed [Virtualbox](https://www.virtualbox.org/) and [Vagrant](https://www.vagrantup.com/) which will allow to use the vagrant box above.

## How-to

Once you have everything set up you just need to clone this repository in a shared folder of the vagrant box previously described.
After you access your virtual machine through `vagrant ssh`, it's necessary to install Flask-WTF: `sudo pip install flask-wtf` 

In order to create the database structure is important to run `python database_setup.py`. The previous command is not mandatory by running `python application.py` the application should create the database structure as well and it will possible to use the web application from this URL [http://localhost:5000](http://localhost:5000)