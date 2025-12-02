from flask_jwt_extended import JWTManager, create_access_token

jwt = JWTManager()

def create_token(data):
    token = create_access_token(identity=data)
    return token
