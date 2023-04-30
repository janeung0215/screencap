import os
from flask import Flask, render_template, redirect, url_for, session, request
from werkzeug.utils import secure_filename
from natsort import natsorted
from celery import Celery
import time
from task import capture

app = Flask(__name__)
app.config['CELERY_BROKER_URL']='redis://redis:6379/0'
app.config['CELERY_RESULT_BACKEND']='redis://redis:6379/0'    
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])
celery.conf.update(app.config)

app.config['UPLOAD_EXTENSIONS'] = ['.mp4', '.webm', '.ogg']
app.config['UPLOAD_PATH'] = 'uploads'


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        return render_template('index.html')
    if request.method == 'POST':
        file = request.files['file']
        global uploadfilename
        uploadfilename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_PATH'], uploadfilename))
        return redirect('loading')
       

@app.route('/loading')
def loading():
    global uploadfilename 
    result = capture.delay(uploadfilename)
    global result_id
    result_id = result.id
    result = celery.AsyncResult(result.id)
    if not result.ready():
      return render_template('/loading.html')   
    while True:
        if not result.ready():
            time.sleep(1)
        else: 
            return redirect(url_for('result',uploadfilename=uploadfilename))       
        

@app.route('/result/<uploadfilename>')
def result():
    global uploadfilename
    global result_id
    while True:
        result = celery.AsyncResult(result_id)
        if not result.ready(uploadfilename):
            time.sleep(1)  
        else:  
            imagelist=natsorted(os.listdir('/static/img/'+uploadfilename+'/'))
            imagelist = [uploadfilename+'/' + i for i in imagelist]
            imglist=[] 
            for i in imagelist:
                directory = i
                name = directory.split('.')
                filename = name[0].split('/')
                imglist.append(int(filename)/capture())
                return render_template("result.html", imagelist=imagelist, imglist=imglist,uploadfilename=uploadfilename, url=url_for(result,uploadfilename = uploadfilename ))



if __name__=='__main__':
    app.run()
    
