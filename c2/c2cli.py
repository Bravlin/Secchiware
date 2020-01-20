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
def lsenv():
    try:
        resp = requests.get(C2_URL + "/environments")
        print(resp.json())
    except requests.exceptions.ConnectionError as e:
        print("Connection refused.")

@main.command()
@click.argument("ip")
@click.argument("port")
def lsinstalled(ip, port):
    try:
        url = C2_URL + "/environments/{}/{}/installed"
        resp = requests.get(url.format(ip, port))
        print(resp.json())
    except requests.exceptions.ConnectionError as e:
        print("Connection refused.")

if __name__ == "__main__":
    main()