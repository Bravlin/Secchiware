import click, os, requests

def print_package(pack: dict, level: int, ident: str):
    base_ident = ident * level
    print(f"{base_ident}{pack['name']}")
    if pack['modules']:
        print(f"{base_ident}{ident}Modules:")
        for mod in pack['modules']:
            print(f"{base_ident}{ident * 2}{mod['name']}")
            if mod['test_sets']:
                print(f"{base_ident}{ident * 3}Test sets:")
                for ts in mod['test_sets']:
                    print(f"{base_ident}{ident * 4}{ts['name']}")
                if ts['tests']:
                    print(f"{base_ident}{ident * 5}Tests:")
                    for test in ts['tests']:
                        print(f"{base_ident}{ident * 6}{test}")
    if pack['subpackages']:
        print(base_ident + ident + "Subpackages:")
        for sub in pack['subpackages']:
            print_package(sub, level + 2, ident)

def print_test_report(report: dict, ident: str):
    print(f"Test: {report['test_name']}")
    print(f"Description: {report['test_description']}")
    print(f"Result code: {report['result_code']}")
    if 'additional_info' in report:   
        print("Additional information:")
        for key, value in report['additional_info'].items():
            print(f"{ident}{key}: {value}")

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
        resp = requests.get(f"{C2_URL}/test_sets")
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        for pack in resp.json():
            print_package(pack, 0, " " * 2)
            print()

@main.command("upload")
@click.argument("file_path")
def upload_compressed_packages(file_path: str):
    if not os.path.isfile(file_path):
        print("Given path does not exists or is not a file.")
    elif not file_path.endswith(".tar.gz"):
        print("Only .tar.gz extension allowed.")
    else:
        try:
            with open(file_path, "rb") as f:
                resp = requests.post(
                    f"{C2_URL}/test_sets",
                    files={'packages': f})
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            print("Connection refused.")
        except Exception as e:
            print(str(e))

@main.command("lsenv")
def lsenv():
    """Lists the environments currently registered at the C&C server."""
    try:
        resp = requests.get(f"{C2_URL}/environments")
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        envs = resp.json()
        for ip in envs:
            for port in envs[ip]:
                print(ip + ":" + port)

@main.command("lsinstalled")
@click.argument("ip")
@click.argument("port")
def lsinstalled(ip, port):
    """
    Lists the currently instaled tests sets
    in the environment at IP:PORT.
    """
    url = f"{C2_URL}/environments/{ip}/{port}/installed"
    try:
        resp = requests.get(url)
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        for pack in resp.json():
            print_package(pack, 0, " " * 2)
            print()

@main.command("install")
@click.argument("ip")
@click.argument("port")
@click.argument("packages", nargs=-1)
def install(ip, port, packages):
    """Install the given PACKAGES in the environment at IP:PORT."""
    url = f"{C2_URL}/environments/{ip}/{port}/installed"
    try:
        resp = requests.post(url, json={'packages': packages})
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        if not resp.json()['success']:
            print("Operation failed.")

@main.command("execute_all")
@click.argument("ip")
@click.argument("port")
def execute_all_in_env(ip, port):
    """Execute all tests at the environment at IP:PORT."""
    url = f"{C2_URL}/environments/{ip}/{port}/report"
    try:
        resp = requests.get(url)
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        for report in resp.json():
            print_test_report(report, " " * 2)
            print()


if __name__ == "__main__":
    main()