'''
EMR Add Step:
s3://us-east-1.elasticmapreduce/libs/script-runner/script-runner.jar
/usr/lib/spark/bin/spark-submit
/home/hadoop/Movie-Scene-Recommend/recommender/rating.py
/home/hadoop/Movie-Scene-Recommend/recommender/engine.py
'''
import json, csv, thread
from collections import *
import boto.sqs,boto.sns,json, inspect, threading, logging, time, requests
from engine import RecommendationEngine
from pyspark import SparkContext, SparkConf
from socketIO_client import SocketIO

conn = boto.sqs.connect_to_region("us-east-1")
queue=conn.get_queue('Watch_interval')

def init_spark_context():
    # load spark context
    conf = SparkConf().setAppName("movie_recommendation-server")
    # IMPORTANT: pass aditional Python modules to each worker
    sc = SparkContext(conf=conf, pyFiles=['engine.py'])
 
    return sc

recommendation_engine = RecommendationEngine(init_spark_context())    
socketIO = SocketIO('http://54.221.40.5:8111', 6888)

def Recommend(uid):

	intput_table =[]
	for k,v in rate_map[uid].items():
		intput_table.append((0,int(k),v))
	# print intput_table
	if len(intput_table) > 2:
		rec_list = recommendation_engine.recommends(intput_table)

		# ret = [(t[0],t[2]) for t in rec_list]
		print rec_list
		ret = []
		for row in rec_list:
			content = row.split(",")
			ret.append(( str(content[0][3:-1]),str(content[2][3:-1]) ))
		data ={}
		data["uid"]=uid
		data["rec_list"] = ret 
		print json.dumps(data)
		socketIO.emit('recommendUser',json.dumps(data))




movielen = {}
rate_map = defaultdict(lambda: defaultdict( lambda:0))

def worker():
    while True:
        for message in queue.get_messages(1):

		body = json.loads(message.get_body())
		msg =json.loads(body["Message"])
		
		if msg["event"] not in ["watch_interval","click_video"]: continue 
		
		if msg["event"] == "watch_interval":
            if msg["mid"] not in movielen: continue 
			print msg["uid"], msg["watch_interval"],msg["mid"]
			intterval = msg["watch_interval"].split(":")
			diff = float(intterval[1])-float(intterval[0])
			rate_map[msg["uid"]][msg["mid"]]+= round(diff*3/movielen[msg["mid"]],2) 
		
		if msg["event"] == "click_video":
                        if msg["mid"] not in movielen: continue
			print msg["uid"],msg["mid"] 
			rate_map[msg["uid"]][msg["mid"]]+=1
		try:

			print rate_map
			thread.start_new_thread(Recommend,(msg["uid"],))

		except Exception , errtxt:
			print errtxt
	

if __name__ == '__main__':
    movies = open('movie_len.csv', 'rb')
    spamreader = csv.reader(movies, delimiter=',')
    for row in spamreader:
    	movielen[row[-1]] = int(row[4])
    # print movielen



    worker()
