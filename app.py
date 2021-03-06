from flask import Flask, jsonify, request, make_response
from flask.json import dumps
from flask_expects_json import expects_json
from jsonschema import ValidationError
from flask_jwt import JWT, jwt_required, current_identity
from datetime import timedelta
from decouple import config as config_decouple
import json

from Models import db, User, Neruda, Borges, OctavioPaz,UserPoem
from schemas import signUpSchema,savePoem
from config import configdic
from flask_cors import CORS

from utils.wordEmbedding import poem_generator


def create_app(enviroment):
    app = Flask(__name__)

    app.config.from_object(enviroment)

    with app.app_context():
        db.init_app(app)
        db.create_all()

    return app


enviroment = configdic['development']
if config_decouple('PRODUCTION', default=False):
    enviroment = configdic['production']

app = create_app(enviroment)
CORS(app)

app.config['SECRET_KEY'] = 'Esto es super secreto , por favor no lo leas'
app.config['JWT_AUTH_USERNAME_KEY'] = "email"
app.config['JWT_AUTH_URL_RULE'] = "/Login"
app.config['JWT_EXPIRATION_DELTA'] = timedelta(days=2)


def authenticate(email, password):
    user = User.query.filter_by(email=email).first()
    if user and user.verify_password(password):
        return user


def identity(payload):
    id = payload['identity']
    return User.query.filter_by(id=id).first()


jwt = JWT(app, authenticate, identity)


# errores
@app.errorhandler(400)
def bad_request(error):
    if isinstance(error.description, ValidationError):
        original_error = error.description
        return make_response(jsonify({'error': original_error.message}), 400)
    return error

# rutas


@app.route("/singUp", methods=['POST'])
@expects_json(signUpSchema)
def signUp():
    userData = request.get_json()
    name, lastName, email, password = userData.values()
    if User.query.filter_by(email=email).first() is not None:
        return jsonify({"msg": "email adress already taken"}), 400
    else:
        user = User(
            name=name,
            lastName=lastName,
            email=email,
            password=User.hash_password(password),
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({"msg": "Success"}), 200


@app.route('/protected')
@jwt_required()
def protected():
    return '%s' % current_identity


@app.route('/new-poem/<keyword>/<author>')
@jwt_required()
def newPoem(keyword,author):
    print(keyword)
    print(author)
    if author == 'OctavioPaz':
        result=OctavioPaz.query.with_entities(OctavioPaz.doc_id, OctavioPaz.sentence)
        verses=[dict(i) for i in result]
        poem=poem_generator(verses,keyword)
        return jsonify({"msg": "Success",
                        "poem":poem}), 200
    elif author == 'PabloNeruda':
        result=Neruda.query.with_entities(Neruda.doc_id, Neruda.sentence)
        verses=[dict(i) for i in result]
        poem=poem_generator(verses,keyword)
        return jsonify({"msg": "Success",
                        "poem":poem}), 200
    elif author == 'JoseLuisBorges':
        result=Borges.query.with_entities(Borges.doc_id, Borges.sentence)
        verses=[dict(i) for i in result]
        poem=poem_generator(verses,keyword)
        return jsonify({"msg": "Success",
                        "poem":poem}), 200
    else:
        return jsonify({"msg": "Invalid Parameters"}), 200

@app.route('/save-poem',methods=['POST'])
@jwt_required()
@expects_json(savePoem)
def savePoem():
    userData = request.get_json()
    poem=userData["poem"]
    keyword=userData["keyword"]
    title=userData["title"]
    userid=int('%s' % current_identity)
    userPoem=UserPoem(
        user_id=userid,
        poem=json.dumps(poem),
        title=title,
        keyword=keyword
    )
    db.session.add(userPoem)
    db.session.commit()
    return jsonify({"msg": "Success"}), 200

#contenido de un cierto poema
@app.route("/list-poem")
@jwt_required()
def listPoem():
    userid=int('%s' % current_identity)
    poems=UserPoem.query.filter_by(user_id=userid)
    data=[{"id":poem.id,"title":poem.title} for poem in poems]
    return jsonify({"msg": "Success","data":data}), 200

@app.route("/get-poem/<poem_id>")
@jwt_required()
def getPoem(poem_id):
    try:
        poem=UserPoem.query.filter_by(id=poem_id).first()
        poem=poem.poem
        poem=json.loads(poem)
        return jsonify({"msg": "Success","poem":poem}), 200
    except:
        return jsonify({"msg":"poem not found"}),400


@app.route("/getName")
@jwt_required()
def getName():
    try:
        userid=int('%s' % current_identity)
        us=User.query.filter_by(id=userid).first()
        return jsonify({"name":f"{us.name} {us.lastName}","msg":"Success"}),200
    except:
        return jsonify({"msg":"Name not found"}),400

@app.route("/isAdmin")
@jwt_required()
def isAdmin():
    try:
        userid=int('%s' % current_identity)
        us=User.query.filter_by(id=userid).first()
        return jsonify({"isAdmin":us.is_admin, "msg":"Success"}),200
    except:
        return jsonify({"msg":"ID not found"}),400


@app.route("/deletePoem/<poem_id>",methods=['DELETE'])
@jwt_required()
def deletePoem(poem_id):
    try:
        userid=int('%s' % current_identity)
        poemDelete=UserPoem.query.filter_by(id=poem_id,user_id=userid).first()
        db.session.delete(poemDelete)
        db.session.commit()
        return jsonify({"msg":"Poem deleted"}),200
    except:
        return jsonify({"msg":"Id not found"}),400

@app.route("/getUserInfoEmail/<email>")
@jwt_required()
def getUserInfoEmail(email):
    try:
        userid=int('%s' % current_identity)
        isAdmin=User.query.filter_by(id=userid).first()
        if(isAdmin.is_admin):
            user=User.query.filter_by(email=email).first()
            return jsonify({"id":user.id,"email":user.email,"name":f"{user.name} {user.lastName}","msg":"Success"}),200
        else:
            return jsonify({"msg":"Access denied"}), 401
    except:
        return jsonify({"msg":"Email not found"}), 400


@app.route("/getUserInfoId/<userid>")
@jwt_required()
def getUserInfoId(userid):
    try:
        user_id=int('%s' % current_identity)
        isAdmin=User.query.filter_by(id=user_id).first()
        if(isAdmin.is_admin):
            user=User.query.filter_by(id=userid).first()
            return jsonify({"id": user.id, "email": user.email, "name":f"{user.name} {user.lastName}", "msg":"Success"})
        else:
            return jsonify({"msg":"Access denied"}), 401
    except:
        return jsonify({"msg":"Id not found"}), 400

@app.route("/list-users")
@jwt_required()
def getUserList():
    try:
        userid=int('%s' % current_identity)
        isAdmin=User.query.filter_by(id=userid).first()
        if(isAdmin.is_admin):
            userList=User.query.all()
            data=[{"id":user.id, "name":user.name, "lastname": user.lastName, "email": user.email,"isAdmin":user.is_admin} for user in userList]
            return jsonify({"msg": "Success","data":data}), 200
        else:
            return jsonify({"msg":"Access denied"}), 401
    except:
        return jsonify({"msg":"bad request"}), 400

@app.route("/list-poem-admin/<id>")
@jwt_required()
def listPoemAdmin(id):
    try:
        userid=int('%s' % current_identity)
        isAdmin=User.query.filter_by(id=userid).first()
        if(isAdmin.is_admin):
            poems=UserPoem.query.filter_by(user_id=id)
            data=[{"id":poem.id,"title":poem.title} for poem in poems]
            return jsonify({"msg": "Success","data":data}), 200
        else:
            return jsonify({"msg":"Access denied"}), 401
    except:
        return jsonify({"msg":"bad request"}), 400

@app.route("/deleteUser/<userId>",methods=['DELETE'])
@jwt_required()
def deleteUser(userId):
    try:
        userid=int('%s' % current_identity)
        isAdmin=User.query.filter_by(id=userid).first()
        if(isAdmin.is_admin):
            user=User.query.filter_by(id=userId).first()
            db.session.delete(user)
            db.session.commit()
            return jsonify({"msg":"User Deleted"}), 200
        else:
            return jsonify({"msg":"Access denied"}), 401
    except:
        return jsonify({"msg":"bad request"}), 400

@app.route("/deletePoemAdmin/<poemId>",methods=['DELETE'])
@jwt_required()
def deletePoemAdmin(poemId):
    try:
        userid=int('%s' % current_identity)
        isAdmin=User.query.filter_by(id=userid).first()
        if(isAdmin.is_admin):
            poem=UserPoem.query.filter_by(id=poemId).first()
            db.session.delete(poem)
            db.session.commit()
            return jsonify({"msg":"Poem Deleted"}), 200
        else:
            return jsonify({"msg":"Access denied"}), 401
    except:
        return jsonify({"msg":"bad request"}), 400
# main
if __name__ == "__main__":
    app.run(port=4000, debug=True)
