from flask import Blueprint, jsonify


bp = Blueprint("error_handlers", __name__)

@bp.app_errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400

@bp.app_errorhandler(401)
def unauthorized(e):
    res = jsonify(error=str(e))
    res.status_code = 401
    res.headers['WWW-Authenticate'] = (
        'SECCHIWARE-HMAC-256 realm="Access to C2"')
    return res

@bp.app_errorhandler(404)
def not_found(e):
    return jsonify(error=str(e)), 404

@bp.app_errorhandler(415)
def unsupported_media_type(e):
    return jsonify(error=str(e)), 415

@bp.app_errorhandler(500)
def internal_server_error(e):
    return jsonify(error=str(e)), 500

@bp.app_errorhandler(502)
def bad_gateway(e):
    return jsonify(error=str(e)), 502

@bp.app_errorhandler(504)
def gateway_timeout(e):
    return jsonify(error=str(e)), 504