# Monidog

Monidog is a console application to monitor websites availability and response times.

## Launching the application

### With Docker

#### Build

To build the docker image, use the following command :
```
docker build -t monidog .
```

#### Run

Once you have built the docker image, you should be able to run it with the following command :

```
docker run -ti monidog
```

The ```-ti``` option is necessary to display in the terminal window.

### Without Docker

If you don't have Docker installed, you can run the program the old way.

First, make sure you have the ```requests``` module. Run the following command to check :
```
pip install requests
```

Then, to launch the application:
```
python3 Monidog.py
```
