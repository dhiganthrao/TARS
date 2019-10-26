# Authors: Nanda H Krishna (https://github.com/nandahkrishna), Abhijith Ragav (https://github.com/abhijithragav)

import os
from datetime import *
from dateutil.relativedelta import *
from dateutil.rrule import *
import json
import requests
import threading
from flask import Flask, jsonify, render_template, request
from slacker import Slacker

app = Flask(__name__)
app.debug = True

vineethv_id = os.environ.get("VINEETHV_ID")
tars_admin = os.environ.get("TARS_ADMIN")
tars_token = os.environ.get("TARS_TOKEN")
tars_bot_id = os.environ.get("TARS_BOT_ID")
tars = Slacker(tars_token)

vineethv_im_request = tars.im.open("UDD17R796")
vineethv_im_channel = vineethv_im_request.body["channel"]["id"]

post_message_url = "https://slack.com/api/chat.postMessage"
post_headers = {"Content-type": "application/json", "Authorization": "Bearer " + tars_token}
response_headers = {"Content-type": "application/json"}

office_hours_set = {
	"datetime_today": None,
	"last_sunday": None,
	"slot_message_ts": 0,
	"slot_days": "",
	"slot_start": "",
	"slot_start_val": "",
	"slot_end": "",
	"slot_end_val": "",
	"office_hours_text": ""
}

@app.route("/", methods=["GET"])
def index():
	return render_template("index.html")

@app.route("/event", methods=["POST"])
def event():
	payload = json.loads(request.get_data())
	thread = threading.Thread(target=event_handler, args=(payload,))
	thread.start()
	return "", 200

def event_handler(payload):
	try:
		text = payload["event"]["text"].replace("@", "")
		user = payload["event"]["user"]
		channel = payload["event"]["channel"]
		time = payload["event_time"]
		message = text + "\nFrom " + user + " in " + channel + "."
		# tars.chat.post_message(tars_admin, message)
		text = text.lower()
		if "schedule office hours" in text:
			office_hours_event_handler()
	except:
		if payload["event"]["bot_id"] != tars_bot_id:
			message = json.dumps(payload).replace("@", "")
			tars.chat.post_message(tars_admin, message)

def office_hours_event_handler():
	message = json.load(open("messages/request_office_hours.json"))
	message["channel"] = vineethv_im_channel
	office_hours_set["datetime_today"] = date.today()
	if office_hours_set["datetime_today"].weekday() == 6:
		office_hours_set["last_sunday"] = office_hours_set["datetime_today"]
	else:
		office_hours_set["last_sunday"] = office_hours_set["datetime_today"] + relativedelta(weekday=SU(-1))
	requests.post(post_message_url, headers=post_headers, json=message)

@app.route("/interact", methods=["POST"])
def interact():
	payload = json.loads(request.form.get("payload"))
	thread = threading.Thread(target=interact_handler, args=(payload,))
	thread.start()
	return "", 200

def interact_handler(payload):
	action_id = payload["actions"][0]["action_id"]
	if "office_hours" in action_id:
		office_hours_interact_handler(action_id, payload)

def office_hours_interact_handler(action_id, payload):
	message = None
	if action_id == "enter_office_hours":
		message = json.load(open("messages/slot_office_hours.json"))
		office_hours_set["slot_message_ts"] = tars.chat.post_message(vineethv_im_channel, "Your slot details will be updated here.").body["ts"]
	elif action_id == "cancel_office_hours":
		message = json.load(open("messages/cancel_office_hours.json"))
	elif action_id == "select_days_office_hours":
		options = payload["actions"][0]["selected_options"]
		office_hours_set["slot_days"] = ""
		for option in options:
			office_hour_set["slot_days"] += option["text"]["text"] + " "
		slot_text = office_hours_set["slot_days"] + office_hours_set["slot_start"] + office_hours_set["slot_end"]
		tars.chat.update(channel=vineethv_im_channel, ts=office_hours_set["slot_message_ts"], text=slot_text)
	elif action_id == "select_start_time_office_hours":
		office_hours_set["slot_start"] = payload["actions"][0]["selected_option"]["text"]["text"] + " - "
		office_hours_set["slot_start_val"] = payload["actions"][0]["selected_option"]["value"]
		slot_text = office_hours_set["slot_days"] + office_hours_set["slot_start"] + office_hours_set["slot_end"]
		tars.chat.update(channel=vineethv_im_channel, ts=office_hours_set["slot_message_ts"], text=slot_text)
	elif action_id == "select_end_time_office_hours":
		office_hours_set["slot_end"] = payload["actions"][0]["selected_option"]["text"]["text"] + "\n"
		office_hours_set["slot_end_val"] = payload["actions"][0]["selected_option"]["value"]
		slot_text = office_hours_set["slot_days"] + office_hours_set["slot_start"] + office_hours_set["slot_end"]
		tars.chat.update(channel=vineethv_im_channel, ts=office_hours_set["slot_message_ts"], text=slot_text)
	elif action_id == "slot_done_office_hours":
		if datetime.strptime(office_hours_set["slot_start_val"], "%H:%M").time() < datetime.strptime(office_hours_set["slot_end_val"], "%H:%M").time():
			message = json.load(open("messages/confirm_office_hours.json"))
			office_hours_set["office_hours_text"] = office_hours_set["slot_days"] + office_hours_set["slot_start"] + office_hours_set["slot_end"]			
		else:
			slot_text = office_hours_set["slot_days"] + office_hours_set["slot_start"] + office_hours_set["slot_end"] + "Invalid!"
			tars.chat.update(channel=vineethv_im_channel, ts=office_hours_set["slot_message_ts"], text=slot_text)
	elif action_id == "done_office_hours":
		message = json.load(open("messages/done_office_hours.json"))
		tars.chat.post_message(tars_admin, office_hours_set["office_hours_text"])
	if message is not None:
		response_url = payload["response_url"]
		requests.post(response_url, headers=response_headers, json=message)

if __name__ == "__main__":
	app.run()
