import hmac
import json
import os
import redis
import requests as rq
import signatures
import shutil
import signal
import sqlite3
import sys
import tempfile
import test_utils
import time

from base64 import b64encode
from flask import abort, Flask, g, jsonify, request, Response
from flask_cors import CORS
from hashlib import sha256
from typing import Callable, Dict, Optional, Tuple


################################ Globals #####################################

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
TESTS_PATH = os.path.join(SCRIPT_PATH, "test_sets")
DATABASE_PATH = os.path.join(SCRIPT_PATH, "secchiware.db")

with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as config_file:
    config = json.load(config_file)
config['NODE_SECRET'] = config['NODE_SECRET'].encode()
config['CLIENT_SECRET'] = config['CLIENT_SECRET'].encode()


########################### Key recoverer functions ##########################

def client_key_recoverer(key_id: str) -> Optional[bytes]:
    """The key recoverer for client oriented endpoints. Only the ID 'Client'
    is allowed.
    
    Parameters
    ----------
    key_id: str
        The ID to look for.

    Returns
    -------
    bytes, optional
        The key corresponding to the given ID or None if there was no match.
    """

    return config['CLIENT_SECRET'] if key_id == "Client" else None

def node_key_recoverer(key_id: str) -> Optional[bytes]:
    """The key recoverer for node oriented endpoints. Only the ID 'Node' is
    allowed.
    
    Parameters
    ----------
    key_id: str
        The ID to look for.

    Returns
    -------
    bytes, optional
        The key corresponding to the given ID or None if there was no match.
    """

    return config['NODE_SECRET'] if key_id == "Node" else None


######################## Database related functions ##########################

def get_database() -> sqlite3.Connection:
    """Gets a database connection.

    It starts one if it was not already created.

    Returns
    -------
    sqlite3.Connection
        The open database connection.
    """

    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE_PATH)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

def init_database() -> None:
    """Creates in the database the schemas needed for the application, if they
    don't exist."""

    db = get_database()
    with open(os.path.join(SCRIPT_PATH, "schema.sql")) as f:
        db.executescript(f.read())
    db.commit()

def api_parametrized_search(
        db: sqlite3.Connection,
        table: str,
        order_by_api_to_db: Dict[str, str],
        where_api_to_db: Dict[str, Tuple[str, str]],
        parameters: dict,
        select_columns: tuple = None) -> sqlite3.Cursor:
    """Converts the recieved parameters into a SQL SELECT statement, executes
    it and returns the corresponding cursor.

    Parameters
    ----------
    db: sqlite3.Connection
        The connection to the database to query to.
    table: str
        The database table to look into.
    order_by_api_to_db: Dict[str, str]
        A dictionary where each key is one of the accepted parameters to sort
        by of the external API and its value is the corresponding column name.
    where_api_to_db: Dict[str, Tuple[str, str]]
        A dictionary where each key is one of the accepted parameters to
        filter by of the external API and its values is a tuple where the
        first member is the corresponding column name and the second one is
        the associated operator.
    parameters: dict
        A dictionary where each key-value pair is the name of an argument
        recieved by the external API and its corresponding value.
    select_columns: tuple
        The columns that the developer wants to return with the generated
        query.

    Exceptions
    ----------
    ValueError
        There is content present in the "parameters" argument that is not
        valid.

    Returns
    -------
    sqlite3.Cursor
        A cursor to the formulated query.
    """

    if not select_columns:
        query = f"SELECT * FROM {table}"
    else:
        query = f"SELECT {', '.join(select_columns)} FROM {table}"

    param_keys = {*parameters.keys()}
    if not 'order_by' in param_keys:
        if 'arrange' in param_keys:
            raise ValueError("arrange key present when no order is specified")
        order_by_clause = ""
    else:
        if not parameters['order_by'] in order_by_api_to_db:
            raise ValueError("Invalid order key")
        order_by_clause = (
            f"ORDER BY {order_by_api_to_db[parameters['order_by']]}")
        param_keys.remove('order_by')

        if 'arrange' in param_keys:
            if parameters['arrange'] not in {'asc', 'desc'}:
                raise ValueError("Invalid arrange value")
            order_by_clause = f"{order_by_clause} {parameters['arrange']}"
            param_keys.remove('arrange')
    
    if not 'limit' in param_keys:
        limit_clause = ""
    else:
        if int(parameters['limit']) <= 0:
            raise ValueError("Invalid limit value")
        limit_clause = f"LIMIT {parameters['limit']}"
        param_keys.remove('limit')

    where_clause = ""
    placeholders_values = {}
    for key in param_keys:
        if key not in where_api_to_db:
            raise ValueError("Invalid query parameter found")
        where_filter = ""
        column = where_api_to_db[key][0]
        operator = where_api_to_db[key][1]
        i = 0
        for value in parameters[key].split(","):
            placeholder_key = f"{key}{i}"
            placeholders_values[placeholder_key] = value
            where_filter = (
                f"{where_filter} OR {column}{operator}:{placeholder_key}")
            i += 1

        where_filter = where_filter.replace(" OR ", "", 1)
        where_clause = f"{where_clause} AND ({where_filter})"
    where_clause = where_clause.replace(" AND", "WHERE", 1)

    query = f"{query} {where_clause} {order_by_clause} {limit_clause}"
    return db.execute(query, placeholders_values)


################### Memory storage related function ##########################

def get_memory_storage() -> redis.StrictRedis:
    memory_storage = getattr(g, '_memory_storage', None)
    if memory_storage is None:
        memory_storage = redis.StrictRedis(
            decode_responses=True,
            charset="utf-8")
        g._memory_storage = memory_storage
    return memory_storage

def init_memory_storage() -> None:
    memory_storage = get_memory_storage()
    memory_storage.flushdb()
    pipe = memory_storage.pipeline()
    for p in test_utils.get_installed_test_sets("test_sets"):
        pipe.set(f"repository:{p['name']}", json.dumps(p))
        pipe.zadd("repository_index", {p['name']: 0})
    pipe.execute()

def clear_environment_cache(environment_key) -> None:
    memory_storage = get_memory_storage()
    pipe = memory_storage.pipeline()
    pipe.delete(environment_key)
    pipe.delete(f"{environment_key}:installed_index")
    pipe.execute()


######################## Request check functions #############################

def check_registered(ip: str, port: int) -> None:
    """Verifies if the given ip and port correspond to an active environment.

    Parameters
    ----------
    ip: str
        The ip to look for.
    port: int
        The port associated to the given ip to look for.

    Abort
    -----
    404
        There is no environment registered with the given ip and port.
    """

    db = get_database()
    cursor = db.execute(
        """SELECT id_session
        FROM session
        WHERE env_ip = ? AND env_port = ? AND session_end IS NULL""",
        (ip, port))
    if cursor.fetchone() is None:
        abort(404,
            description=f"No environment registered at {ip}:{port}")

def check_is_json() -> None:
    """Verifies that the current request's MIME type is 'application/json'.

    Abort
    -----
    415
        The MIME type of the request is not vlid.
    """

    if not request.is_json:
        abort(415, description="Content Type is not application/json")

def check_digest_header() -> None:
    """Verifies that the current request has a "Digest" header and that the
    provided digest corresponds to the request's body.

    Abort
    -----
    400
        The "Digest" header is missing, the algorithm used to calculate the
        digest is not SHA-256 or it does not match the request's body.
    """

    if not 'Digest' in request.headers:
        abort(400, description="'Digest' header mandatory.")
    if not request.headers['Digest'].startswith("sha-256="):
        abort(400, description="Digest algorithm should be sha-256.")
    digest = b64encode(sha256(request.get_data()).digest()).decode()
    if digest != request.headers['Digest'].split("=", 1)[1]:
        abort(400, description="Given digest does not match content.")

def check_authorization_header(
        key_recoverer: Callable[[str], Optional[bytes]],
        *mandatory_headers) -> None:
    """Verifies that the incoming request fulfills the SECCHIWARE-HMAC-256.
    authorization scheme.
    
    The "Authorization" header must be present in the request, it must have
    the proper format and the informed signature must correspond to the
    request's content.

    Parameters
    ----------
    key_recoverer: Callable[[str], Optional[bytes]]
        A function that returns the corresponding key given an ID or None if
        there is no match.
    mandatory_headers: *Tuple[str], optional
        A variable amount of header keys that must be present in the incoming
        request.

    Abort
    -----
    401
        The request does not fulfill the described criteria.
    """

    if not 'Authorization' in request.headers:
        abort(401, description="No 'Authorization' header found in request.")
    try:
        is_valid = signatures.verify_authorization_header(
            request.headers['Authorization'],
            key_recoverer,
            lambda h: request.headers.get(h),
            request.method,
            request.path,
            request.query_string.decode(),
            mandatory_headers)
    except ValueError as e:
        abort(401, description=str(e))
    except Exception as e:
        abort(401, description="Invalid 'Authorization' header.")
    if not is_valid:
        abort(401, description="Invalid signature.")


######################## Flask app initialization ############################

app = Flask(__name__)
CORS(
    app,
    resources={
        r"/environments": {'methods': "GET"},
        r"/environments/([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]+/+": {},
        r"/executions/*": {},
        r"/sessions/*": {},
        r"/subscribe": {},
        r"/test_sets/*": {}
    })

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


############################# Error handlers #################################

@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400

@app.errorhandler(401)
def unauthorized(e):
    res = jsonify(error=str(e))
    res.status_code = 401
    res.headers['WWW-Authenticate'] = (
        'SECCHIWARE-HMAC-256 realm="Access to C2"')
    return res

@app.errorhandler(404)
def not_found(e):
    return jsonify(error=str(e)), 404

@app.errorhandler(415)
def unsupported_media_type(e):
    return jsonify(error=str(e)), 415

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify(error=str(e)), 500

@app.errorhandler(502)
def bad_gateway(e):
    return jsonify(error=str(e)), 502

@app.errorhandler(504)
def gateway_timeout(e):
    return jsonify(error=str(e)), 504


############################### Endpoints ####################################

@app.route("/environments", methods=["GET"])
def list_environments():
    db = get_database()
    cursor = db.execute(
        """SELECT id_session, session_start, env_ip, env_port
        FROM session
        WHERE session_end IS NULL""")
    
    environments = []
    env = cursor.fetchone()
    while env:
        environments.append({
            'session_id': env['id_session'],
            'ip': env['env_ip'],
            'port': env['env_port'],
            'session_start': env['session_start']
        })
        env = cursor.fetchone()

    return jsonify(environments)

@app.route("/environments", methods=["POST"])
def add_environment():
    check_digest_header()
    check_authorization_header(node_key_recoverer, "Digest")
    check_is_json()
    if not ('ip' in request.json
            and 'port' in request.json
            and 'platform_info' in request.json):
        abort(400, description="One or more keys missing in request's body")

    ip = request.json['ip']
    port = request.json['port']
    platform_info = request.json['platform_info']

    db = get_database()

    # Checks if there is an active session associated to the incoming ip and
    # port already.
    cursor = db.execute(
        """SELECT id_session
        FROM session
        WHERE env_ip = ? AND env_port = ? AND session_end IS NULL""",
        (ip, port))
    previous_session = cursor.fetchone()
    if previous_session:
        # If there is such session, it is assumed that its corresponding
        # environment was not shut down properly.
        cursor.execute(
            """UPDATE session
            SET session_end = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            WHERE id_session = ?""",
            (previous_session['id_session'],))

        clear_environment_cache(f"environments:{ip}:{port}")

    memory_storage = get_memory_storage()

    # Marks installed tests cache as not initialized.
    memory_storage.hset(
        f"environments:{ip}:{port}",
        "installed_cached",
        "0")

    to_insert = (
        ip,
        port,
        platform_info['platform'],
        platform_info['node'],
        platform_info['os']['system'],
        platform_info['os']['release'],
        platform_info['os']['version'],
        platform_info['hardware']['machine'],
        platform_info['hardware']['processor'],
        platform_info['python']['build'][0],
        platform_info['python']['build'][1],
        platform_info['python']['compiler'],
        platform_info['python']['implementation'],
        platform_info['python']['version']
    )
    cursor.execute(
        """INSERT INTO session
        (
            env_ip, env_port, env_platform, env_node, env_os_system,
            env_os_release, env_os_version, env_hw_machine,
            env_hw_processor, env_py_build_no, env_py_build_date,
            env_py_compiler, env_py_implementation, env_py_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        to_insert)
    db.commit()

    # Notifies about the now connected environment.
    cursor = db.execute(
        """SELECT id_session, session_start, env_ip, env_port
        FROM session
        WHERE id_session = ?""",
        (cursor.lastrowid,))
    last_inserted = cursor.fetchone()
    message = json.dumps({
        'event': 'start',
        'content': {
            'session_id': last_inserted['id_session'],
            'session_start': last_inserted['session_start'],
            'ip': last_inserted['env_ip'],
            'port': last_inserted['env_port']
        }
    })
    memory_storage.publish("environments", message)

    return Response(status=204, mimetype="application/json")

@app.route("/environments/<ip>/<int:port>", methods=["DELETE"])
def remove_environment(ip, port):
    check_authorization_header(node_key_recoverer)

    db = get_database()
    cursor = db.execute(
        """UPDATE session
        SET session_end = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        WHERE env_ip = ? AND env_port = ? AND session_end IS NULL""",
        (ip, port))

    if cursor.rowcount == 0:
        abort(404,
            description=f"No environment registered at {ip}:{port}")

    db.commit()

    clear_environment_cache(f"environments:{ip}:{port}")

    message = json.dumps({
        'event': 'stop',
        'content': {
            'ip': ip,
            'port': port
        }
    })
    get_memory_storage().publish("environments", message)

    return Response(status=204, mimetype="application/json")

@app.route("/environments/<ip>/<int:port>/info", methods=["GET"])
def get_environment_info(ip, port):
    db = get_database()
    row = db.execute(
        """SELECT env_platform, env_node, env_os_system, env_os_release,
        env_os_version, env_hw_machine, env_hw_processor, env_py_build_no,
        env_py_build_date, env_py_compiler, env_py_implementation,
        env_py_version
        FROM session
        WHERE env_ip = ? AND env_port = ? AND session_end IS NULL""",
        (ip, port)).fetchone()

    if row is None:
        abort(404,
            description=f"No environment registered at {ip}:{port}")

    info = {
        'platform': row['env_platform'],
        'node': row['env_node'],
        'os': {
            'system': row['env_os_system'],
            'release': row['env_os_release'],
            'version': row['env_os_version']
        },
        'hardware': {
            'machine': row['env_hw_machine'],
            'processor': row['env_hw_processor']
        },
        'python': {
            'build': (row['env_py_build_no'], row['env_py_build_date']),
            'compiler': row['env_py_compiler'],
            'implementation': row['env_py_implementation'],
            'version': row['env_py_version']
        }
    }

    return jsonify(info)
    
@app.route("/environments/<ip>/<int:port>/installed", methods=["GET"])
def list_installed_test_sets(ip, port):
    check_registered(ip, port)

    memory_storage = get_memory_storage()
    environment_key = f"environments:{ip}:{port}"

    installed_cached = memory_storage.hget(
        environment_key,
        "installed_cached")
    lock = memory_storage.lock(f"{environment_key}:installed:mutex", timeout=30)
    while installed_cached == "0" and not lock.acquire(blocking=False):
        time.sleep(0.5)

    if installed_cached == "1":
        packages_names = memory_storage.zrange(
            f"{environment_key}:installed_index",
            0,
            -1)
        installed_str = ",".join(memory_storage.hmget(
            environment_key,
            tuple(f"installed:{p}" for p in packages_names)))
    else:
        try:
            resp = rq.get(f"http://{ip}:{port}/test_sets")
        except rq.exceptions.ConnectionError:
            abort(504,
                description="The requested environment could not be reached")
        else:
            if resp.status_code != 200:
                abort(
                    502,
                    description=
                        f"Unexpected response from node at {ip}:{port}")

            installed_str = resp.text

            # Saves the node's response in the cache.
            pipe = memory_storage.pipeline()
            for p in json.loads(installed_str):
                pipe.hset(
                    environment_key,
                    f"installed:{p['name']}",
                    json.dumps(p))
                pipe.zadd(
                    f"{environment_key}:installed_index",
                    {p['name']: 0})
            pipe.hset(environment_key, "installed_cached", "1")
            pipe.execute()
        finally:
            lock.release()

    return Response(
        response=f"[{installed_str}]",
        status=200,
        mimetype="application/json")

@app.route("/environments/<ip>/<int:port>/installed", methods=["PATCH"])
def install_packages(ip, port):
    check_digest_header()
    check_authorization_header(client_key_recoverer, "Digest")
    check_registered(ip, port)
    check_is_json()

    packages = request.json

    with tempfile.SpooledTemporaryFile() as f:
        # Can throw ValueError.
        try:
            test_utils.compress_test_packages(f, packages, TESTS_PATH)
        except ValueError as e:
            abort(400, description=str(e))
        f.seek(0)
        prepared = rq.Request(
            "PATCH",
            f"http://{ip}:{port}/test_sets",
            files={'packages': f}).prepare()
    
    digest = b64encode(sha256(prepared.body).digest()).decode()
    prepared.headers['Digest'] = f"sha-256={digest}"

    headers = ['Digest']
    signature = signatures.new_signature(
        config['NODE_SECRET'],
        "PATCH",
        "/test_sets",
        signature_headers=headers,
        header_recoverer=lambda h: prepared.headers.get(h))
    prepared.headers['Authorization'] = (
        signatures.new_authorization_header("C2", signature, headers))

    memory_storage = get_memory_storage()
    environment_key = f"environments:{ip}:{port}"
    with memory_storage.lock(
            f"{environment_key}:installed:mutex",
            timeout=30,
            sleep=0.5):
        try:
            resp = rq.Session().send(prepared)        
        except rq.exceptions.ConnectionError:
            abort(
                504,
                description="The requested environment could not be reached")
        if resp.status_code == 204:
            installed_cached = memory_storage.hget(
                environment_key,
                "installed_cached")
            if installed_cached == "1":
                # Updates cache if it exists.
                pipe = memory_storage.pipeline()
                for pack in packages:
                    pipe.hset(
                        environment_key,
                        f"installed:{pack}",
                        memory_storage.get(f"repository:{pack}"))
                    pipe.zadd(f"{environment_key}:installed_index", {pack: 0})
                pipe.execute()

            return Response(status=204, mimetype="application/json")

        if resp.status_code in {400, 401, 415}:
            abort(
                500,
                description="Something went wrong when handling the request")

        abort(
            502,
            description=f"Unexpected response from node at {ip}:{port}")

@app.route(
    "/environments/<ip>/<int:port>/installed/<package>",
    methods=["DELETE"])
def delete_installed_package(ip, port, package):
    check_authorization_header(client_key_recoverer)
    check_registered(ip, port)

    signature = signatures.new_signature(
        config['NODE_SECRET'],
        "DELETE",
        f"/test_sets/{package}")
    authorization_content = signatures.new_authorization_header(
        "C2",
        signature)

    environment_key = f"environments:{ip}:{port}"
    memory_storage = get_memory_storage()
    with memory_storage.lock(
            f"{environment_key}:installed:mutex",
            timeout=30,
            sleep=0.5):
        try:
            resp = rq.delete(
                f"http://{ip}:{port}/test_sets/{package}",
                headers={'Authorization': authorization_content})
        except rq.exceptions.ConnectionError:
            abort(504,
                description="The requested environment could not be reached")

        if resp.status_code == 204:
            installed_cached = memory_storage.hget(
                environment_key,
                "installed_cached")
            if installed_cached == "1":
                # Updates cache if it exists.
                pipe = memory_storage.pipeline()
                pipe.hdel(environment_key, f"installed:{package}")
                pipe.zrem(f"{environment_key}:installed_index", package)
                pipe.execute()

            return Response(status=204, mimetype="application/json")

        if resp.status_code in {401, 404}:
            return abort(
                404,
                description=f"'{package}' not found at {ip}:{port}")

        abort(502, description=f"Unexpected response from node at {ip}:{port}")

@app.route("/environments/<ip>/<int:port>/reports", methods=["GET"])
def execute_tests(ip, port):
    db = get_database()
    cursor = db.execute(
        """SELECT id_session
        FROM session
        WHERE env_ip = ? AND env_port = ? AND session_end IS NULL""",
        (ip, port))
    row = cursor.fetchone()

    if row is None:
        abort(404,
            description=f"No environment registered at {ip}:{port}")
    
    url = f"http://{ip}:{port}/reports"
    if request.args:
        valid_keys = {'packages', 'modules', 'test_sets'}
        difference = set(request.args.keys()) - valid_keys
        if difference:
            abort(400, f"Invalid keys {difference} found in query parameters")
        else:
            url += f"?{request.query_string.decode()}"

    try:
        resp = rq.get(url)
    except rq.exceptions.ConnectionError:
        abort(504,
            description="The requested environment could not be reached")

    if resp.status_code == 400:
        abort(500,
            description="Something went wrong when handling the request")
    if resp.status_code == 404:
        abort(
            404,
            description="A specified entity does not exist in the node.")
    if resp.status_code != 200:
        abort(502, description=f"Unexpected response from node at {ip}:{port}")
    
    cursor.execute(
        "INSERT INTO execution (fk_session) VALUES (?)",
        (row['id_session'],))
    execution_id = cursor.lastrowid

    to_insert = []
    for report in resp.json():
        additional_info = report.get('additional_info')
        if additional_info:
            additional_info = json.dumps(additional_info)
        to_insert.append((
            execution_id,
            report['test_name'],
            report['test_description'],
            report['timestamp_start'],
            report['timestamp_end'],
            report['result_code'],
            additional_info))
    cursor.executemany(
        """INSERT INTO report (fk_execution, test_name, test_description,
        timestamp_start, timestamp_end, result_code, additional_info)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        to_insert)

    db.commit()
    return jsonify(resp.json())

@app.route("/events", methods=["GET"])
def subscribe():
    def event_stream():
        with app.app_context():
            sub = get_memory_storage().pubsub(ignore_subscribe_messages=True)
            sub.subscribe("environments")
            for message in sub.listen():
                yield f"data: {message['data']}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/executions", methods=["GET"])
def search_executions():
    db = get_database()

    if not request.args:
        cursor = db.execute("SELECT * FROM execution")
    else:
        try:
            cursor = api_parametrized_search(
                db=db,
                table="execution",
                order_by_api_to_db={
                    'id': "id_execution",
                    'session': "fk_session",
                    'registered': 'timestamp_registered',
                },
                where_api_to_db={
                    'ids': ("id_execution", "="),
                    'sessions': ("fk_session", "="),
                    'registered_from': ("timestamp_registered", ">="),
                    'registered_to': ("timestamp_registered", "<="),
                },
                parameters=request.args,
                select_columns=("*",))
        except ValueError as e:
            abort(400, str(e))
    
    results = []
    execution = cursor.fetchone()
    subcursor = db.cursor()
    while execution:
        reports = []
        subcursor.execute(
            """SELECT test_name, test_description, result_code,
            additional_info, timestamp_start, timestamp_end
            FROM report
            WHERE fk_execution = ?
            ORDER BY timestamp_start""",
            (execution['id_execution'],))
        report = subcursor.fetchone()
        while report:
            report_dict = {
                'test_name': report['test_name'],
                'test_description': report['test_description'],
                'result_code': report['result_code'],
                'timestamp_start': report['timestamp_start'],
                'timestamp_end': report['timestamp_end'],
            }
            if report['additional_info']:
                report_dict['additional_info'] =\
                    json.loads(report['additional_info'])
            reports.append(report_dict)
            report = subcursor.fetchone()
        
        execution_dict = {
            'execution_id': execution['id_execution'],
            'session_id': execution['fk_session'],
            'timestamp_registered': execution['timestamp_registered']
        }
        if reports:
            execution_dict['reports'] = reports
        results.append(execution_dict)

        execution = cursor.fetchone()
    
    return jsonify(results)

@app.route("/executions/<execution_id>", methods=["DELETE"])
def delete_execution(execution_id):
    check_authorization_header(client_key_recoverer)

    db = get_database()
    cursor = db.execute(
        "DELETE FROM execution WHERE id_execution = ?", (execution_id,))
    
    if cursor.rowcount != 1:
        abort(404, "No execution found with given id")

    db.commit()

    return Response(status=204, mimetype="application/json")

@app.route("/sessions", methods=["GET"])
def search_sessions():
    db = get_database()
    
    if not request.args:
        cursor = db.execute(
            """SELECT id_session, session_start, session_end, env_ip, env_port,
            env_os_system
            FROM session""")
    else:
        try:
            cursor = api_parametrized_search(
                db=db,
                table="session",
                order_by_api_to_db={
                    'id': "id_session",
                    'start': "session_start",
                    'end': "session_end",
                    'ip': "env_ip",
                    'port': "env_port",
                    'system': "env_os_system"
                },
                where_api_to_db={
                    'ids': ("id_session", "="),
                    'start_from': ("session_start", ">="),
                    'start_to': ("session_start", "<="),
                    'end_from': ("session_end", ">="),
                    'end_to': ("session_end", "<="),
                    'ips': ("env_ip", "="),
                    'ports': ("env_port", "="),
                    'systems': ("env_os_system", "="),
                },
                parameters=request.args,
                select_columns=(
                    "id_session",
                    "session_start",
                    "session_end",
                    "env_ip",
                    "env_port",
                    "env_os_system"
                ))
        except ValueError as e:
            abort(400, str(e))

    results = []
    row = cursor.fetchone()
    while row:
        session_dict = {
            'session_id': row['id_session'],
            'session_start': row['session_start'],
            'ip': row['env_ip'],
            'port': row['env_port'],
            'platform_os_system': row['env_os_system']
        }
        if row['session_end']:
            session_dict['session_end'] = row['session_end']
        results.append(session_dict)

        row = cursor.fetchone()

    return jsonify(results)

@app.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    row = get_database().execute(
        """SELECT s.id_session, s.session_start, s.session_end, s.env_ip,
        s.env_port, s.env_platform, s.env_node, s.env_os_system,
        s.env_os_release, s.env_os_version, s.env_hw_machine,
        s.env_hw_processor, s.env_py_build_no, s.env_py_build_date,
        s.env_py_compiler, s.env_py_implementation, s.env_py_version,
        (
            SELECT COUNT(id_execution)
            FROM execution
            WHERE fk_session = s.id_session
        ) AS total_executions
        FROM session s
        WHERE s.id_session = ?""", (session_id,)).fetchone()

    if not row:
        abort(404, "No session found with given id")

    result = {
        'session_id': row['id_session'],
        'session_start': row['session_start'],
        'ip': row['env_ip'],
        'port': row['env_port'],
        'platform_info': {
            'platform': row['env_platform'],
            'node': row['env_node'],
            'os': {
                'system': row['env_os_system'],
                'release': row['env_os_release'],
                'version': row['env_os_version']
            },
            'hardware': {
                'machine': row['env_hw_machine'],
                'processor': row['env_hw_processor']
            },
            'python': {
                'build': (row['env_py_build_no'], row['env_py_build_date']),
                'compiler': row['env_py_compiler'],
                'implementation': row['env_py_implementation'],
                'version': row['env_py_version']
            }
        },
        'total_executions': row['total_executions']
    }

    if row['session_end']:
        result['session_end'] = row['session_end']

    return jsonify(result)

@app.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    check_authorization_header(client_key_recoverer)

    db = get_database()
    cursor = db.execute(
        "SELECT session_end FROM session WHERE id_session = ?",
        (session_id,))
    row = cursor.fetchone()

    if not row:
        abort(404, "No session found with given id")
    if not row[0]:
        abort(400, "Session is still active")

    cursor.execute("DELETE FROM session WHERE id_session = ?", (session_id,))
    db.commit()

    return Response(status=204, mimetype="application/json")

@app.route("/test_sets", methods=["GET"])
def list_available_test_sets():
    memory_storage = get_memory_storage()
    packages_names = memory_storage.zrange("repository_index", 0, -1)
    packages_content = memory_storage.mget(
        *tuple(f"repository:{p}" for p in packages_names))
    return Response(
        response=f"[{','.join(packages_content)}]",
        status=200,
        mimetype="application/json")

@app.route("/test_sets", methods=["PATCH"])
def upload_test_sets():
    if not request.mimetype == 'multipart/form-data':
        abort(415, description="Invalid request's content type")
    check_digest_header()
    if not (request.files and 'packages' in request.files):
        abort(400, description="'packages' key not found in request's body")
    check_authorization_header(client_key_recoverer, "Digest")
    
    memory_storage = get_memory_storage()
    with memory_storage.lock("repository:mutex", timeout=30, sleep=0.5):
        try:
            new_packages = test_utils.uncompress_test_packages(
                request.files['packages'],
                TESTS_PATH)
        except Exception:
            abort(400, description="Invalid file content")

        pipe = memory_storage.pipeline()
        for new_pack in new_packages:
            new_pack = f"test_sets.{new_pack}"
            # If it is a new version, the next sentence removes the old one
            test_utils.clean_package(new_pack)

            # Updates the cache
            new_info = test_utils.get_installed_package(new_pack)
            pipe.set(f"repository:{new_info['name']}", json.dumps(new_info))
            pipe.zadd("repository_index", {new_info['name']: 0})
        pipe.execute()
                            
    return Response(status=204, mimetype="application/json")

@app.route("/test_sets/<package>", methods=["DELETE"])
def delete_package(package):
    check_authorization_header(client_key_recoverer)

    package_path = os.path.join(TESTS_PATH, package)
    memory_storage = get_memory_storage()
    with memory_storage.lock("repository:mutex", timeout=30, sleep=0.5):
        if not os.path.isdir(package_path):
            abort(404, description=f"Package '{package}' not found")

        shutil.rmtree(package_path)
        test_utils.clean_package(package)
        
        # Deletes the entry from the cache
        pipe = memory_storage.pipeline()
        pipe.delete(f"repository:{package}")
        pipe.zrem("repository_index", package)
        pipe.execute()

    return Response(status=204, mimetype="application/json")

########################## Additional functions ##############################

def exit_gracefully(sig, frame):
    """Signal handler that tries to warn all currently working nodes that the
    C&C server is shutting down before it does so.
    
    It also updates the database ending all current sessions.
    """

    print("Starting exit...")

    with app.app_context():
        get_memory_storage().flushdb(asynchronous=True)

        db = get_database() 
        cursor = db.execute(
            """SELECT env_ip, env_port
            FROM session
            WHERE session_end IS NULL""")

        environments = cursor.fetchall()
        if environments:
            signature = signatures.new_signature(
                config['NODE_SECRET'],
                "DELETE",
                "/")
            authorization_content = (
                signatures.new_authorization_header("C2", signature))

            for env in environments:
                ip = env['env_ip']
                port = env['env_port']
                try:
                    resp = rq.delete(
                        f"http://{ip}:{port}/",
                        headers={'Authorization': authorization_content})
                except rq.exceptions.ConnectionError:
                    print(f"Node at {ip}:{port} could not be reached.")
                else:
                    if resp.status_code != 204:
                        print(f"Unexpected response from node at {ip}:{port}.")
                    else:
                        print(f"Node at {ip}:{port} reached.")

            cursor.execute(
                """UPDATE session
                SET session_end = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                WHERE session_end IS NULL""")
            db.commit()
    
    print("Exiting...")
    sys.exit()


############################### Main program #################################

if not os.path.isdir(TESTS_PATH):
    os.mkdir(TESTS_PATH)
    open(os.path.join(TESTS_PATH, "__init__.py"), "w").close()

with app.app_context():
    init_database()
    init_memory_storage()

signal.signal(signal.SIGTERM, exit_gracefully)
signal.signal(signal.SIGINT, exit_gracefully)

if __name__ == "__main__":
    app.run(host=config['IP'], port=config['PORT'])