from flask import Flask, request, render_template, Blueprint, jsonify, flash, redirect, url_for
from flask_socketio import SocketIO, emit
from dateutil.relativedelta import relativedelta
import datetime
import requests
import requests_cache
import random
import collections

import process.VARS as vars
import process.legwork as leg

app = Flask(__name__)
app.secret_key = 'super secret key'

# cache for requests
requests_cache.install_cache('test_cache', backend='sqlite', expire_after=300)


# constituent data
@app.route('/constituent/civic_info', methods=['POST'])
def get_google_civic_info():
    civic_payload = {'address': request.json().get('address'),
                     'key': vars.GOOGLE_CIVIC_KEY,
                     'levels': 'country'
                     #                  'roles': 'legislatorupperbody',
                     #                  'roles': 'legislatorlowerbody'
                     }
    civic_r = requests.get(vars.GOOGLE_CIVIC_ENDPOINT, params=civic_payload)
    google_result = civic_r.json()
    if google_result.get('error'):
        return jsonify({'error': google_result['error'].get('message')})
    return jsonify(google_result)


@app.route('/constituent/location', methods=['POST'])
def get_google_location():
    payload = {'address': request.json().get('address'), 'key': vars.API_KEY}
    r = requests.get(vars.GOOGLE_GEOCODE_ENDPOINT, params=payload)
    location = r.json()['results'][0]['geometry']['location']
    return location


# federal level
@app.route('/us/senators/all')
def get_senate_members():
    master_senate_list = {}
    senate_r = requests.get(vars.PRO_PUBLICA_MEMBERS_ENDPOINT.format('senate'), headers=vars.PRO_PUB_HEADERS)
    for member in senate_r.json()['results'][0]['members']:
        last_name_list = member['last_name'].split()
        parsed_last_name = last_name_list[len(last_name_list) - 1]
        name_key = ''.join(e for e in parsed_last_name if e.isalnum())

        lower_name_key = name_key.lower()
        lower_first_name = member['first_name'][0].lower()
        formatted_key = '{0}{1}{2}'.format(lower_name_key, lower_first_name[0], member['state'])
        master_senate_list[formatted_key] = {}
        master_senate_list[formatted_key]['id'] = member['id']
        master_senate_list[formatted_key]['detail_url'] = member['api_uri']
    return jsonify(master_senate_list)


@app.route('/us/house/all')
def get_house_members():
    master_house_list = {}
    house_r = requests.get(vars.PRO_PUBLICA_MEMBERS_ENDPOINT.format('house'), headers=vars.PRO_PUB_HEADERS)
    for member in house_r.json()['results'][0]['members']:
        last_name_list = member['last_name'].split()
        parsed_last_name = last_name_list[len(last_name_list) - 1]
        name_key = ''.join(e for e in parsed_last_name if e.isalnum())

        lower_name_key = name_key.lower()
        lower_first_name = member['first_name'][0].lower()
        formatted_key = '{0}{1}{2}'.format(lower_name_key, lower_first_name[0], member['state'])
        master_house_list[formatted_key] = {}
        master_house_list[formatted_key]['id'] = member['id']
        master_house_list[formatted_key]['detail_url'] = member['api_uri']
    return jsonify(master_house_list)


@app.route('/us/<state>/<name>')
def pull_contrib_totals(name, state):
    cand_overview = {}
    # best way to do this?
    election_year='laskjdf'
    # create contributes breakdown by receipts + spending
    cand_total_params = {'api_key': vars.OPEN_FEC_KEY,
                         'cycle': election_year,
                         'q': name}
    cand_total_r = requests.get(vars.OPEN_FEC_ENDPOINT + '/candidates/totals/', params=cand_total_params)
    cand_total = cand_total_r.json().get('results')
    if len(cand_total) == 0:
        name_list = name.split()
        cand_name_filter = {'q': name_list[len(name_list) - 1],
                                   'cycle': election_year,
                                   'state': state,
                                   'api_key': vars.OPEN_FEC_KEY}
        cand_total_r = requests.get(vars.OPEN_FEC_ENDPOINT + '/candidates/totals/', params=cand_name_filter)
        cand_total = cand_total_r.json()['results']

    if len(cand_total) > 0:
        cand_overview['total_receipts'] = cand_total[0]['receipts']
        cand_overview['disbursements'] = cand_total[0]['disbursements']
        cand_overview['cash_on_hand'] = cand_total[0]['cash_on_hand_end_period']
        cand_overview['debt'] = cand_total[0]['debts_owed_by_committee']
    return jsonify(cand_overview)


# state level
@app.route('/state/<sunlight_id>/common_bill_subject_data')
def get_bill_data(sunlight_id):
    one_year = datetime.datetime.now() + relativedelta(months=-12)
    bill_params = {'sponsor_id': sunlight_id, 'updated_since': one_year.strftime('%Y-%m-%d')}
    title_subject_data = leg.get_title_subject(bill_params)
    bill_count = collections.Counter(title_subject_data['subjects'])
    sorted_bc = bill_count.most_common(vars.MAX_BILLS_LENGTH)

    data_sum = 0
    rep_bill = {
        'id': sunlight_id,
        'sum': sum(bill_count.values()),
        'data': []
    }
    for bc in sorted_bc:
        bill_subj = {
            'bill': bc[0],
            'count': bc[1]
        }
        data_sum += bc[1]
        rep_bill['data'].append(bill_subj)
    rep_bill['dataSum'] = data_sum
    return jsonify(rep_bill)
