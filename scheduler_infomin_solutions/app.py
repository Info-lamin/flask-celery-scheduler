import os
import sys
import pytz
import time
import datetime
import requests
from flask import Flask
from flask import jsonify
from flask import request
from flask import render_template
from celery import Celery
from celery.contrib.abortable import AbortableTask
from sqlalchemy.orm.exc import NoResultFound
sys.path.extend([os.path.dirname(os.path.realpath(__file__)), os.path.dirname(os.path.dirname(os.path.realpath(__file__)))])
import connection
import env_variables

app = Flask(__name__)
celery = Celery(
    app.name, 
    broker=env_variables.REDIS_BROKER_URI, 
)
celery.conf.update(
    result_backend='scheduler_infomin_solutions.backend.MyResultBackend',
    result_backend_transport_options={
        'visibility_timeout': 3600,
    },
    broker_connection_retry_on_startup=True
)
celery.conf.timezone = 'Asia/Kolkata'


@celery.task(base=AbortableTask)
def trigger_webhook(url, security_code, payload, api_key):
    for _ in range(5):
        try:
            response = requests.post(
                url = url,
                headers = {
                    'Authorization': security_code
                },
                json = payload,
                verify=False
            )
            if response.status_code != 200:
                time.sleep(30)
                continue
            return response.status_code
        except:
            pass
    raise RuntimeError('Maximum retries occured')


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/read', methods=['POST', 'GET'])
@app.route('/read/<string:task_id>', methods=['POST', 'GET'])
def read(task_id=None):
    with connection.Session() as session:
        api_key = request.headers.get('Authorization') or request.args.get('Authorization')
        if task_id is None:
            api_account = session.query(connection.ApiAccount).filter_by(api_key=api_key).first()
            if api_account:
                tasks = api_account.tasks
                data = [{'task_id': task.task_id, 'result': task.result, 'state': task.state} for task in tasks]
                return jsonify({
                    'success': True,
                    'tasks': data
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'No API account found for this API key.'
                })
        else:
            task = session.query(connection.Task).join(connection.ApiAccount).filter(connection.ApiAccount.api_key == api_key, connection.Task.task_id == task_id).first()
            if task:
                return jsonify({
                    'success': True,
                    'task_id': task.task_id,
                    'result': task.result,
                    'state': task.state
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Task not found.'
                })


@app.route('/create', methods=['POST'])
def create_task():
    with connection.Session() as session:
        try:
            api_key = request.headers.get('Authorization') or request.args.get('Authorization')
            api_account = session.query(connection.ApiAccount).filter_by(api_key=api_key).one()

            timestamp = request.json.get('timestamp', datetime.datetime.now().timestamp())
            url = request.json.get('url')
            payload = request.json.get('payload', {})
            security_code = request.json.get('security_code')

            if not url:
                return jsonify({
                    'success': False,
                    'message': 'url is not passed and it is a required parameter'
                })
            if not security_code:
                return jsonify({
                    'success': False,
                    'message': 'security_code is not passed and it is a required parameter'
                })
            schedule_time = datetime.datetime.fromtimestamp(float(timestamp), pytz.timezone('Asia/Kolkata')).isoformat()
            my_task = trigger_webhook.apply_async(
                args=(url, security_code, payload, api_account.api_key), 
                eta=schedule_time
            )

            return jsonify({
                'success': True,
                'task_id': my_task.id
            })
        except NoResultFound:
            return jsonify({
                'success': False,
                'message': 'Invalid api_key is provided'
            })


@app.route('/delete', methods=['POST'])
def delete_task():
    with connection.Session() as session:
        task_id = request.json.get('task_id', None)
        api_key = request.headers.get('Authorization') or request.args.get('Authorization')
        if task_id is None:
            return jsonify({
                'success': False,
                'message': 'task_id is not passed and it is a required parameter'
            })
        task = session.query(connection.Task).join(connection.ApiAccount).filter(connection.ApiAccount.api_key == api_key, connection.Task.task_id == task_id).first()
        if task:
            my_task = trigger_webhook.AsyncResult(task.task_id)
            my_task.abort()
            return jsonify({
                'success': True,
                'task_id': task.task_id,
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Task not found.'
            })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5022)
