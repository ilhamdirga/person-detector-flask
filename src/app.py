from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import datetime
import os

from dotenv import load_dotenv

app = Flask(__name__)
api = Api(app)
mysql = MySQL()

load_dotenv

app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB')

mysql.init_app(app)

UPLOAD_FOLDER = 'static\images'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class Persons(Resource):
    def get(self):
        sql = mysql.connection.cursor()
        try:
            schema = '''SELECT * FROM person'''
            sql.execute(schema)
            persons = sql.fetchall()

            persons_list = []
            for person in persons:
                persons_dict = {
                    'id': person[0],
                    'name': person[1],
                    'full_name': person[2],
                    'created_at': person[3],
                    'picture': person[4]
                }
                persons_list.append(persons_dict)

            schema = '''SELECT COUNT(*) FROM person'''
            sql.execute(schema)
            count_persons = sql.fetchone()

            result = jsonify(total=count_persons[0],persons=persons_list)
            result.status_code = 200
            return result
        except Exception as err:
            print(err)
        finally:
            sql.close()
    
    def post(self):
        sql = mysql.connection.cursor()
        try:        
            name = request.form.get('name')
            full_name = request.form.get('full_name')
            file = request.files.get('file')

            schema = '''SELECT name FROM person WHERE name = %s'''
            sql.execute(schema, (name,))
            check = sql.fetchone()

            if check:
                result = jsonify(message='Input another name please!')
                result.status_code = 400
                return result
            
            if name is None or name == '':
                result = jsonify(message='Input name please!')
                result.status_code = 400
                return result
            
            if full_name is None or full_name == '':
                result = jsonify(message='Input full name please!')
                result.status_code = 400
                return result

            if file is None or file.filename == '':
                result = jsonify(message='Input image please!')
                result.status_code = 400
                return result

            if file and allowed_file(file.filename):
                filename = secure_filename(name + '.jpg')
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                               
                created_at = datetime.datetime.utcnow()

                schema = '''INSERT INTO person (name, full_name, created_at, picture) VALUES (%s,%s,%s,%s)'''

                sql.execute(schema, (name, full_name, created_at, file_path))
                mysql.connection.commit()
                
                result = jsonify(message='Person created!')
                result.status_code = 201
                return result
        except Exception as err:
            print(err)
        finally:
            sql.close()

class Person(Resource):
    # method untuk mengambil data person dengan id = pk
    def get_person(self, pk):
        sql = mysql.connection.cursor()
        schema = '''SELECT * FROM person WHERE id = %s'''
        sql.execute(schema, (pk,))
        person = sql.fetchone()
        sql.close()
        return person

    def get(self, pk):
        try:
            person = self.get_person(pk)
            if not person:
                result = jsonify(message='Person not found!')
                result.status_code = 404
                return result

            person_dict = {
                'id': person[0],
                'name': person[1],
                'full_name': person[2],
                'created_at': person[3],
                'picture': person[4]
            }

            result = jsonify(person=person_dict)
            result.status_code = 200
            return result
        except Exception as err:
            print(err)


    def put(self, pk):
        sql = mysql.connection.cursor()
        try:
            person = self.get_person(pk)
            if not person:
                result = jsonify(message='Person not found!')
                result.status_code = 404
                return result

            name = request.form.get('name')
            full_name = request.form.get('full_name')
            file = request.files.get('file')

            extra_keys = set(request.form.keys()) - {'name', 'full_name', 'file'}
            if extra_keys:
                result = jsonify(message=f"Invalid parameter(s): {', '.join(extra_keys)}")
                result.status_code = 404
                return result

            check_name = name is not None and name != ''
            check_full_name = full_name is not None and full_name != ''
            check_file = file is not None and file.filename != '' and allowed_file(file.filename)

            update_fields = {}

            if check_name:
                # Ambil path picture yang sebelumnya
                old_file = person[4]
                if old_file and os.path.exists(old_file) and not check_file:
                    filename = secure_filename(name + '.jpg')
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    os.rename(old_file, file_path)
                    update_fields['picture'] = file_path

                update_fields['name'] = name

            if check_full_name:
                update_fields['full_name'] = full_name

            if check_file:
                if not check_name:
                    # Ambil nama person yang sebelumnya   
                    old_name = person[1]
                    filename = secure_filename(old_name + '.jpg')
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    update_fields['picture'] = file_path
                else:         
                    # Ambil path picture yang sebelumnya
                    old_file = person[4]
                    os.remove(old_file)   

                    filename = secure_filename(name + '.jpg')
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    update_fields['picture'] = file_path
           
            if not update_fields:
                result = jsonify(message='No field(s) detected or Invalid Value(s)!')
                result.status_code = 400
                return result
            
            update_statement = ', '.join(f'{field} = %s' for field in update_fields.keys())
            schema = f'''UPDATE person SET {update_statement} WHERE id = %s'''
           
            sql.execute(schema, (*update_fields.values(), pk))

            mysql.connection.commit()

            result = jsonify(message='Success updated!')
            result.status_code = 200
            return result
            
        except Exception as err:
            print(err)
        finally:
            sql.close()

    def delete(self, pk):
        sql = mysql.connection.cursor()
        try:
            person = self.get_person(pk)
            if not person:
                result = jsonify(message='Person not found')
                result.status_code = 404
                return result

            schema = '''DELETE FROM person WHERE id = %s'''
            sql.execute(schema, (pk,))
            mysql.connection.commit()

            try:
                os.remove(person[4])
            except FileNotFoundError:
                pass

            result = jsonify(message='Success deleted!')
            result.status_code = 200
            return result

        except Exception as err:
            print(err)
        finally:
            sql.close()

class IpCameras(Resource):
    def get(self):
        sql = mysql.connection.cursor()
        try:
            schema = '''SELECT * FROM ip_camera'''
            sql.execute(schema)
            ip_camera = sql.fetchall()

            ip_camera_list = []
            for camera in ip_camera:
                ip_camera_dict = {
                    'id': camera[0],
                    'name': camera[1],
                    'ip_address': camera[2]
                }
                ip_camera_list.append(ip_camera_dict)

            result = jsonify(ip_camera=ip_camera_list)
            result.status_code = 200
            return result
        except Exception as err:
            print(err)
        finally:
            sql.close()

    def post(self):
        sql = mysql.connection.cursor()
        try:
            name = request.form.get('name')
            ip_address = request.form.get('ip_address')

            if not name or not ip_address:
                result = jsonify(message='Input name and ip_address please!')
                result.status_code = 400
                return result
            
            extra_keys = set(request.form.keys()) - {'name', 'ip_address'}
            if extra_keys:
                result = jsonify(message=f"Invalid parameter(s): {', '.join(extra_keys)}")
                result.status_code = 400
                return result      

            schema = '''SELECT * FROM ip_camera WHERE ip_address = %s'''
            sql.execute(schema, (ip_address,))
            check_ip_address = sql.fetchone()
            if check_ip_address:
                result = jsonify(message='Input another Ip Adress please!'
                )
                result.status = 400
                return result          

            schema = '''INSERT INTO ip_camera (name, ip_address) VALUES (%s,%s)'''
            sql.execute(schema, (name, ip_address))
            mysql.connection.commit()

            result = jsonify(message='Ip camera created!')
            result.status_code = 201
            return result
        except Exception as err:
            print(err)
        finally:
            sql.close()

class IpCamera(Resource):
    # Method untuk mengambil data ip_camera dengan id = pk
    def get_ip_camera(self, pk):
        sql = mysql.connection.cursor()
        schema = '''SELECT * FROM ip_camera WHERE id = %s'''
        sql.execute(schema, (pk,))
        ip_camera = sql.fetchone()
        sql.close()
        return ip_camera

    def get(self, pk):
        try:
            ip_camera = self.get_ip_camera(pk)
            if not ip_camera:
                result = jsonify(message='Camera not found!')
                result.status_code = 404
                return result

            ip_camera_dict = {
                'id': ip_camera[0],
                'name': ip_camera[1],
                'ip_address': ip_camera[2]
            }

            result = jsonify(ip_camera=ip_camera_dict)
            result.status_code = 200
            return result
        except Exception as err:
            print(err)

    def put(self, pk):
        sql = mysql.connection.cursor()
        try:
            # Periksa apakah data ip_camera dengan id = pk ada di database
            ip_camera = self.get_ip_camera(pk)
            if not ip_camera:
                result = jsonify(message='Camera not found!')
                result.status_code = 404
                return result

            name = request.form.get('name')
            ip_address = request.form.get('ip_address')

            extra_keys = set(request.form.keys()) - {'name', 'ip_address'}
            if extra_keys:
                result = jsonify(message=f'Invalid parameter(s): {", ".join(extra_keys)}')
                result.status_code = 400
                return result

            update_fields = {}

            if name is not None and name != '':
                update_fields['name'] = name
            
            if ip_address is not None and ip_address != '':
                update_fields['ip_address'] = ip_address

            update_statements = ', '.join(f'{field} = %s' for field in update_fields.keys())
            schema = f'''UPDATE ip_camera SET {update_statements} WHERE id = %s'''
           
            sql.execute(schema, (*update_fields.values(), pk))
            mysql.connection.commit()

            result = jsonify(message='Update camera success!')
            result.status_code = 200          

            return result
        except Exception as err:
            print(err)
        finally:
            sql.close()

    def delete(self, pk):
        sql = mysql.connection.cursor()
        try:
            # Periksa apakah data ip_camera dengan id = pk ada di database
            ip_camera = self.get_ip_camera(pk)
            if not ip_camera:
                result = jsonify(message='Camera not found!')
                result.status_code = 404
                return result

            schema = '''DELETE FROM ip_camera WHERE id = %s'''
            sql.execute(schema, (pk,))                          
            mysql.connection.commit()

            result = jsonify(message='Deleted success!')
            result.status_code = 200
            return result
        except Exception as err:
            print(err)
        finally:
            sql.close()

api.add_resource(Persons, '/persons', endpoint='persons')
api.add_resource(Person, '/persons/<int:pk>', endpoint='persons-detail')
api.add_resource(IpCameras, '/ip-camera', endpoint='ip-camera')
api.add_resource(IpCamera, '/ip-camera/<int:pk>', endpoint='ip-camera-detail')

if __name__ == '__main__':
    app.run(debug=True)


