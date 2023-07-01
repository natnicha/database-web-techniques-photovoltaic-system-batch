# Photovoltaic System Batch

## Prerequisite - Need to know
There are 4 services in this system including
1. Photovoltaic System Services
2. Photovoltaic System App
3. Photovoltaic System Cron
4. Photovoltaic System Batch

Work flows look like this
1. `App` call to `Services` 
2. `Services` call to `Batch`
3. `Cron` call to `Services`

You should setup/run the services in this sequence:
1. `Batch`
2. `Services`
3. `Cron` - no dependencies can setup either `App` or `Cron` first
3. `App` - no dependencies can setup either `App` or `Cron` first

## Installing the project on your machine
1 - install pipenv using pip

~~~
pip install --user pipenv
~~~

2 - create pipenv environment and install dependencies by this command

~~~
pipenv install 
~~~

or using this command
~~~
python3 -m pipenv install
~~~

## Setting up the database destination
1 - Set a database destination in a .env file 

Don't forget to find the pipenv environment for Photovoltaic System Services

| Please note that this service is no need to run. It will be trigged by Photovoltaic System Services. That means this project and Photovoltaic System Services have to place on the same environment.|
| --- |
