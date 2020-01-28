import click, requests

@click.group()
@click.option("--c2-url", "-u", default="http://127.0.0.1:5000",
    help="URL of the Command and Control server.")
def main(c2_url):
    global C2_URL
    C2_URL = c2_url

@main.command("lsavailable")
def lsavialable():
    """Lists the test sets available at the C&C server."""
    try:
        resp = requests.get(C2_URL + "/test_sets")
    except requests.exceptions.ConnectionError as e:
        print("Connection refused.")
    else:
        print(resp.json())

@main.command("lsenv")
def lsenv():
    """Lists the environments currently registered at the C&C server."""
    try:
        resp = requests.get(C2_URL + "/environments")
    except requests.exceptions.ConnectionError as e:
        print("Connection refused.")
    else:
        print(resp.json())

@main.command("lsinstalled")
@click.argument("ip")
@click.argument("port")
def lsinstalled(ip, port):
    """
    Lists the currently instaled tests sets
    in the environment at IP:PORT.
    """
    url = C2_URL + "/environments/{}/{}/installed".format(ip, port)
    try:
        resp = requests.get(url)
    except requests.exceptions.ConnectionError as e:
        print("Connection refused.")
    else:
        print(resp.json())

@main.command("install")
@click.argument("ip")
@click.argument("port")
@click.argument("packages", nargs=-1)
def install(ip, port, packages):
    """Install the given PACKAGES in the environment at IP:PORT."""
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