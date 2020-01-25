import click, requests

@click.group()
@click.option("--c2-ip", "-i", default="127.0.0.1",
    help="IP of the Command and Control server.")
@click.option("--c2-port", "-p", default=5000,
    help="Port of the Command and Control server.")
def main(c2_ip, c2_port):
    global C2_IP, C2_PORT, C2_URL
    C2_IP = c2_ip
    C2_PORT = c2_port
    C2_URL = "http://" + C2_IP + ":" + str(C2_PORT)

@main.command()
def lsavialable():
    try:
        resp = requests.get(C2_URL + "/test_sets")
    except requests.exceptions.ConnectionError as e:
        print("Connection refused.")
    else:
        print(resp.json())

@main.command()
def lsenv():
    try:
        resp = requests.get(C2_URL + "/environments")
    except requests.exceptions.ConnectionError as e:
        print("Connection refused.")
    else:
        print(resp.json())

@main.command()
@click.argument("ip")
@click.argument("port")
def lsinstalled(ip, port):
    url = C2_URL + "/environments/{}/{}/installed".format(ip, port)
    try:
        resp = requests.get(url)
    except requests.exceptions.ConnectionError as e:
        print("Connection refused.")
    else:
        print(resp.json())

@main.command()
@click.argument("ip")
@click.argument("port")
@click.argument("packages", nargs=-1)
def install(ip, port, packages):
    url = C2_URL + "/environments/{}/{}/installed".format(ip, port)
    try:
        resp = requests.post(url, json={'packages': packages})
    except requests.exceptions.ConnectionError as e:
        print("Connection refused.")
    else:
        if not resp.json()['success']:
            print("Operation failed.")


if __name__ == "__main__":
    main()