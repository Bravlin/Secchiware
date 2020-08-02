# Secchiware

## About

Secchiware is a free (libre) transparency tester for malware dynamic analysis environments. Its main goal is to aid system administrators and computer security investigators in the process of building better environments resilient to be discovered by malware.

### Features

* A "nanoframework" is provided to ease the development of new tests, understanding that the ever-changing nature of malware requires a flexible tool.
* Management of multiple environments through a central server.
* Uploading and execution of selected tests in the user's environments.
* Persistance of the results of the executed tests and of the information about the connected environments.
* A simple CLI client to start using the tool right away.
* A GUI client which can be found [here](https://github.com/Bravlin/secchiware-desktop-client).

### Repository contents

* node: The component to be executed in each desired environment. When it starts, it tries to connect to the configured central server. If that is done successfully, a local server is initiated by which the node is allowed to be managed; if that is not the case, all already installed tests in the environment are executed and returned through the standard output.
* c2: The central server, better known as the command and control server (benevolent intentions only!). Through it a client can manage all active nodes, do CRUD operations on the tests repository held by the server and check the histories of nodes' sessions and tests results.
* c2cli: A command line interface client to interact with the software.
* common: Libraries used by the previous components.
* test_sets_dev: Modules containing a variety of exemplary tests.
* api_documentation: The APIs for the c2 and node servers described using the OpenAPI specification. Anyone interested in learn more about or implementing their own node, c2 or client should check it out.

## Installation

The node, c2 and cli components all need libraries from the common package. To install it, execute the following command from the repository's root directory:

```
pip install -e common
```

### Node installation

Just execute the next command to install the required dependencies:

```
pip install -r node/requirements.txt
```

After that, execute:

```
cp node/config_example.json node/config.json
```

Once that is done, edit the configuration file with your desired parameters and start the program with:

```
python node/node.py
```

### C2 installation

First install its dependencies with:

```
pip install -r c2/requirements.txt
```

After that, create the instance folder with:

```
mkdir c2/instance
```

To create the database and the configuration file execute:

```
cd c2
```

```
FLASK_APP=secchiware_c2 flask init-database
```

```
cp config_example.json instance/config.json
```

Modify the configuration file with your specific parameters. The command and control server depends on Redis as a caché and concurrency control medium, so be sure to provide a valid instance's parameters.

If you are in Linux, you can start the system right away using Flask's built-in server using the provided script "run_example.sh". In that file you can see that some setup and cleanup tasks are necessary before the server is turned on and after it gets shutdown. The program is intended to be deployed to any compatible WSGI server, just be sure to invoke those tasks in one way or another in your particular deployment environment.

### CLI installation

Install its dependencies with:

```
pip install -r c2cli/requirements.txt
```

You can then run commands like this:

```
python c2cli/c2cli.py <COMMAND> <ARGUMENTS>
```

## License

Secchiware is licensed under the GNU General Public License v3.0.

## Author

[Bravlin](https://github.com/Bravlin): Braulio Pablos
