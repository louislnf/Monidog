# Monidog

Monidog is a console application to monitor websites availability and response times.

## Launching the application

### With Docker

#### Build

To build the docker image, use the following command :
```
make build
```

#### Run

Once you have built the docker image, you should be able to run it with the following command :

```
make run
```

### Without Docker

If you don't have Docker installed, you can run the program the old way.

First, make sure you have the required python modules. Run the following command to check :
```
pip install -r /requirements.txt
```

Then, to launch the application:
```
python src/Monidog.py
```
## Using the application

> _Warning :_ The minimum dimensions for the application to display correctly are 130 cols x 22 lines

### Add a website to monitor

To add a website to monitor press ```a``` and type the url of the website you want to monitor.
For example :

> https://github.com 

Then, simply press enter and you website will be added at the bottom of the list.

### Remove a website monitor

To remove a website, first make sure you are not editing the url input (press the ESC key). Select the website you want to remove in the list and press ```x```.

### Change stats view

- ```F1``` : display stats for the last 2min
- ```F2``` : display stats for the last hour 