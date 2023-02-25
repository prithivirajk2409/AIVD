from flask import Flask, request, render_template, jsonify, send_file
import sys,subprocess, openai, argparse, re, os, urllib.request, threading
app= Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/text_gen" , methods=['POST', 'GET'])
def text_gen():
    name=request.form['search']
    cmd1 = ['python', 'text_generator.py', name]
    process1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
    output, error = process1.communicate()
    text = output.decode('utf-8').replace('\r\n', '<br>')
    return jsonify({'htmlresponse': render_template('textover.html', output=text)})

@app.route("/video_gen" , methods=['POST', 'GET'])
def video_gen():
    cmd2 = ['python', 'video_generator.py']
    process2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE)
    output, error = process2.communicate()
    return jsonify({'htmlresponse': render_template('videover.html')})

@app.route('/video')
def serve_video():
    video_path = "final_video.mp4"
    return send_file(video_path)

if __name__=='__main__':
    app.run()
