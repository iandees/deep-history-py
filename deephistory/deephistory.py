import arrow
import json
import requests
from flask import Flask, redirect, render_template, request, url_for
from itertools import tee
from xml.etree import ElementTree

app = Flask(__name__)
API_URL = 'https://api.openstreetmap.org/api/0.6'


class ElementDoesntExistException(Exception):
    def __init__(self, response):
        self.response = response

@app.errorhandler(ElementDoesntExistException)
def element_missing_exception_handler(exc):
    return render_template(
        'missing_element.html',
        exc=exc,
    )

def fetch_and_parse_json(url_suffix):
    response = requests.get(API_URL + url_suffix)

    if response.status_code == 404:
        raise ElementDoesntExistException(response)
    else:
        response.raise_for_status()

    data = response.json()
    
    return data.get('elements')

def fetch_node_history(id):
    data = fetch_and_parse_json('/node/%d/history.json' % id)
    return data

def fetch_way_history(id):
    data = fetch_and_parse_json('/way/%d/history.json' % id)
    return data

def fetch_relation_history(id):
    data = fetch_and_parse_json('/relation/%d/history.json' % id)
    return data

def compute_all_tag_keys(versions):
    all_keys = []
    for v in versions:
        for t in v.get('tags', {}).keys():
            if t not in all_keys:
                all_keys.append(t)
    return all_keys

def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def change_row(versions, attr_getter, url_template=None):
    row = []

    local_versions = [None]
    local_versions.extend(versions)

    for prev_ver, cur_ver in pairwise(local_versions):
        prev_val = attr_getter(prev_ver) if prev_ver is not None else None
        cur_val = attr_getter(cur_ver)

        if prev_val is None and cur_val is None:
            clz = 'notpresent'
        elif prev_val is None and cur_val is not None:
            clz = 'new'
        elif prev_val is not None and cur_val is None:
            clz = 'removed'
        elif prev_val != cur_val:
            clz = 'changed'
        elif prev_val == cur_val:
            clz = 'unchanged'

        row.append({
            "clz": clz,
            "val": cur_val if cur_val is not None else '',
            "url": url_template.format(val=cur_val) if url_template else None,
        })

    return row

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history/node.php')
def mapki_node_history():
    obj_id = request.args.get('id', type=int)

    if obj_id:
        return redirect(url_for('node_history', id=obj_id))
    
    return redirect(url_for('index'))

@app.route('/history/way.php')
def mapki_way_history():
    obj_id = request.args.get('id', type=int)

    if obj_id:
        return redirect(url_for('way_history', id=obj_id))
    
    return redirect(url_for('index'))

@app.route('/history/relation.php')
def mapki_relation_history():
    obj_id = request.args.get('id', type=int)

    if obj_id:
        return redirect(url_for('relation_history', id=obj_id))
    
    return redirect(url_for('index'))

@app.route('/node/<int:id>')
def node_history(id):
    versions = fetch_node_history(id)

    prop_lines = [
        ('User', change_row(versions, lambda v: v['user'], 'https://osm.org/user/{val}')),
        ('Changeset', change_row(versions, lambda v: v['changeset'], 'https://osm.org/changeset/{val}')),
        ('Lat', change_row(versions, lambda v: v.get('lat'))),
        ('Lon', change_row(versions, lambda v: v.get('lon'))),
    ]

    tag_lines = [
        (t, change_row(versions, lambda v: v.get('tags', {}).get(t)))
        for t in compute_all_tag_keys(versions)
    ]

    return render_template(
        'node.html',
        versions=versions,
        prop_lines=prop_lines,
        tag_lines=tag_lines,
    )

@app.route('/way/<int:id>')
def way_history(id):
    versions = fetch_way_history(id)

    prop_lines = [
        ('User', change_row(versions, lambda v: v['user'], 'https://osm.org/user/{val}')),
        ('Changeset', change_row(versions, lambda v: v['changeset'], 'https://osm.org/changeset/{val}')),
    ]

    tag_lines = [
        (t, change_row(versions, lambda v: v.get('tags', {}).get(t)))
        for t in compute_all_tag_keys(versions)
    ]

    all_nodes = []
    for v in versions:
        for n in v['nodes']:
            if n not in all_nodes:
                all_nodes.append(n)

    node_lines = [
        (n, change_row(versions, lambda v: n in v['nodes']))
        for n in all_nodes
    ]

    return render_template(
        'way.html',
        versions=versions,
        prop_lines=prop_lines,
        tag_lines=tag_lines,
        node_lines=node_lines,
    )

@app.route('/relation/<int:id>')
def relation_history(id):
    versions = fetch_relation_history(id)

    prop_lines = [
        ('User', change_row(versions, lambda v: v['user'], 'https://osm.org/user/{val}')),
        ('Changeset', change_row(versions, lambda v: v['changeset'], 'https://osm.org/changeset/{val}')),
    ]

    tag_lines = [
        (t, change_row(versions, lambda v: v.get('tags', {}).get(t)))
        for t in compute_all_tag_keys(versions)
    ]

    all_members = []
    for v in versions:
        for m in v['members']:
            if m not in all_members:
                all_members.append(m)

    member_lines = [
        (n, change_row(versions, lambda v: n in v.get('members', [])))
        for n in all_members
    ]

    return render_template(
        'relation.html',
        versions=versions,
        prop_lines=prop_lines,
        tag_lines=tag_lines,
        member_lines=member_lines,
    )
